# Running this

## Setup (fresh clone/unzip → working `parse`)

**Docker (recommended — this is what we test against):**

```
# from the repo root (the directory containing Dockerfile, not candidate-package/)
docker build --platform linux/amd64 -t ridgeline-rfq .
docker run --rm --platform linux/amd64 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY -e OPENAI_MODEL=gpt-5-mini \
  -v "$(pwd)/candidate-package/data:/app/candidate-package/data" \
  ridgeline-rfq
```

`--platform linux/amd64` matters even on an Apple Silicon Mac: `paddlepaddle` ships no
Linux ARM64 wheel at all (only `manylinux1_x86_64`, macOS ARM64, and Windows amd64), so the
image is pinned to amd64 — which is also what a Windows grading machine actually is.

That runs the default command (`parse --emails data/dev/emails --out data/dev/parsed.json`)
against the dev inbox. The `-v` mount is so `data/cache/` and `data/dev/parsed.json` land
back on the host instead of staying inside the throwaway container. `.env` is intentionally
**not** baked into the image (see `.dockerignore`), so both `OPENAI_API_KEY` and
`OPENAI_MODEL` must be passed with `-e` — omitting `OPENAI_MODEL` silently falls back to
the default model name, which won't match the committed cache keys and forces every email
to the safe fallback. Verified both ways: with the real key (fresh calls) and with it
removed (pure cache replay, identical output, $0.00). To run against a different inbox or
output path, override the command:

```
docker run --rm --platform linux/amd64 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY -e OPENAI_MODEL=gpt-5-mini \
  -v "$(pwd)/candidate-package/data:/app/candidate-package/data" \
  ridgeline-rfq parse --emails data/dev/emails --out data/dev/parsed.json
```

PaddleOCR's model weights are downloaded and baked into the image at `docker build` time
(see the Dockerfile's warm-up step), so `docker run` itself makes no network calls except
to the OpenAI API — consistent with the brief's "no outbound side effects" rule.

**Without Docker** (needs Python 3.12+, and system libs for OpenCV/PaddleOCR — see the
Dockerfile for the exact apt packages if you hit an import error):

```
# from the repo root
uv sync
cd candidate-package
cp .env.example .env   # put your OPENAI_API_KEY in .env
python main.py parse --emails data/dev/emails --out data/dev/parsed.json
```

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

Ships with a `Dockerfile` at the repo root — build and run with Docker on Windows,
natively, in Docker, or under WSL, no other setup needed. `paddleocr`/`paddlepaddle` are
heavy and finicky to install natively on Windows; Docker sidesteps that entirely.

Verified end to end this session: image builds clean (`--platform linux/amd64`), the
PaddleOCR model warm-up succeeds at build time, `.env`/API key are confirmed absent from
the built image, and a full `docker run` against the dev inbox matches the real cached
output exactly (with the key removed, $0.00 / 0 new calls; with it present, same result).
