#main.py 

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

from pipeline.email_parser import load_emails, extract_attachments
from pipeline.document_reader import read_documents
from pipeline.extractor import extract_with_ai
from pipeline.validator import validate


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


def save_json(data, output_file):

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False
        ) as file:
            temp_path = Path(file.name)
            json.dump(data, file, indent=2, ensure_ascii=False)

        os.replace(temp_path, output_path)

    except Exception:
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise


def process_email(email):

    email_id = email["id"]

    try:
        attachments = extract_attachments(email)

    except Exception:
        logger.exception("Attachment extraction failed for %s", email_id)
        attachments = []

    try:
        documents = read_documents(attachments)

    except Exception:
        logger.exception("Document processing failed for %s", email_id)
        documents = []

    try:
        extracted_data = extract_with_ai(email, documents)
        validated_data = validate(extracted_data)

        return validated_data

    except Exception:
        logger.exception("Email processing failed for %s", email_id)

        return {
            "classification": "other",
            "revises": None,
            "duplicate_of": None,
            "needs_review": False,
            "review_reason": None,
            "line_items": []
        }


def parse_emails(email_dir, output_file):

    email_dir = Path(email_dir)

    if not email_dir.is_dir():
        raise NotADirectoryError(
            f"Email directory does not exist: {email_dir}"
        )

    emails = load_emails(email_dir)

    if not emails:
        raise ValueError(f"No emails found in {email_dir}")

    results = {}
    failed = 0

    for email in emails:

        email_id = email["id"]

        try:
            results[email_id] = process_email(email)

        except Exception:
            logger.exception("Unexpected failure processing %s", email_id)
            failed += 1

            results[email_id] = {
                "classification": "other",
                "revises": None,
                "duplicate_of": None,
                "needs_review": False,
                "review_reason": None,
                "line_items": []
            }

    save_json(results, output_file)

    logger.info("Processed: %d", len(results))
    logger.info("Failed: %d", failed)
    logger.info("Output: %s", output_file)

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

    parse_command.add_argument(
        "--emails",
        required=True
    )

    parse_command.add_argument(
        "--out",
        required=True
    )

    args = parser.parse_args()

    try:
        if args.command == "parse":
            parse_emails(args.emails, args.out)

    except Exception:
        logger.exception("Pipeline execution failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
