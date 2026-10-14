"""
Prop AI - run the agent evaluation against real Gemini.

    python -m evals.run                      # all cases
    python -m evals.run --category not_for_sale
    python -m evals.run --case nfs-sold --repeat 3
    python -m evals.run --calibrate          # check the judge first

Each case: the agent answers (real Gemini, real database, read-only), then a
second Gemini call judges the transcript. Uses free-tier quota (about 3-5
calls per case), so it is run by hand and never inside pytest.
"""

import argparse
import json
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.database import SessionLocal
from app.services.agent import run_agent
from app.services.llm.base import AssistantMessage, LLMClient, LLMError, Message, UserMessage
from app.services.llm.gemini import GeminiClient
from evals.judge import JUDGE_SYSTEM, Verdict, build_judge_prompt, build_transcript, parse_verdict

HERE = Path(__file__).resolve().parent
CASES_FILE = HERE / "cases.json"
CALIBRATION_FILE = HERE / "calibration.json"
REPORTS_DIR = HERE / "reports"

Sleep = Callable[[float], None]


@dataclass
class CaseOutcome:
    case_id: str
    category: str
    attempts: int = 0
    runs: int = 0  # attempts that got a verdict
    passes: int = 0
    scores: list[int] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)  # why attempts failed or errored
    agent_errors: int = 0
    judge_errors: int = 0

    @property
    def passed(self) -> bool:
        """Every attempt was judged and passed: 2 of 3 is flaky, not a pass."""
        return self.attempts > 0 and self.passes == self.attempts


def load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def to_history(messages: list[dict]) -> list[Message]:
    return [
        UserMessage(m["content"]) if m["role"] == "user" else AssistantMessage(m["content"])
        for m in messages
    ]


def judge(judge_llm: LLMClient, expected: str, transcript: str) -> Verdict | None:
    """One judge call. None means no usable verdict (a judge error, not a fail)."""
    try:
        reply = judge_llm.generate(
            JUDGE_SYSTEM, [UserMessage(build_judge_prompt(expected, transcript))], []
        )
    except LLMError:
        return None
    return parse_verdict(reply.text)


def evaluate_case(
    db,
    case: dict,
    agent_llm: LLMClient,
    judge_llm: LLMClient,
    repeat: int = 1,
    delay: float = 0.0,
    sleep: Sleep = time.sleep,
) -> CaseOutcome:
    outcome = CaseOutcome(case["id"], case["category"])
    for _ in range(repeat):
        outcome.attempts += 1
        try:
            result = run_agent(db, to_history(case["messages"]), agent_llm)
        except LLMError as exc:
            outcome.agent_errors += 1
            outcome.failures.append(f"agent error: {exc}")
            sleep(delay)
            continue
        sleep(delay)  # stay under the free tier's requests-per-minute limit

        verdict = judge(judge_llm, case["expected"], build_transcript(case["messages"], result))
        sleep(delay)
        if verdict is None:
            outcome.judge_errors += 1
            outcome.failures.append("judge error: no valid verdict")
            continue
        outcome.runs += 1
        outcome.passes += verdict.passed
        outcome.scores.append(verdict.score)
        outcome.reasons.append(verdict.reason)
        if not verdict.passed:
            outcome.failures.append(verdict.reason)
    return outcome


def calibrate(
    judge_llm: LLMClient, items: list[dict], delay: float = 0.0, sleep: Sleep = time.sleep
) -> tuple[int, int, list[str]]:
    """How often the judge agrees with hand-labelled transcripts."""
    disagreements = []
    for item in items:
        verdict = judge(judge_llm, item["expected"], item["transcript"])
        sleep(delay)
        if verdict is None or verdict.passed != item["verdict"]:
            disagreements.append(item["id"])
    return len(items) - len(disagreements), len(items), disagreements


def select_cases(cases: list[dict], case_id: str | None = None, category: str | None = None) -> list[dict]:
    return [
        c for c in cases
        if (case_id is None or c["id"] == case_id) and (category is None or c["category"] == category)
    ]


def _totals(outcomes: list[CaseOutcome]) -> dict:
    scores = [s for o in outcomes for s in o.scores]
    passed = sum(o.passed for o in outcomes)
    return {
        "cases": len(outcomes),
        "passed": passed,
        "pass_rate": round(passed / len(outcomes), 3) if outcomes else 0.0,
        "average_score": round(sum(scores) / len(scores), 2) if scores else None,
        "agent_errors": sum(o.agent_errors for o in outcomes),
        "judge_errors": sum(o.judge_errors for o in outcomes),
    }


def _reason(outcome: CaseOutcome) -> str:
    """The most useful single reason: the first failure, else the judge's reason."""
    pool = outcome.failures or outcome.reasons
    text = pool[0] if pool else ""
    return text.replace("|", "/").replace("\n", " ")


def write_report(outcomes: list[CaseOutcome], out_dir: Path, meta: dict) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    totals = _totals(outcomes)
    json_path, md_path = out_dir / "latest.json", out_dir / "latest.md"
    json_path.write_text(
        json.dumps({"meta": meta, "totals": totals, "cases": [asdict(o) for o in outcomes]},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = [
        "# Prop AI agent eval",
        "",
        f"{meta.get('date', '')} · model `{meta.get('model', '')}` · repeat {meta.get('repeat', 1)} · judged by an LLM",
        "",
        f"**Cases passed: {totals['passed']}/{totals['cases']}** (pass rate {totals['pass_rate']:.0%}) · "
        f"average score {totals['average_score']} / 5 · agent errors {totals['agent_errors']} · "
        f"judge errors {totals['judge_errors']}",
        "",
        "| Case | Category | Passed | Avg score | Judge's reason |",
        "|---|---|---|---|---|",
    ]
    for o in outcomes:
        avg = f"{sum(o.scores) / len(o.scores):.1f}" if o.scores else "–"
        lines.append(f"| {o.case_id} | {o.category} | {o.passes}/{o.attempts} | {avg} | {_reason(o)} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def make_client() -> GeminiClient | None:
    settings = get_settings()
    key = settings.gemini_api_key
    if key is None or not key.get_secret_value().strip():
        return None
    return GeminiClient(
        api_key=key.get_secret_value(),
        model=settings.gemini_model,
        fallback_model=settings.gemini_fallback_model,
    )


def main(argv: list[str] | None = None, sleep: Sleep = time.sleep) -> int:
    # Windows consoles default to cp1252, which can't print ₹.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Evaluate the Prop AI agent with an LLM judge.")
    parser.add_argument("--case", help="run one case by id")
    parser.add_argument("--category", help="run one category, e.g. not_for_sale")
    parser.add_argument("--repeat", type=int, default=1, help="runs per case (shows flaky cases)")
    parser.add_argument("--delay", type=float, default=4.0, help="seconds between Gemini calls")
    parser.add_argument("--calibrate", action="store_true", help="check the judge on labelled transcripts")
    parser.add_argument("--out", type=Path, default=REPORTS_DIR, help="report folder")
    args = parser.parse_args(argv)

    if args.calibrate:
        client = make_client()
        if client is None:
            print("GEMINI_API_KEY is not set in backend/.env.")
            return 2
        agreed, total, disagreements = calibrate(client, load(CALIBRATION_FILE), args.delay, sleep)
        print(f"Judge agreement: {agreed}/{total}")
        for item_id in disagreements:
            print(f"  disagreed on: {item_id}")
        return 0 if agreed == total else 1

    cases = select_cases(load(CASES_FILE), args.case, args.category)
    if not cases:
        print("No cases match. Check --case / --category against evals/cases.json.")
        return 2
    client = make_client()
    if client is None:
        print("GEMINI_API_KEY is not set in backend/.env.")
        return 2

    outcomes = []
    with SessionLocal() as db:
        for i, case in enumerate(cases, 1):
            outcome = evaluate_case(db, case, client, client, args.repeat, args.delay, sleep)
            outcomes.append(outcome)
            mark = "PASS" if outcome.passed else "FAIL"
            print(f"[{i}/{len(cases)}] {mark} {outcome.case_id} ({outcome.passes}/{outcome.attempts}) {_reason(outcome)}")

    meta = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "model": get_settings().gemini_model,
        "repeat": args.repeat,
        "filter": {"case": args.case, "category": args.category},
    }
    _, md_path = write_report(outcomes, args.out, meta)
    totals = _totals(outcomes)
    print(f"\nPassed {totals['passed']}/{totals['cases']} · average score {totals['average_score']} · report: {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
