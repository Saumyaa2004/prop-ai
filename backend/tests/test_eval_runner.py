"""
Tests for the eval runner, with fake LLMs for both the agent and the judge.
No quota is used; the real run is `python -m evals.run`.
"""

import json

from app.services.llm.base import AssistantMessage, LLMError, UserMessage
from evals import run
from evals.run import calibrate, evaluate_case, select_cases, write_report
from tests.fakes import FakeLLM, answer

PASS = answer('{"pass": true, "score": 5, "reason": "Did the right thing."}')
FAIL = answer('{"pass": false, "score": 2, "reason": "Invented a price."}')

CASE = {
    "id": "ooc-weather",
    "category": "out_of_context",
    "messages": [{"role": "user", "content": "What's the weather?"}],
    "expected": "Declines politely and offers property help.",
}


def no_sleep(seconds: float) -> None:
    pass


def test_a_passing_run_is_counted(db):
    agent, judge = FakeLLM(answer("I can only help with property.")), FakeLLM(PASS)

    outcome = evaluate_case(db, CASE, agent, judge, sleep=no_sleep)

    assert (outcome.runs, outcome.passes, outcome.scores) == (1, 1, [5])
    assert outcome.passed
    # The judge saw the agent's reply and the expected behaviour.
    prompt = judge.calls[0][0].text
    assert "I can only help with property." in prompt and CASE["expected"] in prompt


def test_garbage_from_the_judge_is_a_judge_error_not_a_fail(db):
    agent, judge = FakeLLM(answer("Sorry, property only.")), FakeLLM(answer("Looks fine to me!"))

    outcome = evaluate_case(db, CASE, agent, judge, sleep=no_sleep)

    assert (outcome.judge_errors, outcome.runs, outcome.passes) == (1, 0, 0)
    assert not outcome.passed


def test_agent_failure_is_an_agent_error_and_skips_the_judge(db):
    agent, judge = FakeLLM(LLMError("quota")), FakeLLM(PASS)

    outcome = evaluate_case(db, CASE, agent, judge, sleep=no_sleep)

    assert outcome.agent_errors == 1
    assert judge.calls == []


def test_repeat_reports_flaky_cases(db):
    agent = FakeLLM(answer("ok"), repeat_last=True)
    judge = FakeLLM(PASS, FAIL, PASS)
    waits: list[float] = []

    outcome = evaluate_case(db, CASE, agent, judge, repeat=3, delay=2.5, sleep=waits.append)

    assert (outcome.runs, outcome.passes) == (3, 2)
    assert not outcome.passed  # 2/3 is flaky, not a pass
    assert waits and all(w == 2.5 for w in waits)  # quota-friendly pauses happened


def test_multi_turn_history_reaches_the_agent(db):
    case = {**CASE, "messages": [
        {"role": "user", "content": "Show me a 2BHK in Powai"},
        {"role": "assistant", "content": "Buy or rent?"},
        {"role": "user", "content": "rent"},
    ]}
    agent, judge = FakeLLM(answer("ok")), FakeLLM(PASS)

    evaluate_case(db, case, agent, judge, sleep=no_sleep)

    history = agent.calls[0]
    assert [type(m) for m in history] == [UserMessage, AssistantMessage, UserMessage]
    assert history[1].text == "Buy or rent?"


def test_select_cases():
    cases = [CASE, {**CASE, "id": "nfs-sold", "category": "not_for_sale"}]
    assert [c["id"] for c in select_cases(cases, case_id="nfs-sold")] == ["nfs-sold"]
    assert [c["id"] for c in select_cases(cases, category="out_of_context")] == ["ooc-weather"]
    assert select_cases(cases, case_id="nope") == []
    assert len(select_cases(cases)) == 2


def test_report_files(db, tmp_path):
    outcome = evaluate_case(db, CASE, FakeLLM(answer("ok")), FakeLLM(FAIL), sleep=no_sleep)

    json_path, md_path = write_report([outcome], tmp_path, {"model": "fake", "repeat": 1})

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["totals"]["cases"] == 1 and data["totals"]["passed"] == 0
    md = md_path.read_text(encoding="utf-8")
    assert "ooc-weather" in md and "Invented a price." in md and "pass rate" in md.lower()


def test_calibrate_counts_agreement():
    items = [
        {"id": "good", "verdict": True, "expected": "x", "transcript": "FINAL REPLY: ok"},
        {"id": "bad", "verdict": False, "expected": "x", "transcript": "FINAL REPLY: ₹1.20 Cr"},
        {"id": "garbled", "verdict": False, "expected": "x", "transcript": "FINAL REPLY: ?"},
    ]
    judge = FakeLLM(PASS, PASS, answer("no json"))  # agrees, disagrees, errors

    agreed, total, disagreements = calibrate(judge, items, sleep=no_sleep)

    assert (agreed, total) == (1, 3)
    assert disagreements == ["bad", "garbled"]


def test_main_exits_2_without_spending_quota_when_nothing_matches(monkeypatch):
    built = []
    monkeypatch.setattr(run, "make_client", lambda: built.append(1))
    assert run.main(["--case", "no-such-case"]) == 2
    assert built == []


def test_main_runs_one_case_end_to_end(monkeypatch, tmp_path):
    fake = FakeLLM(answer("I can only help with property."), PASS)  # agent turn, then judge
    monkeypatch.setattr(run, "make_client", lambda: fake)

    code = run.main(["--case", "ooc-weather", "--delay", "0", "--out", str(tmp_path)])

    assert code == 0
    # A one-case run is a filtered run: it must not overwrite the committed latest.md.
    assert "ooc-weather" in (tmp_path / "filtered.md").read_text(encoding="utf-8")
    assert not (tmp_path / "latest.md").exists()


def test_report_reason_is_the_real_failure_even_after_an_error(db, tmp_path):
    # Attempt 1: judge garbage (error, no score). Attempt 2: pass. Attempt 3: fail.
    agent = FakeLLM(answer("ok"), repeat_last=True)
    judge = FakeLLM(answer("garbage"), PASS, FAIL)
    outcome = evaluate_case(db, CASE, agent, judge, repeat=3, sleep=no_sleep)

    _, md_path = write_report([outcome], tmp_path, {})

    row = next(line for line in md_path.read_text(encoding="utf-8").splitlines() if "ooc-weather" in line)
    assert "judge error" in row or "Invented a price." in row
    assert "Did the right thing." not in row  # a passing reason must never explain a failure


# ---------- review fixes: statuses, date, throttle, safety ----------


def test_three_statuses_errors_are_not_failures(db):
    passing = evaluate_case(db, CASE, FakeLLM(answer("ok")), FakeLLM(PASS), sleep=no_sleep)
    failing = evaluate_case(db, CASE, FakeLLM(answer("ok")), FakeLLM(FAIL), sleep=no_sleep)
    erroring = evaluate_case(db, CASE, FakeLLM(LLMError("429")), FakeLLM(PASS), sleep=no_sleep)
    assert (passing.status, failing.status, erroring.status) == ("pass", "fail", "error")

    totals = run._totals([passing, failing, erroring])
    assert (totals["passed"], totals["failed"], totals["errored"]) == (1, 1, 1)
    assert totals["pass_rate"] == 0.5  # judged cases only: an error is not a failure


def test_judge_sees_todays_date(db):
    judge = FakeLLM(PASS)
    evaluate_case(db, CASE, FakeLLM(answer("ok")), judge, sleep=no_sleep)
    assert "TODAY: " in judge.calls[0][0].text


def test_throttle_spaces_every_call():
    clock = iter([0.0, 1.0, 1.0, 10.0, 10.0])  # now() readings
    waits: list[float] = []
    inner = FakeLLM(answer("a"), answer("b"), answer("c"))
    throttled = run.ThrottledLLM(inner, gap=4.0, clock=lambda: next(clock), sleep=waits.append)

    for _ in range(3):
        throttled.generate("sys", [UserMessage("hi")], [])

    # 2nd call came 1s after the 1st: wait 3s more. 3rd came 9s later: no wait.
    assert waits == [3.0]
    assert len(inner.calls) == 3


def test_bad_arguments_are_rejected_before_any_call(monkeypatch):
    monkeypatch.setattr(run, "make_client", lambda: (_ for _ in ()).throw(AssertionError("no client")))
    for argv in (["--delay", "-1"], ["--repeat", "0"]):
        try:
            run.main(argv)
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError(f"{argv} was accepted")


def test_interrupted_run_still_writes_a_partial_report(monkeypatch, tmp_path):
    monkeypatch.setattr(run, "make_client", lambda: FakeLLM(answer("ok"), PASS))
    calls = {"n": 0}
    real = run.evaluate_case

    def flaky_evaluate(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise KeyboardInterrupt
        return real(*args, **kwargs)

    monkeypatch.setattr(run, "evaluate_case", flaky_evaluate)
    code = run.main(["--category", "out_of_context", "--delay", "0", "--out", str(tmp_path)])

    assert code == 130
    data = json.loads((tmp_path / "filtered.json").read_text(encoding="utf-8"))
    assert data["meta"]["interrupted"] is True and data["totals"]["cases"] == 1


def test_report_json_has_status_and_filtered_runs_dont_overwrite_latest(db, tmp_path):
    outcome = evaluate_case(db, CASE, FakeLLM(answer("ok")), FakeLLM(PASS), sleep=no_sleep)
    json_path, md_path = write_report([outcome], tmp_path, {"filter": {"case": "ooc-weather"}})
    assert json_path.name == "filtered.json" and md_path.name == "filtered.md"
    assert json.loads(json_path.read_text(encoding="utf-8"))["cases"][0]["status"] == "pass"
    assert "ooc-weather" in md_path.read_text(encoding="utf-8").splitlines()[2]  # filter in header
