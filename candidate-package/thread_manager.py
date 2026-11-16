#thread_manager.py

#OH MY GOD! The program needs to be able to tell frq revisions/email treads! we already record email ids so now have 
#to create threads off of that lol

# message_id, in_reply_to, references, and date

'''
There are three main signals to use:
1. In-Reply-To — the strongest direct signal. An email explicitly replies to another email's Message-ID.
2. References — identifies earlier messages in the conversation, even if the email is several replies deep.
3. Explicit email references — potentially an email mentions an earlier request by its ID, such as E003, or references a prior quote/request. This is weaker and may need separate handling.

'''

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def normalize_message_id(value):
    if not value:
        return None

    if isinstance(value, list):
        value = value[0] if value else None

    if not value:
        return None

    return str(value).strip().strip("<>").lower()


def parse_date(value):
    if not value:
        return datetime.max.replace(tzinfo=timezone.utc)

    if isinstance(value, datetime):
        date = value
    else:
        try:
            date = parsedate_to_datetime(str(value))
        except (TypeError, ValueError, OverflowError):
            try:
                date = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                return datetime.max.replace(tzinfo=timezone.utc)

    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)

    return date


def get_references(value):
    if not value:
        return []

    if isinstance(value, str):
        value = value.split()

    return [
        normalized
        for item in value
        if (normalized := normalize_message_id(item))
    ]


def build_threads(emails):
    emails = [email.copy() for email in emails]

    parents = list(range(len(emails)))

    def find(index):
        if parents[index] != index:
            parents[index] = find(parents[index])

        return parents[index]

    def union(first, second):
        first_root = find(first)
        second_root = find(second)

        if first_root != second_root:
            parents[second_root] = first_root

    message_lookup = {}

    for index, email in enumerate(emails):
        message_id = normalize_message_id(email.get("message_id"))

        if message_id:
            message_lookup.setdefault(message_id, index)

    for index, email in enumerate(emails):
        in_reply_to = normalize_message_id(email.get("in_reply_to"))

        if in_reply_to in message_lookup:
            union(index, message_lookup[in_reply_to])

        references = get_references(email.get("references"))

        for reference in references:
            if reference in message_lookup:
                union(index, message_lookup[reference])

    groups = {}

    for index in range(len(emails)):
        root = find(index)
        groups.setdefault(root, []).append(index)

    threads = {}

    for indexes in groups.values():
        indexes.sort(
            key=lambda index: (
                parse_date(emails[index].get("date")),
                str(emails[index].get("id", ""))
            )
        )

        thread_id = emails[indexes[0]].get("id")

        if not thread_id:
            thread_id = emails[indexes[0]].get("message_id")

        thread_email_ids = [
            emails[index].get("id")
            for index in indexes
        ]

        for position, index in enumerate(indexes):
            email = emails[index]

            in_reply_to = normalize_message_id(
                email.get("in_reply_to")
            )

            parent_index = message_lookup.get(in_reply_to)

            email["thread_id"] = thread_id
            email["thread_position"] = position
            email["thread_size"] = len(indexes)
            email["thread_email_ids"] = thread_email_ids
            email["parent_email_id"] = (
                emails[parent_index].get("id")
                if parent_index is not None
                else None
            )

        threads[thread_id] = [
            emails[index] for index in indexes
        ]

    return emails, threads


def get_thread(emails, email_id):
    for email in emails:
        if email.get("id") == email_id:
            thread_id = email.get("thread_id")

            return [
                item
                for item in emails
                if item.get("thread_id") == thread_id
            ]

    return []
