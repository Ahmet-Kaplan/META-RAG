#!/usr/bin/env python3
"""
gen_fig_meta_rag_gemini.py — Figure 1 (META-RAG architecture) via Gemini
image generation, Style D "Classic Accent Bar" (academic, grayscale-safe).

Reads GEMINI_API_KEY from phase1/.env. Generates 3 attempts; keep the best.

Usage:
  python3 figures/gen_fig_meta_rag_gemini.py
"""

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / "phase1" / ".env")
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    sys.exit("ERROR: GEMINI_API_KEY not found in phase1/.env")

from google import genai  # noqa: E402

MODELS = ["gemini-3-pro-image-preview", "gemini-2.5-flash-image"]
OUT_DIR = Path(__file__).resolve().parent

PROMPT = """
FRAMING
Create a CLASSIC ACCENT BAR style technical diagram for an IEEE conference paper
about library AI. The diagram shows the META-RAG system: a metadata-aware
retrieval-augmented generation architecture with a closing loop from LLM
cataloging back into the catalog. It must look like a clean academic systems
figure: precise, flat, professional, fully legible in grayscale, with every
label spelled EXACTLY as given below.

VISUAL STYLE — CLASSIC ACCENT BAR
- Horizontal section bands stacked vertically, pale gray (#F7F7F5) fill where bands are used
- Thick colored LEFT ACCENT BAR (8px) distinguishes each component box
- Content boxes: white fill, thin #DDD border, 4px rounded corners
- Section palette: Blue #4A90D9, Teal #5BA58B, Amber #D4A252, Slate #7B8794
- Sans-serif typography (Helvetica/Arial), bold titles, regular body
- Arrows are clean straight or slightly curved lines with small arrowheads, colored to match their source box accent
- Flat, clean, ZERO decoration, no icons, no clip art, no shadows, no gradients
- White background

COLOR PALETTE
- Blue #4A90D9 for retrieval components
- Teal #5BA58B for index components
- Amber #D4A252 for the cataloging loop
- Slate #7B8794 for generation and verification components
- Ink #1A1A1A for borders and text
- Pale gray #F7F7F5 for band fills
- Dashed/dotted arrows in the same color family as their source

LAYOUT (left to right, top to bottom; approximate positions on a wide canvas)
1. Top-left: box labeled "Patron query"
2. Top-middle-left: box labeled "Hybrid retrieval" with subline "RRF fusion (k=60)"
3. Top-middle-right: box labeled "top-k records + passages"
4. Top-right: box labeled "LLM generation (grounded)"
5. Below generation: box labeled "Answer with [REC:key] [CHUNK:id] citations"
6. Below that: box labeled "Verification" with subline "citations exist · judge support"
7. Right-middle: box labeled "Verified answer" with subline "(faithful, cited)"
8. Middle-left, two stacked boxes:
   a. "Chunk index" with subline "full text · dense + BM25"
   b. "Record index" with subline "subjects ⊕ DDC · field-boosted BM25 + dense"
9. Bottom-left band: box labeled "LLM cataloging" with subline "(authority-file RAG · LCSH/DDC)"
10. Bottom-right band: box labeled "LIBRA-Eval  ·  LIBRA-QA (discovery)  ·  LIBRA-CAT (cataloging)"
11. Bottom caption line (small, gray): "open data: Project Gutenberg · OpenLibrary · HathiTrust · id.loc.gov"

CONNECTIONS (draw every arrow; label only the two annotated ones)
- Arrow: "Patron query" -> "Hybrid retrieval"
- Arrows (two, teal, vertical): "Hybrid retrieval" <-> "Chunk index"  (query down, candidates up)
- Arrows (two, teal, curved): "Hybrid retrieval" <-> "Record index"
- Arrow: "Hybrid retrieval" -> "top-k records + passages"
- Arrow: "top-k records + passages" -> "LLM generation (grounded)"
- Arrow (vertical): "LLM generation (grounded)" -> "Answer with [REC:key] [CHUNK:id] citations"
- Arrow (vertical): "Answer with [REC:key] [CHUNK:id] citations" -> "Verification"
- Arrow: "Verification" -> "Verified answer"
- Dashed amber arrow (vertical, labeled): "LLM cataloging" -> "Record index", label "validated subjects / DDC" with small note "metadata → discovery"
- Dotted arrow: "Verified answer" -> "LIBRA-Eval" band
- Dotted arrow: "LLM cataloging" -> "LIBRA-Eval" band

CONSTRAINTS
- Spell every label EXACTLY as written above, including "[REC:key]", "[CHUNK:id]", "k=60", "⊕", "·", "LCSH/DDC", "LIBRA-QA", "LIBRA-CAT". SPELL EXACTLY.
- No icons, no clip art, no emoji, no photos, no shadows, no 3D.
- Everything inside the canvas; no text cut off; boxes large enough for their labels.
- Grayscale-printable: do not rely on color alone to distinguish components.
"""


def generate(client, model, prompt, attempt):
    out = OUT_DIR / f"fig_meta_rag_gemini_attempt{attempt}.png"
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                out.write_bytes(part.inline_data.data)
                print(f"  saved {out.name} ({out.stat().st_size:,} bytes) [model={model}]")
                return out
        print(f"  attempt {attempt}: no image part; text={getattr(part, 'text', '')[:200]}")
    except Exception as e:
        print(f"  attempt {attempt} [{model}] ERROR: {type(e).__name__}: {str(e)[:250]}")
    return None


def main():
    client = genai.Client(api_key=API_KEY)
    results = []
    for i in range(1, 4):
        if i > 1:
            time.sleep(2)
        print(f"--- attempt {i} ---")
        for model in MODELS:
            path = generate(client, model, PROMPT, i)
            if path:
                results.append(path)
                break
    print(f"\nGenerated {len(results)}/3 attempts.")
    if not results:
        sys.exit(1)
    print("Review figures/fig_meta_rag_gemini_attempt*.png and keep the best as figures/fig_meta_rag.png")


if __name__ == "__main__":
    main()
