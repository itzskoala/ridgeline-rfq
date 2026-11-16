
from pathlib import Path
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from datetime import timezone

from readers import read_document
from thread_manager import build_threads


def load_emails(email_dir):
    email_dir = Path(email_dir)
    attachment_dir = email_dir.parent / "attachments"
    emails = []

    for email_path in sorted(email_dir.glob("*.eml")):
        try:
            email_data = parse_email(email_path, attachment_dir)
            emails.append(email_data)

        except Exception as error:
            emails.append({
                "id": email_path.stem,
                "filename": email_path.name,
                "parse_error": str(error),
                "full_email_text": None,
                "attachments": []
            })

    emails, _ = build_threads(emails)

    return emails


def parse_email(email_path, attachment_dir):
    with open(email_path, "rb") as file:
        message = BytesParser(policy=policy.default).parse(file)

    body_text_parts = []
    body_html_parts = []

    for part in message.walk():
        if part.is_multipart():
            continue

        if part.get_filename():
            continue

        if part.get_content_disposition() == "attachment":
            continue

        content_type = part.get_content_type()

        if content_type == "text/plain":
            text = get_part_text(part)
            if text:
                body_text_parts.append(text)

        elif content_type == "text/html":
            html = get_part_text(part)
            if html:
                body_html_parts.append(html)

    body_text = "\n\n".join(body_text_parts)
    body_html = "\n\n".join(body_html_parts)

    message_id = message.get("Message-ID")
    in_reply_to = message.get("In-Reply-To")

    references = message.get_all("References", [])
    references = " ".join(str(reference) for reference in references).split()

    date = message.get("Date")
    date_timestamp = parse_email_date(date)

    readable_body = body_text

    if not readable_body and body_html:
        readable_body = html_to_text(body_html)

    full_email_text = "\n".join([
        f"From: {message.get('From', '')}",
        f"To: {message.get('To', '')}",
        f"CC: {message.get('Cc', '')}",
        f"Subject: {message.get('Subject', '')}",
        f"Date: {date or ''}",
        "",
        readable_body
    ])

    email_data = {
        "id": Path(email_path).stem,
        "filename": Path(email_path).name,
        "sender": message.get("From"),
        "recipient": message.get("To"),
        "subject": message.get("Subject"),
        "date": date,
        "date_timestamp": date_timestamp,
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "references": references,
        "body_text": body_text,
        "body_html": body_html,
        "full_email_text": full_email_text.strip(),
        "attachments": []
    }

    email_data["attachments"] = extract_attachments(
        message,
        Path(email_path).stem,
        attachment_dir
    )

    return email_data


def parse_email_date(date):
    if not date:
        return None

    try:
        parsed_date = parsedate_to_datetime(date)

        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)

        return parsed_date.timestamp()

    except (TypeError, ValueError, OverflowError):
        return None


def extract_attachments(message, email_name, attachment_dir):
    attachment_dir = Path(attachment_dir) / email_name
    attachment_dir.mkdir(parents=True, exist_ok=True)

    attachments = []
    attachment_count = 0

    for part in message.walk():
        if part.is_multipart():
            continue

        filename = part.get_filename()
        disposition = part.get_content_disposition()
        content_id = part.get("Content-ID")

        is_attachment = (
            filename is not None
            or disposition == "attachment"
            or (disposition == "inline" and content_id is not None)
        )

        if not is_attachment:
            continue

        attachment_count += 1

        if not filename:
            filename = f"inline_attachment_{attachment_count}.bin"

        filename = Path(filename).name
        attachment_path = attachment_dir / f"{attachment_count:02d}_{filename}"

        try:
            content = part.get_payload(decode=True)

            if content is None:
                raise ValueError("Could not decode attachment content")

            attachment_path.write_bytes(content)

            attachment = {
                "filename": filename,
                "content_type": part.get_content_type(),
                "path": str(attachment_path),
                "extracted": False,
                "markdown": None,
                "extraction_error": None
            }

            try:
                document = read_document(str(attachment_path))

                if isinstance(document, dict):
                    markdown = document.get("content") or ""
                    status = str(document.get("status", "")).lower()
                    error = document.get("error")

                    attachment["markdown"] = markdown
                    attachment["extracted"] = bool(markdown) and status not in {
                        "error", "failed", "unsupported"
                    }

                    if not attachment["extracted"]:
                        attachment["extraction_error"] = error or status or "No readable content extracted"

                else:
                    attachment["markdown"] = document
                    attachment["extracted"] = bool(document)

                    if not attachment["extracted"]:
                        attachment["extraction_error"] = "No readable content extracted"

            except Exception as error:
                attachment["extraction_error"] = str(error)

            attachments.append(attachment)

        except Exception as error:
            attachments.append({
                "filename": filename,
                "content_type": part.get_content_type(),
                "path": None,
                "extracted": False,
                "markdown": None,
                "extraction_error": str(error)
            })

    return attachments


def get_part_text(part):
    try:
        return part.get_content()
    except Exception:
        return ""


def html_to_text(html):
    parser = HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text()


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def get_text(self):
        return " ".join(self.text)
