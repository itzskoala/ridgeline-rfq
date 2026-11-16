# Running this

## Setup (fresh clone/unzip → working `parse`)

```
# from the candidate-package/ directory
uv sync                       # or: pip install -r requirements.txt, if you export one
cp .env.example .env           # TODO: create .env.example; put OPENAI_API_KEY in .env
python main.py parse --emails data/dev/emails --out data/dev/parsed.json
```

TODO: confirm the exact one-liner above actually works from a clean checkout (no `.venv`,
no `data/cache/`) and trim this to the single real setup step, per the brief ("one setup
step from a fresh clone or unzip to a working `parse`").

## Model

- `OPENAI_MODEL` env var, default `gpt-4.1-mini`. This run uses **gpt-5-mini** (set in `.env`).
- Two chat-completions calls per email: (1) a cheap intent/classification pass that also
  decides whether prior requests need to be searched, (2) the final structured extraction
  (with candidate prior requests embedded in the prompt when step 1 said to search). No
  function/tool-calling round trip — the prior-request search is plain Python over
  already-extracted results, not a model call.

## Cost (dev inbox, 24 emails)

Measured on this dev run (`python main.py parse --emails data/dev/emails --out
data/dev/parsed.json`, gpt-5-mini, 2 chat-completions calls per email — one intent/search
decision, one final structured extraction):

- Total model calls: 48 (2 per email; 0 extra tool-calling round trips)
- Total tokens: 320,818
- Total cost: $0.0744
- Cost per email (avg): ~$0.0031

## Replayability / idempotency — verified

- Model responses are cached in `data/cache/responses.json`, keyed by
  `{model}:{email_id}:{sha256(email_markdown)}`. This file is committed.
- Verified: running `parse` again on the same inbox with `OPENAI_API_KEY` unset serves all
  24 emails entirely from cache — identical output, $0.00 cost, 0 new model calls.
- Changing the model name or an email's extracted content changes the cache key, so a
  cache entry is never silently reused for different input.

## Error handling

- A single `.eml` that fails to parse, or an attachment that can't be read, is caught at
  that email's boundary and flagged `needs_review` with a reason — it does not stop the run.
- A model-call exception (timeout, API down, refusal) for one email falls back to a safe
  "needs review" result for that email only; the rest of the inbox still processes.

## Platform

TODO: confirm this runs under the required Windows/Docker/WSL target, or note what's needed
(e.g. `paddleocr`/`paddlepaddle` are heavy — confirm they install cleanly on Windows, or ship
a Dockerfile). Say here what we need to run it.

## Recording

TODO: link the ≤5-minute screen recording here (or confirm it's committed to the repo,
under 50MB total).
