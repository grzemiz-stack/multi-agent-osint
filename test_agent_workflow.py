from unittest.mock import patch

from agent_orchestrator import AgentAction, AgentOrchestrator, AgentState
from research_agent import ResearchAgent


def test_research_workflow():
    state = AgentState(target="https://example.com", max_iterations=3)
    orchestrator = AgentOrchestrator(state)

    action = orchestrator.next_action()
    assert action == AgentAction.RESEARCH

    documents = [{
        "url": "https://example.com/",
        "content": "Example Domain",
        "characters": 14,
    }]

    with patch("research_agent.validate_public_url"), patch(
        "research_agent.collect_site",
        return_value=(documents, []),
    ) as collector:
        result = ResearchAgent().run(state, max_pages=1)

    collector.assert_called_once_with(
        "https://example.com",
        max_pages=1,
    )

    assert result["documents"] == 1
    assert state.iteration == 1
    assert len(state.findings) == 1

    next_action = orchestrator.next_action()
    assert next_action == AgentAction.ANALYZE

    assert [entry["agent"] for entry in state.history] == [
        "orchestrator",
        "research_agent",
        "orchestrator",
    ]

    print("PASS | Orchestrator -> Research Agent -> Orchestrator")
    print("PIERWSZA AKCJA:", action.value)
    print("POBRANE DOKUMENTY:", len(state.findings))
    print("NASTĘPNA AKCJA:", next_action.value)
    print("ZDARZENIA W HISTORII:", len(state.history))


if __name__ == "__main__":
    test_research_workflow()
