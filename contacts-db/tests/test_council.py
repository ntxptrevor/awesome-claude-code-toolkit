"""F2b — mini model council (JEV default + cheap LLM escalation)."""
from ntxp_contacts.council import Council, decide
from ntxp_contacts.council.base import Task, Verdict
from ntxp_contacts.council.judges import DeepSeekJudge, JEVJudge


def test_jev_decides_for_free_when_confident():
    task = {"kind": "pick_value", "question": "best phone?",
            "options": [{"id": "A", "value": "x", "grade": 0.92},
                        {"id": "B", "value": "y", "grade": 0.40}]}
    out = decide(task)
    assert out["choice"] == "A"
    assert out["mode"] == "jev-only"
    assert out["cost"] == 0.0


def test_escalates_when_uncertain_but_still_decides_with_no_keys():
    task = {"kind": "pick_value", "question": "best email?",
            "options": [{"id": "A", "value": "x", "grade": 0.50},
                        {"id": "B", "value": "y", "grade": 0.48}]}
    out = decide(task)               # no API keys -> no LLM judges available
    assert out["mode"] == "escalated"
    assert out["choice"] in ("A", "B")
    assert out["cost"] == 0.0        # nothing spent
    assert len(out["provenance"]) == 1  # JEV only


class _Fake:
    name = "fake"
    cost = 0.1

    def available(self):
        return True

    def decide(self, task):
        return Verdict("B", 0.9, "fake", 0.1, "test")


def test_escalation_consults_llm_and_votes():
    council = Council(judges={"jev": JEVJudge(), "fake": _Fake()})
    task = Task("pick_value", "best?",
                [{"id": "A", "grade": 0.50}, {"id": "B", "grade": 0.48}])
    out = council.decide(task)
    judges = [p["judge"] for p in out["provenance"]]
    assert "fake" in judges and out["cost"] == 0.1
    assert out["choice"] == "B"       # fake's high-confidence vote wins


def test_llm_judge_gated_on_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert DeepSeekJudge().available() is False
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    assert DeepSeekJudge().available() is True


def test_abstain_on_no_options():
    out = decide({"kind": "pick_value", "question": "?", "options": []})
    assert out["choice"] is None
