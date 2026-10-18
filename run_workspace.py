import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent
RUNS = BASE / "runs"


def create_workspace(url):
    parsed = urlparse(url)

    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Wymagany adres HTTPS z domeną")

    hostname = parsed.hostname.lower().removeprefix("www.")

    if not re.fullmatch(r"[a-z0-9.-]+", hostname):
        raise ValueError("Niepoprawna nazwa domeny")

    if hostname.startswith(".") or ".." in hostname:
        raise ValueError("Niepoprawna nazwa domeny")

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    folder = RUNS / hostname / timestamp
    folder.mkdir(parents=True, exist_ok=False)

    metadata = {
        "url": url,
        "hostname": hostname,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "created"
    }

    (folder / "run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return folder


if __name__ == "__main__":
    from tempfile import TemporaryDirectory
    from unittest.mock import patch

    with TemporaryDirectory() as tmp:
        with patch(__name__ + ".RUNS", Path(tmp)):
            first = create_workspace("https://agentro.pl")
            second = create_workspace("https://example.com")

            assert first.exists()
            assert second.exists()
            assert first != second
            assert (first / "run.json").exists()
            assert (second / "run.json").exists()

            print("PASS - oddzielne katalogi")
            print("PASS - metadane uruchomienia")
            print("PASS - brak nadpisywania")
            print("TESTOWY KATALOG 1:", first)
            print("TESTOWY KATALOG 2:", second)
