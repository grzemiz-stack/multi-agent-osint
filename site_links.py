from html.parser import HTMLParser
from safe_http import fetch_https
from urllib.parse import urljoin, urlparse, urlunparse

DEFAULT_URL = "https://agentro.pl"
MAX_PAGES = 20


class LinkParser(HTMLParser):
    def __init__(self, base_url, hostname):
        super().__init__()
        self.base_url = base_url
        self.hostname = hostname
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return

        href = dict(attrs).get("href")
        if not href:
            return

        url = urljoin(self.base_url, href)
        parsed = urlparse(url)

        if parsed.scheme != "https":
            return

        hostname = (parsed.hostname or "").lower()

        if hostname.removeprefix("www.") != self.hostname:
            return

        path = parsed.path.rstrip("/") or "/"

        if path == "/polityka-prywatnosci.html":
            return

        clean = urlunparse((
            "https",
            parsed.netloc.lower(),
            path,
            "",
            "",
            ""
        ))

        self.links.add(clean)


def discover_links(base_url=DEFAULT_URL, max_pages=MAX_PAGES):
    parsed = urlparse(base_url)

    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Wymagany poprawny adres HTTPS")

    if parsed.username or parsed.password or parsed.port:
        raise ValueError("Adres nie może zawierać danych logowania ani portu")

    if not 1 <= max_pages <= 100:
        raise ValueError("Limit stron musi wynosić od 1 do 100")

    hostname = parsed.hostname.lower().removeprefix("www.")

    response = fetch_https(base_url)
    final_url = response["url"]

    final_host = (urlparse(final_url).hostname or "").lower()
    if final_host.removeprefix("www.") != hostname:
        raise ValueError("Przekierowanie poza wskazaną domenę")

    html = response["content"]

    parser = LinkParser(final_url, hostname)
    parser.feed(html.decode("utf-8", errors="replace"))

    start = urlparse(final_url)
    start_path = start.path.rstrip("/") or "/"

    homepage = urlunparse((
        "https",
        start.netloc.lower(),
        start_path,
        "",
        "",
        ""
    ))

    links = sorted(parser.links - {homepage})
    return [homepage] + links[:max_pages - 1]


if __name__ == "__main__":
    import argparse

    cli = argparse.ArgumentParser()
    cli.add_argument("--url", default=DEFAULT_URL)
    cli.add_argument("--max-pages", type=int, default=MAX_PAGES)
    args = cli.parse_args()

    links = discover_links(args.url, args.max_pages)

    print("Stron do analizy:", len(links))
    for i, url in enumerate(links, 1):
        print(f"{i}. {url}")
