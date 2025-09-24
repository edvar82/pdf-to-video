"""Pipeline de alto nível para converter uma aula em vídeo a partir de PDF e áudios."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .audio_manager import discover_slide_audios
from .pdf_renderer import render_pdf_to_images
from .script_parser import parse_script_docx
from .types import (AulaPaths, BuildConfig, ClipSpec, PauseToken, SlideAsset,
                    SlideToken, VignetteToken)
from .video_builder import build_video


def build_aula_paths(aula_dir: Path, output_name: str = "output.mp4") -> AulaPaths:
    """Monta os caminhos importantes da aula e retorna um objeto consolidado."""

    pdf_candidates = list(aula_dir.glob("*.pdf"))
    pdf_path = pdf_candidates[0] if pdf_candidates else aula_dir / "slides.pdf"
    docx_candidates = list(aula_dir.glob("script*.docx"))
    docx_path = docx_candidates[0] if docx_candidates else None
    audios_dir = aula_dir / "audios"
    vignette_path = None
    for name in ("vignette.mp4", "vinheta.mp4", "vignette.MP4"):
        candidate = aula_dir / name
        if candidate.exists():
            vignette_path = candidate
            break
    output_dir = aula_dir / "output"
    frames_dir = output_dir / "frames"
    output_video_path = output_dir / output_name
    return AulaPaths(
        root=aula_dir,
        pdf_path=pdf_path,
        docx_path=docx_path,
        audios_dir=audios_dir,
        vignette_path=vignette_path,
        output_dir=output_dir,
        frames_dir=frames_dir,
        output_video_path=output_video_path,
    )


def _collect_slide_assets(paths: AulaPaths, config: BuildConfig) -> Dict[int, SlideAsset]:
    """Renderiza o PDF e associa imagens e áudios por índice de slide."""

    image_paths = render_pdf_to_images(paths.pdf_path, paths.frames_dir, config.resolution, config.pdf_oversample)
    audio_map = discover_slide_audios(paths.audios_dir)
    assets: Dict[int, SlideAsset] = {}
    for idx, image_path in enumerate(image_paths, start=1):
        audio_info = audio_map.get(idx)
        audio_path = audio_info[0] if audio_info else None
        audio_duration = audio_info[1] if audio_info else None
        assets[idx] = SlideAsset(index=idx, image_path=image_path, audio_path=audio_path, audio_duration=audio_duration)
    return assets


def _build_clips_from_tokens(tokens, assets: Dict[int, SlideAsset], config: BuildConfig, vignette_path: Optional[Path]) -> List[ClipSpec]:
    """Converte a sequência de tokens em especificações de clipes para renderização."""

    clips: List[ClipSpec] = []
    for token in tokens:
        if isinstance(token, SlideToken):
            asset = assets.get(token.slide_index)
            if not asset:
                continue
            duration = asset.audio_duration if asset.audio_duration and asset.audio_duration > 0 else None
            if duration is None:
                duration = max(config.short_pause_seconds, 0.1)
            clips.append(
                ClipSpec(
                    kind="slide",
                    image_path=asset.image_path,
                    audio_path=asset.audio_path,
                    duration=duration,
                    description=f"slide_{asset.index:02d}",
                )
            )
        elif isinstance(token, PauseToken):
            clips.append(
                ClipSpec(
                    kind="pause",
                    image_path=None,
                    audio_path=None,
                    duration=token.seconds,
                    description="pause",
                )
            )
        elif isinstance(token, VignetteToken):
            if vignette_path and vignette_path.exists():
                clips.append(
                    ClipSpec(
                        kind="vignette",
                        image_path=None,
                        audio_path=vignette_path,
                        duration=None,
                        description="vignette",
                    )
                )
    return clips


def _fallback_tokens_from_audios(assets: Dict[int, SlideAsset]) -> List[SlideToken]:
    """Gera tokens de slides na ordem dos índices disponíveis quando não há script válido."""

    indices = sorted(assets.keys())
    return [SlideToken(slide_index=i) for i in indices]


def run_pipeline(paths: AulaPaths, config: BuildConfig) -> Path:
    """Executa a pipeline completa e retorna o caminho do vídeo gerado."""

    print("[pdf-to-video] Preparando assets (frames e áudios)...")
    assets = _collect_slide_assets(paths, config)
    tokens = []
    if paths.docx_path is not None and paths.docx_path.exists():
        print(f"[pdf-to-video] Lendo tokens do script: {paths.docx_path.name}")
        tokens = parse_script_docx(paths.docx_path, config.short_pause_seconds, config.long_pause_seconds)
    if not tokens:
        tokens = _fallback_tokens_from_audios(assets)
    print("[pdf-to-video] Gerando especificação dos clipes...")
    clips = _build_clips_from_tokens(tokens, assets, config, paths.vignette_path)
    if not clips:
        raise RuntimeError("Nenhum clipe foi gerado a partir dos tokens.")
    print("[pdf-to-video] Construindo o vídeo final...")
    output_path = build_video(clips, paths.output_video_path, config)
    return output_path


