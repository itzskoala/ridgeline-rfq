
from pathlib import Path
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser

from readers import read_document

EMAIL_DIR = Path("data/dev/emails")
ATTACHMENT_DIR = Path("dev/attachments")


def load_emails():
    emails = []

    for email_path in sorted(EMAIL_DIR.glob("*.eml")):
        try:
            email_data = parse_email(email_path)
            emails.append(email_data)

        #TODO if email can't be parsed for whatever reason -> Send fully to AI model? + same goes for Attachments
        except Exception as error:
            emails.append({
                "filename": email_path.name,
                "parse_error": str(error),
                "full_email_text": None,
                "attachments": []
            })

    return emails


def parse_email(email_path):
    with open(email_path, "rb") as file:
        message = BytesParser(policy=policy.default).parse(file)

    body_text_parts = []
    body_html_parts = []

    body_html = None

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
    references = " ".join(references).split()

    readable_body = body_text

    if not readable_body and body_html:
        readable_body = html_to_text(body_html)

    full_email_text = f"""
    From: {message.get('From', '')}
    To: {message.get('To', '')}
    CC: {message.get('Cc', '')}
    Subject: {message.get('Subject', '')}
    Date: {message.get('Date', '')}

    {readable_body}
    """

    email_data = {
        "filename": Path(email_path).name,
        "sender": message.get("From"),
        "recipient": message.get("To"),
        "subject": message.get("Subject"),
        "date": message.get("Date"),

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
        Path(email_path).stem
    )

    return email_data


def extract_attachments(message, email_name):
    attachment_dir = ATTACHMENT_DIR / email_name
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
                attachment["markdown"] = read_document(str(attachment_path))
                attachment["extracted"] = True

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
