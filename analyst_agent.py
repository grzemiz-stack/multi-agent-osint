import json
import urllib.request

from agent_orchestrator import AgentAction, AgentState

MODEL = "qwen3:30b-a3b-instruct-2507-q4_K_M"
API = "http://localhost:11434/api/chat"

FACT_SCHEMA = {
    "type": "object",
    "properties": {
        "fakty": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "fakt": {"type": "string"},
                    "dowod": {"type": "string"}
                },
                "required": ["fakt", "dowod"],
                "additionalProperties": False
            }
        }
    },
    "required": ["fakty"],
    "additionalProperties": False
}


def ask_model(text: str) -> dict:
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Wyodrębnij maksymalnie 5 faktów z dokumentu. "
                    "Najpierw wybierz dosłowny cytat ze źródła, a następnie sformułuj wyłącznie fakt bezpośrednio potwierdzony przez TEN SAM cytat. Nie łącz faktu z innym fragmentem dokumentu. Jeżeli cytat nie potwierdza całego faktu, pomiń tę parę. "
                    "Nie wymyślaj informacji. "
                    "Jeżeli brak dowodów, zwróć pustą listę."
                )
            },
            {"role": "user", "content": text[:12000]}
        ],
        "format": FACT_SCHEMA,
        "stream": False,
        "options": {"temperature": 0}
    }

    request = urllib.request.Request(
        API,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.load(response)

    return json.loads(result["message"]["content"])


class AnalystAgent:
    name = "analyst_agent"

    def run(self, state: AgentState) -> dict:
        if not state.findings:
            raise ValueError("Brak dokumentów do analizy")

        extracted = []
        errors = []

        for document in state.findings:
            url = document.get("url", "")
            content = document.get("content", "")

            if not content.strip():
                continue

            try:
                content = " ".join(content.split())
                result = ask_model(content)

                for item in result["fakty"]:
                    fact = item["fakt"]
                    quote = item["dowod"]

                    if not quote or quote not in content:
                        errors.append({
                            "url": url,
                            "error": "Cytat nie występuje w źródle",
                            "fact": fact
                        })
                        continue

                    extracted.append({
                        "url": url,
                        "fact": fact,
                        "quote": quote,
                        "status": "awaiting_verification"
                    })

            except Exception as exc:
                errors.append({"url": url, "error": str(exc)})

        state.evidence.extend(extracted)

        if errors and not extracted:
            state.status = "analysis_failed"
            state.record(
                self.name,
                AgentAction.ANALYZE,
                f"Analiza niekompletna; błędów: {len(errors)}; szczegóły: {errors}"
            )
            raise RuntimeError(f"AnalystAgent: analiza niekompletna: {errors}")

        state.analysis_completed = True
        state.iteration += 1

        state.record(
            self.name,
            AgentAction.ANALYZE,
            f"Wyodrębniono {len(extracted)} faktów; błędów: {len(errors)}"
        )

        return {
            "agent": self.name,
            "facts": len(extracted),
            "errors": errors
        }


if __name__ == "__main__":
    from unittest.mock import patch

    state = AgentState(target="https://example.com")
    state.findings.append({
        "url": "https://example.com",
        "content": "Firma ABC produkuje systemy CRM."
    })

    mocked = {
        "fakty": [{
            "fakt": "Firma ABC produkuje systemy CRM",
            "dowod": "Firma ABC produkuje systemy CRM."
        }]
    }

    with patch("__main__.ask_model", return_value=mocked):
        result = AnalystAgent().run(state)

    assert result["facts"] == 1
    assert result["errors"] == []
    assert state.evidence[0]["status"] == "awaiting_verification"
    assert state.evidence[0]["quote"] in state.findings[0]["content"]
    assert state.history[-1]["agent"] == "analyst_agent"

    print("PASS | Analyst Agent: 5/5 testów OK")
