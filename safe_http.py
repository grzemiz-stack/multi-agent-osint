import gzip
import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urljoin, urlparse

from url_safety import validate_public_url

MAX_BYTES = 2_000_000
MAX_REDIRECTS = 5
TIMEOUT = 15


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname, address, timeout=TIMEOUT):
        super().__init__(
            hostname,
            port=443,
            timeout=timeout,
            context=ssl.create_default_context()
        )
        self.pinned_address = address

    def connect(self):
        raw = socket.create_connection(
            (self.pinned_address, 443),
            self.timeout
        )
        try:
            self.sock = self._context.wrap_socket(
                raw,
                server_hostname=self.host
            )
        except Exception:
            raw.close()
            raise


def fetch_https(url, max_bytes=MAX_BYTES):
    if not 1 <= max_bytes <= MAX_BYTES:
        raise ValueError("Nieprawidłowy limit pobierania")

    visited = set()

    for _ in range(MAX_REDIRECTS + 1):
        if url in visited:
            raise ValueError("Wykryto pętlę przekierowań")

        visited.add(url)

        validated = validate_public_url(url)
        parsed = urlparse(url)

        addresses = validated["addresses"]
        if not addresses:
            raise ValueError("Brak zweryfikowanego adresu IP")

        address = addresses[0]

        if not ipaddress.ip_address(address).is_global:
            raise ValueError("Niedozwolony adres IP")

        connection = PinnedHTTPSConnection(
            parsed.hostname,
            address
        )

        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        try:
            connection.request(
                "GET",
                path,
                headers={
                    "Host": parsed.hostname,
                    "User-Agent": "OSINTLab/0.2",
                    "Accept": "text/html, text/plain",
                    "Accept-Encoding": "gzip, identity"
                }
            )

            response = connection.getresponse()

            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location:
                    raise ValueError("Przekierowanie bez Location")

                url = urljoin(url, location)
                continue

            if response.status != 200:
                raise ValueError(
                    f"HTTP {response.status}: {url}"
                )

            content_type = response.getheader(
                "Content-Type", ""
            ).lower()

            if not (
                "text/html" in content_type
                or "text/plain" in content_type
            ):
                raise ValueError(
                    f"Niedozwolony Content-Type: {content_type}"
                )

            body = response.read(max_bytes + 1)

            if len(body) > max_bytes:
                raise ValueError("Przekroczono limit pobierania")

            encoding = response.getheader(
                "Content-Encoding", "identity"
            ).strip().lower()

            if encoding == "gzip":
                import zlib

                decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
                decoded = decoder.decompress(body, max_bytes + 1)

                if len(decoded) > max_bytes or decoder.unconsumed_tail:
                    raise ValueError("Przekroczono limit po dekompresji")

                decoded += decoder.flush(max_bytes + 1 - len(decoded))

                if len(decoded) > max_bytes:
                    raise ValueError("Przekroczono limit po dekompresji")

                if not decoder.eof or decoder.unused_data:
                    raise ValueError("Nieprawidłowe dane GZIP")

                body = decoded

            elif encoding not in ("", "identity"):
                raise ValueError(
                    f"Nieobsługiwana kompresja: {encoding}"
                )

            return {
                "url": url,
                "content": body,
                "content_type": content_type,
                "status": response.status,
                "ip": address
            }

        finally:
            connection.close()

    raise ValueError("Przekroczono limit przekierowań")


if __name__ == "__main__":
    print("Moduł safe_http.py gotowy.")
