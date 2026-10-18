import unittest
from unittest.mock import patch

from agent_orchestrator import AgentState
from analyst_agent import AnalystAgent
from url_safety import normalize_url


class AgentReliabilityTests(unittest.TestCase):

    def test_normalize_markdown_url(self):
        address = "https:" + "//" + "example.com"
        markdown = "[" + address + "](" + address + ")"
        self.assertEqual(normalize_url(markdown), address)

    def test_reject_mismatched_markdown_url(self):
        first = "https:" + "//" + "example.com"
        second = "https:" + "//" + "other.com"
        markdown = "[" + first + "](" + second + ")"

        with self.assertRaises(ValueError):
            normalize_url(markdown)

    def test_ollama_failure_is_not_success(self):
        state = AgentState(target="test")
        state.findings.append({
            "url": "test-source",
            "content": "Firma ABC produkuje CRM."
        })

        with patch(
            "analyst_agent.ask_model",
            side_effect=ConnectionError("Ollama niedostępna")
        ):
            with self.assertRaises(RuntimeError):
                AnalystAgent().run(state)

        self.assertEqual(state.status, "analysis_failed")
        self.assertFalse(state.analysis_completed)
        self.assertIn(
            "Ollama niedostępna",
            state.history[-1]["reason"]
        )


    def test_verifier_failure_is_not_success(self):
        from verifier_agent import VerifierAgent

        state = AgentState(target="test")
        state.analysis_completed = True
        state.evidence = [{
            "fact": "Firma ABC produkuje CRM",
            "quote": "Firma ABC produkuje CRM.",
            "status": "awaiting_verification"
        }]

        with patch(
            "verifier_agent.verify_claim",
            side_effect=ConnectionError("Ollama niedostępna")
        ):
            with self.assertRaises(RuntimeError):
                VerifierAgent().run(state)

        self.assertEqual(state.status, "verification_failed")
        self.assertFalse(state.verification_completed)
        self.assertEqual(state.evidence[0]["status"], "needs_review")
        self.assertIn(
            "Ollama niedostępna",
            state.evidence[0]["verification_reason"]
        )


    def test_research_without_documents_stops(self):
        from agent_orchestrator import AgentAction, AgentOrchestrator
        from research_agent import ResearchAgent

        state = AgentState(target="test", max_iterations=5)
        orchestrator = AgentOrchestrator(state)

        self.assertEqual(orchestrator.next_action(), AgentAction.RESEARCH)

        with patch(
            "research_agent.validate_public_url",
            return_value={"url": "test"}
        ), patch(
            "research_agent.collect_site",
            return_value=([], ["Nie udało się pobrać strony"])
        ):
            ResearchAgent().run(state, max_pages=1)

        self.assertEqual(orchestrator.next_action(), AgentAction.FINISH)
        self.assertEqual(state.status, "research_failed")
        self.assertEqual(state.iteration, 1)
        self.assertEqual(len(state.findings), 0)


    def test_research_failure_report_preserves_error(self):
        import json
        import tempfile
        from pathlib import Path
        import run_agents

        message = "Symulowana awaria pobierania"

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                run_agents, "REPORTS_DIR", Path(directory)
            ):
                with patch(
                    "research_agent.collect_site",
                    return_value=([], [message])
                ):
                    with self.assertRaises(RuntimeError):
                        run_agents.run("https://example.com", max_pages=1)

            report_path = Path(directory) / "latest_report.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["status"], "research_failed")
        self.assertEqual(report["error"], message)
        self.assertEqual(report["iterations"], 1)
        self.assertEqual(report["documents"], 0)


    def test_partial_research_report(self):
        import json
        import tempfile
        from pathlib import Path
        import run_agents

        message = "Nie udało się pobrać drugiej podstrony"
        document = {
            "url": "https://example.com",
            "content": "Example Domain",
            "characters": 14,
        }

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                run_agents, "REPORTS_DIR", Path(directory)
            ):
                with patch(
                    "research_agent.collect_site",
                    return_value=([document], [message])
                ), patch(
                    "analyst_agent.ask_model",
                    return_value={"fakty": []}
                ):
                    report = run_agents.run(
                        "https://example.com", max_pages=2
                    )

            saved = json.loads(
                (Path(directory) / "latest_report.json")
                .read_text(encoding="utf-8")
            )

        for result in (report, saved):
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["source_completeness"], "partial")
            self.assertEqual(
                result["review_decision"], "insufficient_evidence"
            )
            self.assertEqual(result["research_errors"], [message])
            self.assertEqual(result["documents"], 1)


    def test_iteration_limit_respects_completion(self):
        from agent_orchestrator import AgentAction, AgentOrchestrator

        completed = AgentState(target="test", max_iterations=5)
        completed.findings = [{"content": "Dokument testowy"}]
        completed.analysis_completed = True
        completed.verification_completed = True
        completed.review_completed = True
        completed.iteration = 5

        action = AgentOrchestrator(completed).next_action()
        self.assertEqual(action, AgentAction.FINISH)
        self.assertEqual(completed.status, "completed")

        unfinished = AgentState(target="test", max_iterations=5)
        unfinished.findings = [{"content": "Dokument testowy"}]
        unfinished.analysis_completed = True
        unfinished.iteration = 5

        action = AgentOrchestrator(unfinished).next_action()
        self.assertEqual(action, AgentAction.FINISH)
        self.assertEqual(unfinished.status, "iteration_limit")


    def test_failed_agent_records_duration(self):
        import json
        import tempfile
        from contextlib import ExitStack
        from pathlib import Path
        from unittest.mock import patch
        import run_agents

        document = {
            "url": "https://example.com",
            "content": "Example Domain",
            "characters": 14,
        }

        with tempfile.TemporaryDirectory() as tmp:
            with ExitStack() as stack:
                stack.enter_context(patch(
                    "research_agent.collect_site",
                    return_value=([document], [])
                ))
                stack.enter_context(patch(
                    "analyst_agent.AnalystAgent.run",
                    side_effect=RuntimeError("TEST: awaria agenta AI")
                ))
                stack.enter_context(patch.object(
                    run_agents, "REPORTS_DIR", Path(tmp)
                ))

                with self.assertRaises(RuntimeError):
                    run_agents.run("https://example.com", max_pages=1)

            report = json.loads(
                (Path(tmp) / "latest_report.json")
                .read_text(encoding="utf-8")
            )

            self.assertNotEqual(report["status"], "completed")
            self.assertEqual(len(report["results"]), 2)

            failed = report["results"][-1]
            self.assertEqual(failed["action"], "analyze")
            self.assertGreaterEqual(failed["duration_ms"], 0)
            self.assertEqual(failed["agent"], "analyst_agent")
            self.assertEqual(failed["error"], "TEST: awaria agenta AI")
            self.assertEqual(report["error"], "TEST: awaria agenta AI")


if __name__ == "__main__":
    unittest.main()
