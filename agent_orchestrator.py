from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentAction(str, Enum):
    RESEARCH = "research"
    ANALYZE = "analyze"
    VERIFY = "verify"
    REVIEW = "review"
    FINISH = "finish"


@dataclass
class AgentState:
    target: str
    max_iterations: int = 5
    iteration: int = 0
    findings: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    status: str = "pending"
    analysis_completed: bool = False
    verification_completed: bool = False
    review_completed: bool = False

    def record(self, agent: str, action: AgentAction, reason: str) -> None:
        self.history.append({
            "iteration": self.iteration,
            "agent": agent,
            "action": action.value,
            "reason": reason,
        })


class AgentOrchestrator:
    def __init__(self, state: AgentState):
        self.state = state

    def next_action(self) -> AgentAction:
        state = self.state

        if (
            state.findings
            and state.analysis_completed
            and state.verification_completed
            and state.review_completed
        ):
            state.status = "completed"
            action = AgentAction.FINISH
            reason = "Zakończono"
        elif state.iteration >= state.max_iterations:
            state.status = "iteration_limit"
            action = AgentAction.FINISH
            reason = "Osiągnięto limit iteracji"
        elif state.iteration > 0 and not state.findings:
            state.status = "research_failed"
            action = AgentAction.FINISH
            reason = "Nie pobrano żadnych dokumentów"
        elif not state.findings:
            action = AgentAction.RESEARCH
            reason = "Brak zebranych dokumentów"
        elif not state.analysis_completed:
            action = AgentAction.ANALYZE
            reason = "Analiza dokumentów"
        elif not state.verification_completed:
            action = AgentAction.VERIFY
            reason = "Weryfikacja faktów"
        elif not state.review_completed:
            action = AgentAction.REVIEW
            reason = "Ocena wyników"
        else:
            state.status = "completed"
            action = AgentAction.FINISH
            reason = "Zakończono"

        state.record("orchestrator", action, reason)
        return action


if __name__ == "__main__":
    state = AgentState(target="https://example.com")
    orchestrator = AgentOrchestrator(state)

    assert orchestrator.next_action() == AgentAction.RESEARCH

    state.findings.append({"fact": "Przykładowy fakt"})
    assert orchestrator.next_action() == AgentAction.ANALYZE

    state.analysis_completed = True
    assert orchestrator.next_action() == AgentAction.VERIFY

    state.verification_completed = True
    assert orchestrator.next_action() == AgentAction.REVIEW

    state.iteration = 5
    assert orchestrator.next_action() == AgentAction.FINISH

    assert len(state.history) == 5

    print("PASS | Agent Orchestrator: 5/5 testów OK")
