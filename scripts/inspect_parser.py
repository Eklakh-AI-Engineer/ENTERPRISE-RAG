import json

from app.parsing.pdf_parser import parse_pdf


def main():

    pages = parse_pdf("data/raw/sample.pdf")

    with open(
        "data/processed/sample_pages.json",
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            pages,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Saved {len(pages)} page records.")
    print("Output: data/processed/sample_pages.json")


if __name__ == "__main__":
    main()