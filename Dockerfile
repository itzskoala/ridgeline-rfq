FROM --platform=linux/amd64 python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md /app/
COPY src/ /app/src/

RUN uv sync --frozen --no-dev

COPY candidate-package/ /app/candidate-package/

RUN /app/.venv/bin/python -c "from paddleocr import PaddleOCR; PaddleOCR(lang='en', use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)"

WORKDIR /app/candidate-package

ENTRYPOINT ["/app/.venv/bin/python", "main.py"]
CMD ["parse", "--emails", "data/dev/emails", "--out", "data/dev/parsed.json"]
