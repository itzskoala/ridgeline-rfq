#main.py

import argparse
import json
import logging
import os
import warnings
from pathlib import Path

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

from ingest import load_emails
from ai_extractor import extract_email
from schemas import validate_email_result


def fallback_result(reason):
    return {
        "classification": "rfq",
        "revises": None,
        "duplicate_of": None,
        "needs_review": True,
        "review_reason": reason,
        "line_items": []
    }


def parse_emails(email_dir, output_file):
    emails = load_emails(Path(email_dir))
    inbox = []

    for email in emails:
        email_markdown = email.get("full_email_text") or ""

        parent_email_id = email.get("parent_email_id")

        if parent_email_id:
            email_markdown += f"\n\nThread context: this email replies to earlier email {parent_email_id}."

        attachment_failures = []

        for attachment in email.get("attachments", []):
            markdown = attachment.get("markdown")
            filename = attachment.get("filename", "unknown")

            if markdown:
                email_markdown += f"\n\nAttachment: {filename}\n{markdown}"
            else:
                error = attachment.get("extraction_error") or "No readable content extracted"
                email_markdown += f"\n\nAttachment: {filename}\nATTACHMENT COULD NOT BE READ: {error}"
                attachment_failures.append(filename)

        inbox.append({
            **email,
            "email_markdown": email_markdown,
            "attachment_failures": attachment_failures
        })

    inbox.sort(
        key=lambda email: email.get("date_timestamp") or 0
    )

    results = {}
    total_tokens_all = 0
    total_cost_all = 0.0

    for email in inbox:
        email_id = email["id"]

        if email.get("parse_error"):
            result = fallback_result(f"Email failed to parse: {email['parse_error']}")
            searched = False
            total_tokens = 0
            cost = 0.0

        else:
            try:
                extraction = extract_email(
                    email_markdown=email["email_markdown"],
                    current_email=email,
                    inbox=inbox,
                    prior_results=results
                )

                result = extraction["result"]
                searched = extraction.get(
                    "searched_prior_requests",
                    bool(extraction.get("tool_calls"))
                )
                total_tokens = extraction["usage"]["total_tokens"]
                cost = extraction["usage"]["estimated_cost"]

            except Exception as error:
                result = fallback_result(f"Extraction failed: {error}")
                searched = False
                total_tokens = 0
                cost = 0.0

        result = validate_email_result(result, email.get("attachment_failures", []))

        results[email_id] = result
        total_tokens_all += total_tokens
        total_cost_all += cost

        print(
            f"{email_id}: "
            f"{result['classification']} | "
            f"Searched prior requests: {searched} | "
            f"Tokens: {total_tokens} | "
            f"Cost: ${cost:.6f}"
        )

    print(f"Total tokens: {total_tokens_all:,} | Total estimated cost: ${total_cost_all:.4f}")

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
