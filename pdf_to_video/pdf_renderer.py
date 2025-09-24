"""Renderização de páginas de PDF em imagens PNG numeradas por slide."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF


def render_pdf_to_images(pdf_path: Path, frames_dir: Path, target_resolution: Tuple[int, int], oversample: float = 1.5) -> List[Path]:
    """Converte cada página do PDF em PNG com resolução suficiente para o vídeo final.

    O fator de oversample aumenta a resolução para evitar upscale e melhorar a nitidez.
    """

    frames_dir.mkdir(parents=True, exist_ok=True)
    print("[pdf-to-video] Renderizando PDF em imagens de alta resolução...")
    doc = fitz.open(str(pdf_path))
    image_paths: List[Path] = []
    target_w, target_h = target_resolution
    safe_oversample = max(1.0, float(oversample))
    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        rect = page.rect
        scale_w = target_w / float(rect.width)
        scale_h = target_h / float(rect.height)
        zoom = max(scale_w, scale_h) * safe_oversample
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        slide_num = page_index + 1
        out_path = frames_dir / f"slide_{slide_num:02d}.png"
        pix.save(str(out_path))
        print(f"  Gerado frame do slide {slide_num:02d} em {out_path.name} ({pix.width}x{pix.height})")
        image_paths.append(out_path)
    doc.close()
    print(f"[pdf-to-video] {len(image_paths)} frames gerados em {frames_dir}")
    return image_paths


