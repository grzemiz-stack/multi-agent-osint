import ipaddress
import socket
from urllib.parse import urlparse



def normalize_url(url):
    import re

    if not isinstance(url, str):
        raise ValueError("URL musi być tekstem")

    url = url.strip()

    match = re.fullmatch(r"\[(https://[^\]\s]+)\]\((https://[^\)\s]+)\)", url)

    if match:
        if match.group(1) != match.group(2):
            raise ValueError("Różne adresy w linku Markdown")
        url = match.group(1)

    return url


def validate_public_url(url):
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise ValueError("Dozwolone są tylko adresy HTTPS")

    if not parsed.hostname:
        raise ValueError("Brak nazwy hosta")

    if parsed.username or parsed.password:
        raise ValueError("Dane logowania w URL są zabronione")

    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("Niepoprawny port") from error

    if port not in (None, 443):
        raise ValueError("Niedozwolony port")

    hostname = parsed.hostname

    try:
        addresses = socket.getaddrinfo(
            hostname, 443, type=socket.SOCK_STREAM
        )
    except socket.gaierror as error:
        raise ValueError(
            f"Nie można rozwiązać domeny: {hostname}"
        ) from error

    if not addresses:
        raise ValueError("Domena nie ma adresów IP")

    resolved = set()

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        resolved.add(str(ip))

        if not ip.is_global:
            raise ValueError(
                f"Adres niepubliczny jest zabroniony: {ip}"
            )

    return {
        "url": url,
        "hostname": hostname,
        "addresses": sorted(resolved)
    }


if __name__ == "__main__":
    for url in [
        "https://127.0.0.1",
        "https://192.168.1.1",
        "https://localhost"
    ]:
        try:
            validate_public_url(url)
            print("FAIL:", url)
        except ValueError:
            print("PASS - zablokowano:", url)
