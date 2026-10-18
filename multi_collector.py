import argparse
import json
import time

from collector import collect
from site_links import discover_links
from run_workspace import create_workspace


def collect_site(url, max_pages=20):
    urls = discover_links(url, max_pages=max_pages)
    documents = []
    errors = []

    for index, page_url in enumerate(urls, 1):
        print(f"[{index}/{len(urls)}] Pobieram: {page_url}")

        try:
            content = collect(page_url)

            documents.append({
                "url": page_url,
                "content": content,
                "characters": len(content)
            })

            print(f"  Pobrano znaków: {len(content)}")

        except Exception as error:
            print(f"  BŁĄD: {error}")
            errors.append({
                "url": page_url,
                "error": str(error)
            })

        if index < len(urls):
            time.sleep(1)

    return documents, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://agentro.pl")
    parser.add_argument("--max-pages", type=int, default=20)
    args = parser.parse_args()

    if not 1 <= args.max_pages <= 100:
        parser.error("--max-pages musi wynosić od 1 do 100")

    # Najpierw sprawdzamy dostępność strony i odkrywamy linki.
    # Dopiero potem tworzymy katalog uruchomienia.
    from url_safety import validate_public_url
    validate_public_url(args.url)

    workspace = create_workspace(args.url)

    documents, errors = collect_site(
        args.url,
        max_pages=args.max_pages
    )

    output = workspace / "collected_pages.json"
    output.write_text(
        json.dumps(documents, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    error_output = workspace / "collection_errors.json"
    error_output.write_text(
        json.dumps(errors, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\nPobrano dokumentów:", len(documents))
    print("Błędów:", len(errors))
    print("KATALOG:", workspace)
    print("RAPORT:", output)


if __name__ == "__main__":
    main()
