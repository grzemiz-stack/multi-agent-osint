from safe_http import fetch_https
from html.parser import HTMLParser

URL = "https://example.com"

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.block_tags = {"p", "div", "section", "article", "header", "footer", "nav", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "br", "tr"}
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.block_tags and not self.skip:
            self.text.append("\n")
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in self.block_tags and not self.skip:
            self.text.append("\n")
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.text.append(data)


def collect(url):
    response = fetch_https(url)
    html = response["content"].decode("utf-8", errors="replace")

    parser = TextExtractor()
    parser.feed(html)

    return "".join(parser.text)


if __name__ == "__main__":
    content = collect(URL)
    print("ŹRÓDŁO:", URL)
    print("POBRANA TREŚĆ:")
    print(content[:3000])
