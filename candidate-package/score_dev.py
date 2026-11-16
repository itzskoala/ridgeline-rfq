import json
import re
import sys
from pathlib import Path

ACTIONABLE = {"rfq", "rfq_revision", "purchase_order"}


def norm(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9|]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def canon(text):
    text = re.sub(r"\bschedule\b", "sch", text)
    text = re.sub(r"\bgalvanized\b", "galv", text)
    text = re.sub(r"\bseamless\b", "smls", text)
    text = re.sub(r"\bbutt weld\b", "bw", text)
    text = re.sub(r"\bnpt\b", "threaded", text)
    text = re.sub(r"\bclass (\d+)\b", r"\1 lb", text)
    text = re.sub(r"\b(\d+)#", r"\1 lb", text)
    return text


def phrase_in(description, phrase):
    desc_n = canon(norm(description))
    for alt in phrase.split("|"):
        alt_n = canon(norm(alt))
        if alt_n and alt_n in desc_n:
            return True
    return False


def qty_matches(pred_qty, ans_qty, tol):
    if ans_qty is None or tol is None:
        return True
    if pred_qty is None:
        return False
    if tol == 0:
        return pred_qty == ans_qty
    return abs(pred_qty - ans_qty) <= tol * max(abs(ans_qty), 1)


def token_overlap(a, b):
    ta = set(norm(a).split())
    tb = set(norm(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def match_lines(pred_lines, truth_lines):
    used = set()
    missed = []
    matched_pairs = []

    for t in truth_lines:
        best_idx, best_score = None, -1.0
        for i, p in enumerate(pred_lines):
            if i in used:
                continue
            if not qty_matches(p.get("qty"), t.get("qty"), t.get("qty_tol")):
                continue
            score = token_overlap(p.get("raw", ""), t.get("raw", ""))
            if score > best_score:
                best_score, best_idx = score, i

        if best_idx is None:
            missed.append(t)
            continue

        used.add(best_idx)
        matched_pairs.append((pred_lines[best_idx], t))

    extra = [p for i, p in enumerate(pred_lines) if i not in used]
    return matched_pairs, missed, extra


def score(root):
    parsed = json.loads((root / "data/dev/parsed.json").read_text())
    answer_key = json.loads((root / "data/dev/answer_key.json").read_text())["emails"]

    silent_losses = []
    lost_requests = []
    phantom_requests = []
    hallucinated_lines = []
    missed_lines = []

    classification_correct = 0
    needs_review_correct = 0
    must_mention_checked = 0
    must_mention_passed = 0
    must_not_mention_violations = 0

    for email_id, truth in sorted(answer_key.items()):
        pred = parsed.get(email_id)
        if pred is None:
            silent_losses.append((email_id, "missing from parsed.json entirely"))
            continue

        truth_class = truth["classification"]
        pred_class = pred["classification"]

        if truth_class == pred_class:
            classification_correct += 1
        if bool(truth["needs_review"]) == bool(pred["needs_review"]):
            needs_review_correct += 1

        truth_needed_action = bool(truth.get("line_items")) or bool(truth["needs_review"])
        pred_silent = not pred.get("line_items") and not pred.get("needs_review")
        if truth_needed_action and pred_silent:
            silent_losses.append((email_id, f"truth={truth_class} needs_review={truth['needs_review']}"))

        if truth_class in ACTIONABLE and pred_class not in ACTIONABLE:
            lost_requests.append((email_id, f"truth={truth_class} pred={pred_class}"))
        if truth_class not in ACTIONABLE and pred_class in ACTIONABLE:
            phantom_requests.append((email_id, f"truth={truth_class} pred={pred_class}"))

        matched_pairs, missed, extra = match_lines(
            list(pred.get("line_items", [])), truth.get("line_items", [])
        )

        for t in missed:
            missed_lines.append((email_id, t["id"], t["raw"]))
        for p in extra:
            hallucinated_lines.append((email_id, p.get("raw")))

        for p, t in matched_pairs:
            desc = p.get("description", "")
            for phrase in t.get("must_mention", []):
                must_mention_checked += 1
                if phrase_in(desc, phrase):
                    must_mention_passed += 1
            for phrase in t.get("must_not_mention", []):
                if phrase_in(desc, phrase):
                    must_not_mention_violations += 1

    n = len(answer_key)
    print("=== Headline numbers (graded in this order) ===")
    print(f"1. Silent losses: {len(silent_losses)}/{n} emails")
    for email_id, detail in silent_losses:
        print(f"   - {email_id}: {detail}")
    print(f"2. Hallucinated lines: {len(hallucinated_lines)}")
    for email_id, raw in hallucinated_lines:
        print(f"   - {email_id}: {raw!r}")
    print(f"3. Lost requests (actionable misclassified away): {len(lost_requests)}")
    for email_id, detail in lost_requests:
        print(f"   - {email_id}: {detail}")
    print(f"   Phantom requests (non-request misclassified as actionable): {len(phantom_requests)}")
    for email_id, detail in phantom_requests:
        print(f"   - {email_id}: {detail}")

    print()
    print("=== Secondary numbers ===")
    print(f"Classification accuracy: {classification_correct}/{n}")
    print(f"needs_review accuracy: {needs_review_correct}/{n}")
    print(f"Lines missed (recall loss, excluding full silent losses above): {len(missed_lines)}")
    for email_id, line_id, raw in missed_lines:
        print(f"   - {email_id} {line_id}: {raw!r}")
    if must_mention_checked:
        print(f"must_mention pass rate: {must_mention_passed}/{must_mention_checked}")
    print(f"must_not_mention violations: {must_not_mention_violations}")


if __name__ == "__main__":
    score(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("."))
