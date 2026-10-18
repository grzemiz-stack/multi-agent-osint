
from agent_orchestrator import AgentAction, AgentState


class ReviewerAgent:
    name = "reviewer_agent"

    def run(self, state: AgentState) -> dict:
        if not state.verification_completed:
            raise ValueError("Weryfikacja nie została zakończona")

        counts = {
            "verified": 0,
            "rejected": 0,
            "needs_review": 0,
        }

        for item in state.evidence:
            status = item.get("status", "needs_review")
            if status not in counts:
                status = "needs_review"
            counts[status] += 1

        total = len(state.evidence)

        if total == 0:
            decision = "insufficient_evidence"
        elif counts["needs_review"] > 0:
            decision = "manual_review_required"
        elif counts["rejected"] > 0:
            decision = "contains_rejected_claims"
        else:
            decision = "source_supported"

        state.review_completed = True
        state.iteration += 1

        state.record(
            self.name,
            AgentAction.REVIEW,
            f"Decyzja: {decision}; "
            f"potwierdzone: {counts['verified']}; "
            f"odrzucone: {counts['rejected']}; "
            f"do sprawdzenia: {counts['needs_review']}"
        )

        return {
            "agent": self.name,
            "decision": decision,
            "total": total,
            **counts
        }


if __name__ == "__main__":
    state = AgentState(target="https://example.com")
    state.verification_completed = True
    state.evidence = [
        {"status": "verified"},
        {"status": "verified"},
        {"status": "rejected"},
    ]

    result = ReviewerAgent().run(state)

    assert result["total"] == 3
    assert result["verified"] == 2
    assert result["rejected"] == 1
    assert result["decision"] == "contains_rejected_claims"
    assert state.review_completed is True
    assert state.history[-1]["agent"] == "reviewer_agent"

    print("PASS | Reviewer Agent: 5/5 testów OK")
