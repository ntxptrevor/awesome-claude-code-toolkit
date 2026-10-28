"""Council router: JEV decides for free; escalate to the cheapest available LLM
judges only when JEV is uncertain; tally a weighted vote with full provenance."""
from __future__ import annotations

from .base import JUDGES, Task, Verdict

JEV_CONFIDENCE = 0.75     # JEV >= this -> accept without spending a cent
DEFAULT_MAX_COST = 1.0    # relative budget per decision
DEFAULT_ESCALATE = 1      # how many LLM judges to consult on escalation


class Council:
    def __init__(self, judges: dict | None = None):
        from . import judges as _reg  # noqa: F401  (ensures registration)
        self.judges = judges if judges is not None else dict(JUDGES)

    def decide(self, task: Task, jev_threshold: float = JEV_CONFIDENCE,
               max_cost: float = DEFAULT_MAX_COST,
               escalate: int = DEFAULT_ESCALATE) -> dict:
        jev = self.judges["jev"].decide(task)
        verdicts = [jev]
        mode = "jev-only"
        if jev.choice is None or jev.confidence < jev_threshold:
            mode = "escalated"
            llm = sorted((j for n, j in self.judges.items() if n != "jev" and j.available()),
                         key=lambda j: j.cost)
            spent = 0.0
            for j in llm[:escalate]:
                if spent + j.cost > max_cost:
                    break
                v = j.decide(task)
                verdicts.append(v)
                spent += v.cost
        return self._finalize(verdicts, mode)

    @staticmethod
    def _finalize(verdicts: list[Verdict], mode: str) -> dict:
        tally: dict[str, float] = {}
        for v in verdicts:
            if v.choice is not None:
                tally[v.choice] = tally.get(v.choice, 0.0) + max(v.confidence, 0.01)
        cost = round(sum(v.cost for v in verdicts), 4)
        prov = [{"judge": v.judge, "choice": v.choice, "confidence": v.confidence,
                 "cost": v.cost, "rationale": v.rationale} for v in verdicts]
        if not tally:
            return {"choice": None, "confidence": 0.0, "cost": cost, "mode": mode,
                    "provenance": prov}
        choice = max(tally, key=lambda k: tally[k])
        backing = [v for v in verdicts if v.choice == choice]
        share = tally[choice] / sum(tally.values())
        avg = sum(v.confidence for v in backing) / len(backing)
        final = round(0.5 * share + 0.5 * avg, 4)
        return {"choice": choice, "confidence": final, "cost": cost, "mode": mode,
                "voters": sorted(v.judge for v in backing), "provenance": prov}


def decide(task: dict, **opts) -> dict:
    """Convenience: build a Task from a dict and run the default council."""
    t = Task(kind=task.get("kind", "pick_value"),
             question=task.get("question", ""),
             options=task.get("options", []),
             context=task.get("context", {}))
    return Council().decide(t, **opts)
