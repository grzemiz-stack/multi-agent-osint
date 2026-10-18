from url_safety import normalize_url
import argparse
import json
from time import perf_counter
from datetime import datetime, timezone
from pathlib import Path

from agent_orchestrator import AgentAction, AgentOrchestrator, AgentState
from research_agent import ResearchAgent
from analyst_agent import AnalystAgent
from verifier_agent import VerifierAgent
from reviewer_agent import ReviewerAgent


REPORTS_DIR = Path("runs") / "agent_demo"

def run(target: str, max_pages: int = 2):
    target = normalize_url(target)
    state = AgentState(target=target, max_iterations=5)
    orchestrator = AgentOrchestrator(state)

    agents = {
        AgentAction.RESEARCH: ResearchAgent(),
        AgentAction.ANALYZE: AnalystAgent(),
        AgentAction.VERIFY: VerifierAgent(),
        AgentAction.REVIEW: ReviewerAgent(),
    }

    results = []

    failure = None

    try:
        for _ in range(state.max_iterations + 2):
            action = orchestrator.next_action()
            print(f"\nORCHESTRATOR -> {action.value}", flush=True)

            if action == AgentAction.FINISH:
                break

            agent = agents[action]
            started = perf_counter()

            try:
                if action == AgentAction.RESEARCH:
                    result = agent.run(state, max_pages=max_pages)
                else:
                    result = agent.run(state)
            except Exception as exc:
                results.append({
                    "action": action.value,
                    "agent": agent.name,
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                    "result": {},
                    "error": str(exc),
                })
                raise

            duration_ms = round((perf_counter() - started) * 1000, 2)
            results.append({
                "action": action.value,
                "agent": agent.name,
                "duration_ms": duration_ms,
                "result": result,
            })
            print("WYNIK:", result, flush=True)
        else:
            raise RuntimeError("Przekroczono limit kroków orkiestracji")

    except Exception as exc:
        failure = exc
        if state.status not in ("analysis_failed", "verification_failed"):
            state.status = "failed"

    research_errors = [
        str(error)
        for item in results
        if item["action"] == "research"
        for error in item["result"].get("errors", [])
    ]

    review_decision = next(
        (
            item["result"].get("decision")
            for item in reversed(results)
            if item["action"] == "review"
        ),
        None,
    )

    report = {
        "target": target,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": state.status,
        "iterations": state.iteration,
        "documents": len(state.findings),
        "evidence": state.evidence,
        "history": state.history,
        "results": results,
        "research_errors": research_errors,
        "source_completeness": (
            "partial" if research_errors else "complete"
        ),
        "review_decision": review_decision,
        "error": (
            str(failure)
            if failure is not None
            else (
                "; ".join(
                    str(error)
                    for item in results
                    if item["action"] == "research"
                    for error in item["result"].get("errors", [])
                ) or f"Przebieg nieukończony: {state.status}"
            )
            if state.status != "completed"
            else None
        ),
    }

    output_dir = Path(REPORTS_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    from uuid import uuid4

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"{timestamp}_{uuid4().hex[:8]}"
    report["run_id"] = run_id

    output = output_dir / f"{run_id}.json"
    payload = json.dumps(report, ensure_ascii=False, indent=2)

    output.write_text(payload, encoding="utf-8")
    (output_dir / "latest_report.json").write_text(
        payload, encoding="utf-8"
    )

    print(f"\nSTATUS: {state.status}")
    print(f"RAPORT: {output}")
    print(f"FAKTY: {len(state.evidence)}")

    if failure is not None:
        raise RuntimeError(
            f"Przebieg zakończony błędem; raport zapisany: {output}"
        ) from failure

    if state.status != "completed":
        raise RuntimeError(
            f"Przebieg nieukończony ({state.status}); raport: {output}"
        )

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Lokalny system wieloagentowy OSINT"
    )
    parser.add_argument("url")
    parser.add_argument("--pages", type=int, default=2)
    args = parser.parse_args()

    run(args.url, max_pages=args.pages)
