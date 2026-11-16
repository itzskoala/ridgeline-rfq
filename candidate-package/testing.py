import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path

from schemas import validate_email_result
from thread_manager import build_threads
from ai_extractor import cache_key, find_request_candidates
import main


class SchemaPolicyTests(unittest.TestCase):
    def test_non_reviewable_classification_clears_lines_and_review(self):
        data = {
            "classification": "vendor_quote",
            "revises": None,
            "duplicate_of": None,
            "needs_review": True,
            "review_reason": "something",
            "line_items": [
                {"raw": "x", "description": "x", "qty": 1, "uom": "EA", "source": "body"}
            ],
        }
        result = validate_email_result(data)
        self.assertEqual(result["line_items"], [])
        self.assertFalse(result["needs_review"])
        self.assertIsNone(result["review_reason"])

    def test_attachment_failure_forces_review(self):
        data = {
            "classification": "rfq",
            "revises": None,
            "duplicate_of": None,
            "needs_review": False,
            "review_reason": None,
            "line_items": [],
        }
        result = validate_email_result(data, attachment_failures=["quote.pdf"])
        self.assertTrue(result["needs_review"])
        self.assertIn("quote.pdf", result["review_reason"])

    def test_reviewable_without_reason_gets_default(self):
        data = {
            "classification": "purchase_order",
            "revises": None,
            "duplicate_of": None,
            "needs_review": True,
            "review_reason": None,
            "line_items": [],
        }
        result = validate_email_result(data)
        self.assertTrue(result["needs_review"])
        self.assertIsNotNone(result["review_reason"])


class ThreadManagerTests(unittest.TestCase):
    def test_reply_links_to_parent(self):
        emails = [
            {
                "id": "E001",
                "message_id": "<a@x>",
                "in_reply_to": None,
                "references": [],
                "date": "Mon, 1 Jan 2024 10:00:00 +0000",
            },
            {
                "id": "E002",
                "message_id": "<b@x>",
                "in_reply_to": "<a@x>",
                "references": "<a@x>",
                "date": "Mon, 1 Jan 2024 11:00:00 +0000",
            },
        ]
        updated, _ = build_threads(emails)
        by_id = {email["id"]: email for email in updated}
        self.assertEqual(by_id["E002"]["parent_email_id"], "E001")
        self.assertEqual(by_id["E001"]["thread_id"], by_id["E002"]["thread_id"])
        self.assertEqual(by_id["E001"]["thread_size"], 2)

    def test_unrelated_emails_get_separate_threads(self):
        emails = [
            {"id": "E001", "message_id": "<a@x>", "in_reply_to": None, "references": [], "date": None},
            {"id": "E002", "message_id": "<b@x>", "in_reply_to": None, "references": [], "date": None},
        ]
        updated, _ = build_threads(emails)
        by_id = {email["id"]: email for email in updated}
        self.assertNotEqual(by_id["E001"]["thread_id"], by_id["E002"]["thread_id"])


class CacheKeyTests(unittest.TestCase):
    def test_same_inputs_same_key(self):
        a = cache_key("E001", "hello world", "gpt-5-mini")
        b = cache_key("E001", "hello world", "gpt-5-mini")
        self.assertEqual(a, b)

    def test_different_model_different_key(self):
        a = cache_key("E001", "hello world", "gpt-5-mini")
        b = cache_key("E001", "hello world", "gpt-4.1-mini")
        self.assertNotEqual(a, b)

    def test_different_content_different_key(self):
        a = cache_key("E001", "hello world", "gpt-5-mini")
        b = cache_key("E001", "goodbye world", "gpt-5-mini")
        self.assertNotEqual(a, b)


class FindRequestCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.inbox = [
            {"id": "E001", "subject": "2 inch pipe quote", "email_markdown": "need 2 inch pipe"},
            {"id": "E002", "subject": "supplier pricing", "email_markdown": "here is our pricing"},
            {"id": "E003", "subject": "current email", "email_markdown": "irrelevant"},
        ]
        self.prior_results = {
            "E001": {
                "classification": "rfq",
                "duplicate_of": None,
                "line_items": [{"description": "2 inch pipe"}],
            },
            "E002": {
                "classification": "vendor_quote",
                "duplicate_of": None,
                "line_items": [{"description": "2 inch pipe"}],
            },
        }

    def test_excludes_vendor_quote_and_current_email(self):
        candidates = find_request_candidates(
            inbox=self.inbox,
            current_email={"id": "E003"},
            prior_results=self.prior_results,
            search_terms=["pipe"],
            referenced_ids=[],
        )
        ids = [candidate["id"] for candidate in candidates]
        self.assertIn("E001", ids)
        self.assertNotIn("E002", ids)
        self.assertNotIn("E003", ids)

    def test_explicit_reference_match(self):
        candidates = find_request_candidates(
            inbox=self.inbox,
            current_email={"id": "E003"},
            prior_results=self.prior_results,
            search_terms=[],
            referenced_ids=["E001"],
        )
        self.assertTrue(candidates[0]["explicit_match"])


class ParseResilienceTests(unittest.TestCase):
    def test_one_bad_email_does_not_stop_the_run(self):
        fake_inbox = [
            {
                "id": "E001",
                "email_markdown": "ok email",
                "attachments": [],
                "date_timestamp": 1,
            },
            {
                "id": "E002",
                "email_markdown": "bad email",
                "attachments": [],
                "date_timestamp": 2,
            },
        ]

        def fake_extract_email(email_markdown, current_email, inbox, prior_results):
            del email_markdown, inbox, prior_results
            if current_email["id"] == "E002":
                raise RuntimeError("boom")
            return {
                "result": {
                    "classification": "rfq",
                    "revises": None,
                    "duplicate_of": None,
                    "needs_review": False,
                    "review_reason": None,
                    "line_items": [],
                },
                "usage": {"total_tokens": 10, "estimated_cost": 0.001},
                "searched_prior_requests": False,
            }

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "parsed.json"
            with patch("main.load_emails", return_value=fake_inbox), \
                 patch("main.extract_email", side_effect=fake_extract_email):
                results = main.parse_emails("unused", out_path)

            self.assertEqual(len(results), 2)
            self.assertFalse(results["E001"]["needs_review"])
            self.assertTrue(results["E002"]["needs_review"])
            self.assertTrue(out_path.exists())


if __name__ == "__main__":
    unittest.main()
