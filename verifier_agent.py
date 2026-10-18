
from agent_orchestrator import AgentAction, AgentState
from analyst_agent import ask_model as _unused
import json
import urllib.request

from analyst_agent import API, MODEL


def verify_claim(fact: str, quote: str) -> dict:
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Oceń wyłącznie, czy podany cytat logicznie "
                    "potwierdza twierdzenie. Nie korzystaj z wiedzy "
                    "zewnętrznej. Odpowiedz w formacie JSON."
                )
            },
            {
                "role": "user",
                "content": json.dumps({
                    "twierdzenie": fact,
                    "cytat": quote
                }, ensure_ascii=False)
            }
        ],
        "format": {
            "type": "object",
            "properties": {
                "supported": {"type": "boolean"},
                "reason": {"type": "string"}
            },
            "required": ["supported", "reason"],
            "additionalProperties": False
        },
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

    answer = json.loads(result["message"]["content"])
    if type(answer.get("supported")) is not bool:
        raise ValueError("Niepoprawna odpowiedź weryfikatora")
    return answer


class VerifierAgent:
    name = "verifier_agent"

    def run(self, state: AgentState) -> dict:
        if not state.analysis_completed:
            raise ValueError("Analiza nie została zakończona")

        verified = 0
        rejected = 0
        needs_review = 0

        for item in state.evidence:
            if item.get("status") != "awaiting_verification":
                continue

            try:
                result = verify_claim(item["fact"], item["quote"])
                item["verification_reason"] = result["reason"]

                if result["supported"]:
                    item["status"] = "verified"
                    verified += 1
                else:
                    item["status"] = "rejected"
                    rejected += 1

            except Exception as exc:
                item["status"] = "needs_review"
                item["verification_reason"] = str(exc)
                needs_review += 1

        if needs_review:
            state.status = "verification_failed"
            state.record(
                self.name,
                AgentAction.VERIFY,
                f"Weryfikacja niekompletna; do sprawdzenia: {needs_review}"
            )
            raise RuntimeError(
                f"VerifierAgent: nie udało się zweryfikować {needs_review} twierdzeń"
            )

        state.verification_completed = True
        state.iteration += 1

        state.record(
            self.name,
            AgentAction.VERIFY,
            f"Potwierdzone: {verified}, odrzucone: {rejected}, "
            f"do sprawdzenia: {needs_review}"
        )

        return {
            "verified": verified,
            "rejected": rejected,
            "needs_review": needs_review
        }


if __name__ == "__main__":
    from unittest.mock import patch

    state = AgentState(target="https://example.com")
    state.analysis_completed = True
    state.evidence = [{
        "fact": "Firma ABC produkuje CRM",
        "quote": "Firma ABC produkuje systemy CRM.",
        "status": "awaiting_verification"
    }]

    with patch("__main__.verify_claim", return_value={
        "supported": True,
        "reason": "Cytat bezpośrednio potwierdza fakt"
    }):
        result = VerifierAgent().run(state)

    assert result["verified"] == 1
    assert state.evidence[0]["status"] == "verified"
    assert state.verification_completed is True

    print("PASS | Verifier Agent: 3/3 testów OK")
