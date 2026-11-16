
import argparse
import json
from pathlib import Path

from ingest import load_emails, extract_attachments, read_documents
from readers import read_document

def parse_emails(email_dir, output_file):
    emails = load_emails(Path(email_dir))
    results = {}

    for email in emails:
        attachments = extract_attachments(email)
        documents = read_documents(attachments)

        results[email["id"]] = {
            "email": email,
            "attachments": attachments,
            "documents": documents
        }

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Ridgeline RFQ email processing pipeline"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )

    parse_command = subparsers.add_parser("parse")
    parse_command.add_argument("--emails", required=True)
    parse_command.add_argument("--out", required=True)

    args = parser.parse_args()

    if args.command == "parse":
        parse_emails(args.emails, args.out)


if __name__ == "__main__":
    main()
