from agent_orchestrator import AgentAction, AgentState
from multi_collector import collect_site
from url_safety import validate_public_url


class ResearchAgent:
    name = "research_agent"

    def run(self, state: AgentState, max_pages: int = 3) -> dict:
        if not 1 <= max_pages <= 100:
            raise ValueError("max_pages musi wynosić od 1 do 100")

        validate_public_url(state.target)
        state.iteration += 1

        documents, errors = collect_site(
            state.target,
            max_pages=max_pages,
        )

        state.findings.extend(documents)

        state.record(
            self.name,
            AgentAction.RESEARCH,
            (
                f"Pobrano {len(documents)} dokumentów; błędów: {len(errors)}"
                + (f"; szczegóły: {errors!r}" if errors else "")
            ),
        )

        return {
            "agent": self.name,
            "documents": len(documents),
            "errors": errors,
            "next_action": (
                AgentAction.ANALYZE.value
                if documents
                else AgentAction.FINISH.value
            ),
        }


if __name__ == "__main__":
    from unittest.mock import patch

    state = AgentState(target="https://example.com")

    documents = [{
        "url": "https://example.com",
        "content": "Example Domain",
        "characters": 14,
    }]

    with patch(
        "__main__.validate_public_url"
    ), patch(
        "__main__.collect_site",
        return_value=(documents, []),
    ):
        result = ResearchAgent().run(state, max_pages=1)

    assert result["documents"] == 1
    assert result["next_action"] == "analyze"
    assert state.iteration == 1
    assert len(state.findings) == 1
    assert state.history[-1]["agent"] == "research_agent"

    print("PASS | Research Agent: 5/5 testów OK")
