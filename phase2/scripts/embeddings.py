#!/usr/bin/env python3
"""
embeddings.py — Minimal sentence embeddings via transformers + torch
(mean pooling). Avoids sentence-transformers' broken TF dependency chain.

Model cache goes to the workspace .hf_cache (sandbox-friendly).
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = os.environ.get("HF_HOME") or str(ROOT.parent / ".hf_cache")
os.environ.setdefault("HF_HOME", CACHE)
os.environ.setdefault("TRANSFORMERS_CACHE", CACHE)

_MODEL = None
_TOKENIZER = None
MODEL_NAME = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def _load():
    global _MODEL, _TOKENIZER
    if _MODEL is None:
        import torch
        from transformers import AutoModel, AutoTokenizer
        _TOKENIZER = AutoTokenizer.from_pretrained(MODEL_NAME)
        _MODEL = AutoModel.from_pretrained(MODEL_NAME)
        _MODEL.eval()
        # Use the GPU when there is one; embedding the corpus is the only
        # step that is compute-bound rather than I/O-bound.
        _MODEL.to(_device())
    return _MODEL, _TOKENIZER


def _device():
    import torch
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def embed(texts, batch_size=None):
    """Return numpy array [n, dim] of mean-pooled embeddings."""
    import numpy as np
    import torch
    model, tok = _load()
    if batch_size is None:
        batch_size = 256 if _device() == "cuda" else 64
    outs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        enc = tok(batch, padding=True, truncation=True, max_length=256, return_tensors="pt")
        enc = {k: v.to(_device()) for k, v in enc.items()}
        with torch.no_grad():
            out = model(**enc)
        mask = enc["attention_mask"].unsqueeze(-1).float()
        pooled = (out.last_hidden_state * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
        outs.append(pooled.cpu().numpy())   # .numpy() fails on a CUDA tensor
    return np.vstack(outs) if len(outs) > 1 else outs[0]


def embed_one(text):
    return embed([text])[0]


if __name__ == "__main__":
    v = embed(["Metadata matters for library discovery", "Moby Dick is about a whale"])
    print("dim:", v.shape)
