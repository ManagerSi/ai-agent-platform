"""OpenAI-compatible embedding server for local BAAI/bge-small-zh-v1.5."""

from __future__ import annotations

import os
from typing import Union

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

MODEL_ID = os.getenv("LOCAL_EMBED_MODEL", "BAAI/bge-small-zh-v1.5")
HOST = os.getenv("LOCAL_EMBED_HOST", "127.0.0.1")
PORT = int(os.getenv("LOCAL_EMBED_PORT", "18001"))


def load_model() -> SentenceTransformer:
    try:
        from modelscope import snapshot_download

        local_path = snapshot_download(MODEL_ID)
        print(f"loaded {MODEL_ID} from ModelScope {local_path}")
        return SentenceTransformer(local_path)
    except Exception as exc:
        print(f"modelscope download failed ({exc}); trying Hugging Face")
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        return SentenceTransformer(MODEL_ID)


app = FastAPI()
model = load_model()
EMBEDDING_DIM = int(model.get_sentence_embedding_dimension() or 512)


class EmbedRequest(BaseModel):
    input: Union[str, list[str]]
    model: str | None = None


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "model": MODEL_ID, "dim": EMBEDDING_DIM}


@app.post("/embeddings")
@app.post("/v1/embeddings")
def embeddings(req: EmbedRequest) -> dict[str, object]:
    texts = [req.input] if isinstance(req.input, str) else list(req.input)
    vectors = model.encode(texts, normalize_embeddings=True).tolist()
    return {
        "object": "list",
        "model": req.model or MODEL_ID,
        "data": [
            {"object": "embedding", "index": index, "embedding": vector}
            for index, vector in enumerate(vectors)
        ],
        "usage": {"prompt_tokens": 0, "total_tokens": 0},
    }


if __name__ == "__main__":
    print(f"local bge embedding server model={MODEL_ID} dim={EMBEDDING_DIM} http://{HOST}:{PORT}/v1")
    uvicorn.run(app, host=HOST, port=PORT)
