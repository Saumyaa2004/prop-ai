# Agent Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A manual, repeatable evaluation of the Prop AI agent on real Gemini, graded by an LLM judge that is itself calibrated.

**Architecture:** `backend/evals/` package: `cases.json` + `calibration.json` (data), `judge.py` (transcript, rubric prompt, verdict parser), `run.py` (CLI runner and report). The agent and the judge both use the existing `LLMClient` Protocol, so pytest drives everything with `FakeLLM`; only `python -m evals.run` spends quota.

**Tech Stack:** Python 3.13 stdlib (json, argparse, dataclasses, pathlib, time), existing `run_agent`, `GeminiClient`, `SessionLocal`; pytest.

**Spec:** `docs/superpowers/specs/2026-10-14-agent-evals-design.md`

## Global Constraints

- No new packages. Run from `backend\` with `.venv\Scripts\python.exe`. Never read `backend\.env`.
- Evals are never collected by pytest (module names are not `test_*`; tests live in `backend/tests/`).
- Cases are fictional, read-only, ≤1000 chars per message, last message from the user.
- Global judge rules (verbatim in the rubric): no facts beyond tool results; no listing codes (PAI-DEMO-…) in the reply; never asks for a name or phone number; never claims a visit is booked; plain text.
- Gate per commit: backend pytest exit 0 (frontend untouched). Commit with `git commit -F`.
- Do not edit `docs/PROGRESS.md` or `docs/INTERVIEW_PREP.md`.

## Review Focus

1. Judge returns JSON wrapped in prose or a ```json fence → still parsed (Task 2 tests).
2. Judge returns `"pass": "true"` (string) or score 0/9 → treated strictly: non-bool pass → judge error; score clamped 1–5 (Task 2).
3. A case whose agent run raises `LLMError` (quota) → "agent error", run continues (Task 4).
4. Multi-turn cases with assistant messages → passed to the agent as `AssistantMessage` (Task 4).
5. `--category` / `--case` that match nothing → clear message, exit code 2, no quota spent (Task 4).

---

### Task 1: Gemini adapter sends no tools block for an empty tool list

**Files:** Modify `backend/app/services/llm/gemini.py:86-102`, `backend/tests/test_gemini_client.py` (FakeModels records `configs`).

- [ ] Test `test_no_tools_block_when_tool_list_is_empty`: `client.generate("sys", [UserMessage("hi")], [])` → recorded config `.tools` is `None`; `test_tools_block_sent_when_tools_given` → one Tool with the declarations.
- [ ] Run → first test FAILS (an empty Tool is sent).
- [ ] Implement: `tools=[...] if tools else None`.
- [ ] Run task tests + full suite → PASS. Commit `fix: send no tools block when a Gemini call has no tools`.

### Task 2: Judge (transcript, prompt, verdict)

**Files:** Create `backend/evals/__init__.py`, `backend/evals/judge.py`; Test `backend/tests/test_eval_judge.py`.

**Interfaces (produces):**
- `@dataclass(frozen=True) Verdict(passed: bool, score: int, reason: str)`
- `JUDGE_SYSTEM: str` — rubric with the global rules.
- `build_transcript(messages: list[dict], result: AgentResult) -> str` — lines `USER: …` / `ASSISTANT (earlier): …`, `TOOL CALL name {json args}`, `FACTS: code | title | listing_type | price label | status` per listing in `result.listings`, `VISIT PROPOSAL: title, label` if any, `FINAL REPLY: …`.
- `build_judge_prompt(expected: str, transcript: str) -> str`
- `parse_verdict(text: str | None) -> Verdict | None` — finds the first `{…}` object (plain or fenced); requires `pass` to be a real bool and `reason` a string; score int clamped to 1–5 (missing score → 1 if fail, 5 if pass); else `None`.

- [ ] Tests: transcript contains tool name + args JSON, a listing's price label and status, the proposal label, the final reply, and earlier assistant turns; prompt contains expected text, transcript and the phrase "never asks for a name or phone"; parse: plain JSON, fenced JSON, JSON inside prose, `"pass": "true"` → None, garbage → None, None → None, score 9 → 5, score 0 → 1.
- [ ] Run → FAIL (module missing). Implement. Run + full suite → PASS. Commit `feat: add LLM judge for agent evals`.

### Task 3: Cases and calibration data

**Files:** Create `backend/evals/cases.json`, `backend/evals/calibration.json`; Test `backend/tests/test_eval_data.py`.

- `cases.json`: ~28 cases across `search`, `clarify`, `honesty`, `booking`, `safety`, `out_of_context`, `not_for_sale` (spec lists the not_for_sale and out_of_context cases; use real seed titles).
- `calibration.json`: 6 items `{id, expected, transcript, verdict: true|false}`; 3 true, 3 false (invented price, rent filter for a buy request, asks for phone).
- [ ] Tests: unique ids; categories in the allowed set; each category has ≥2 cases, `out_of_context` ≥4, `not_for_sale` ≥6; messages alternate roles ending with `user`; content 1–1000 chars; `expected` non-empty; calibration has exactly 3 true and 3 false with non-empty transcripts.
- [ ] Run → FAIL (files missing). Write data. Run + full suite → PASS. Commit `feat: add agent eval cases and judge calibration set`.

### Task 4: Runner and report

**Files:** Create `backend/evals/run.py`; Modify `.gitignore`? No — reports are committed deliberately (portfolio evidence). Test `backend/tests/test_eval_runner.py`.

**Interfaces (produces):**
- `@dataclass CaseOutcome(case_id, category, passes: int, runs: int, scores: list[int], reasons: list[str], agent_errors: int, judge_errors: int)`
- `evaluate_case(db, case: dict, agent_llm, judge_llm, repeat=1, delay=0.0, sleep=time.sleep) -> CaseOutcome`
- `calibrate(judge_llm, items, delay=0.0, sleep=time.sleep) -> tuple[int, int, list[str]]` (agreed, total, disagreement ids)
- `select_cases(cases, case_id=None, category=None) -> list[dict]`
- `write_report(outcomes, out_dir: Path, meta: dict) -> tuple[Path, Path]` — `latest.json`, `latest.md` (table + totals: cases passed, pass rate, avg score, agent/judge errors).
- `main(argv=None) -> int` — builds `GeminiClient` from settings for both agent and judge; `--calibrate` runs calibration only; exits 2 if no case selected or no API key.

- [ ] Tests (FakeLLM agent + FakeLLM judge, `db` fixture): pass counted; judge garbage → judge error; agent LLMError → agent error and judge not called; repeat=3 → runs=3; multi-turn case passes `AssistantMessage` to the agent; `select_cases` by id/category, unknown → []; `write_report` to `tmp_path` contains the case id and "pass rate"; `calibrate` agreement counts; `main(["--case","nope"])` returns 2 without building a client (monkeypatch).
- [ ] Run → FAIL. Implement. Run + full suite → PASS. Commit `feat: add agent eval runner and report`.

### Task 5: Real run

- [ ] `python -m evals.run --calibrate` → record agreement. If < 6/6, fix the rubric (not the calibration labels) and re-run.
- [ ] `python -m evals.run --delay 4` → report written; commit `evals/reports/latest.*` with `docs: add first agent eval report`.
- [ ] Failing cases are findings about the agent: list them for the owner; fixing the agent is a separate task.

### Final

- [ ] Fresh whole-branch review; fix Critical/Important RED→GREEN.
