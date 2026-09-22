"""
Exports index.pkl into two files the Cloudflare Worker can serve.

index.pkl is a Python pickle — unreadable from JavaScript, and it holds the
model object alongside the data. The Worker needs the same information in
formats a runtime with no Python can parse:

  worker-index/vectors.bin   the embedding matrix, raw little-endian float32,
                             row-major, one row per document
  worker-index/docs.json     the document metadata, in the same row order

Splitting them matters. The vectors are dense numbers that would triple in
size as JSON text and cost real time to parse; as a binary blob the Worker
wraps them in a Float32Array with no parsing at all. The metadata is small
enough that JSON is the right call.

Row order is the contract between the two files: row i of vectors.bin
belongs to docs[i]. Nothing else links them, so neither file can be
regenerated independently.

Run manually (after build_index.py):
    python3 export_worker_index.py

Then commit the two files — they are what gets deployed with the Worker.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SITE_ROOT = ROOT.parent.parent
INDEX_PATH = ROOT / "index.pkl"
OUT_DIR = SITE_ROOT / "autism-search" / "public" / "worker-index"

# A handful of abstracts are pathologically long. Capping keeps the asset
# predictable without touching the vectors, which were computed from the
# full text and are unaffected.
MAX_TEXT = 4000


def main() -> None:
    if not INDEX_PATH.exists():
        raise SystemExit("No index.pkl — run build_index.py first.")

    with INDEX_PATH.open("rb") as f:
        index = pickle.load(f)

    docs = index["docs"]
    # "<f4" forces little-endian regardless of the machine doing the export;
    # a JS Float32Array always reads native order, and every Cloudflare
    # runtime is little-endian.
    embeddings = np.asarray(index["embeddings"], dtype="<f4")

    if embeddings.shape[0] != len(docs):
        raise SystemExit(
            f"Row mismatch: {embeddings.shape[0]} vectors vs {len(docs)} documents"
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "vectors.bin").write_bytes(embeddings.tobytes())

    payload = {
        "model": index["model_name"],
        "query_prefix": index.get("query_prefix", ""),
        "dims": int(embeddings.shape[1]),
        "count": len(docs),
        "docs": [
            {
                "id": d["id"],
                "source": d["source"],
                "title": d["title"],
                "text": d["text"][:MAX_TEXT],
                "source_url": d["source_url"],
                "publication_date": d.get("publication_date", ""),
                "authors": (d.get("authors") or [])[:3],
                "venue": d.get("venue", ""),
            }
            for d in docs
        ],
    }
    (OUT_DIR / "docs.json").write_text(json.dumps(payload, separators=(",", ":")))

    vec_mb = (OUT_DIR / "vectors.bin").stat().st_size / 1_048_576
    doc_mb = (OUT_DIR / "docs.json").stat().st_size / 1_048_576
    print(f"Wrote {OUT_DIR}")
    print(f"  vectors.bin  {embeddings.shape[0]} x {embeddings.shape[1]}  {vec_mb:.1f} MB")
    print(f"  docs.json    {len(docs)} documents            {doc_mb:.1f} MB")
    print(f"  model        {index['model_name']}")
    print("\nCommit both files, then redeploy the Worker.")


if __name__ == "__main__":
    main()
