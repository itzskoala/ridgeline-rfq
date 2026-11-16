# Decisions

TODO: at most two pages total. The four sections below are required by the brief — write
them in your own voice; don't leave the TODOs in the submitted version.

Roughly how long I spent: TODO (brief asks for this; budget is 8-12h, stop at 16h).

## Something in the data that surprised you

TODO — one paragraph, in your own words, but here's verified material from scoring dev
against `answer_key.json`:
- E019/E021 (and similar): the model correctly writes "ASTM A106 Grade B" in `description`,
  but the answer key's `must_mention` wants the compact token `a106b`. The brief documents
  spelling equivalences (Sch/Schedule, 150#/150 lb, BW/butt weld, etc.) but grade codes like
  A106B aren't on that list — "Grade B" vs "B" is a real gap between how an ISR might type
  a spec and how the key checks for it.
- E002/E007: a vague quantity ("a couple caps") or a messy handwritten/OCR'd list triggered
  `needs_review=True` even though the answer key says `False` for that email overall — the
  model treated "I can't fully trust one line" as grounds to flag the whole email, when the
  spec's intent seems to be narrower (unresolvable *items*, not just a vague qty, which
  already has its own null-qty handling).

## Something in this brief or the README you disagree with, and what you did about it

TODO — be specific and concrete; "the README is not gospel," they mean it. E.g.: is there
a line-item rule, a classification boundary, or a `needs_review` trigger you read differently
than written, and where in the code does your reading show up?

## Your predicted held-out numbers, and the two kinds of email you expect to get wrong

Current dev scores (after fixing a caching bug and a schema-enforcement gap this session —
see `AI_USAGE.md`): 24/24 classification, 210/210 line recall, 0 hallucinated lines,
421/425 (99%) must_mention, 22/24 needs_review match (both misses are false-positive
reviews, not silent losses). TODO: state your own predicted held-out numbers — expect lower
than dev (held-out has "a few situations dev doesn't show you"), and don't just restate the
dev numbers.

The two kinds of email I'd expect this system to get wrong on held-out:
1. **Scanned/handwritten lists with OCR noise** (like E007's clipboard-photo list) — vague
   quantities, ambiguous abbreviations, and misreads push `needs_review` false positives up
   and can produce a genuinely wrong extra line (E007 predicted a "3-3/4\" bronze ball
   valve" line not in the answer key).
2. **Specs written in a form not covered by the brief's documented spelling equivalences**
   (e.g. "ASTM A106 Grade B" vs. the catalog/key's compact "A106B") — these pass a human
   rep's eye but fail a literal `must_mention` check, so expect some context-carried misses
   on specs with less-common abbreviation patterns than Sch/150#/BW/etc.

## How this runs for real

TODO — the brief gives four concrete scenarios; answer each, and say plainly which you
actually built vs. which is just a design answer:
- **3,000 emails/day arrive by webhook.** What's the ingestion/queueing shape? (Current
  code loads a whole directory synchronously, in one process, sorted by date — that's a
  batch-script shape, not a webhook-handler shape. What would change?)
- **Model provider down for two hours.** Current code already falls back to a safe
  `needs_review` result per email on any extraction exception (see `main.py`'s
  `fallback_result` / `except Exception`) — is that enough for a 2-hour outage at volume,
  or do you need retry/backoff/a dead-letter queue?
- **A customer sends a 300-page PDF.** What actually happens today? (Worth actually testing
  this rather than guessing — token cost, timeout, OCR time.)
- **The same email delivered twice.** This one *is* handled for the dev set's duplicate
  scenario (`duplicate_of`, "later Date: is the duplicate") — but that's about the same
  *content* arriving twice in the inbox, not necessarily true delivery-level dedup (e.g. a
  webhook retry delivering the identical message twice with the same Message-ID). Are those
  the same mechanism in your design or do they need a separate check?

## Design notes (not required, but expected in a good memo)

TODO — where does the model decide vs. where does code decide (e.g. classification/line
extraction is the model; duplicate "later Date: wins," needs_review overrides for unreadable
attachments, and schema validation in `schemas.py` are code); what you measured and how, what
you rejected and why (e.g. did you consider or try the original tool-calling `search_inbox`
approach before moving to directly embedding candidates in the prompt — what changed and why
is the new version better/cheaper); what's known-broken; what's next with more time (matcher?
web app?).
