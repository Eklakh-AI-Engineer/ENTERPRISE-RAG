from app.parsing.pdf_parser import parse_pdf


def main():

    pdf_path = "data/raw/sample.pdf"

    pages = parse_pdf(pdf_path)

    print(f"\nDocument pages extracted: {len(pages)}")

    for page in pages[:3]:

        print("\n" + "=" * 80)
        print(f"Document : {page['document_id']}")
        print(f"Source   : {page['source']}")
        print(f"Page     : {page['page']}")
        print("=" * 80)

        text = page["text"]

        if text:
            print(text[:1500])
        else:
            print("[NO NATIVE TEXT FOUND]")


if __name__ == "__main__":
    main()