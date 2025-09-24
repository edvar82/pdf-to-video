"""Construção do vídeo a partir de especificações de clipes."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from moviepy.editor import (AudioFileClip, ImageClip, VideoFileClip,
                            concatenate_videoclips)

from .types import BuildConfig, ClipSpec


def _ensure_resolution(clip, resolution: Tuple[int, int]):
    """Redimensiona o clipe para a resolução desejada mantendo proporção com letterbox quando necessário."""

    width, height = resolution
    return clip.resize(newsize=resolution)


def build_video(clips: Iterable[ClipSpec], output_path: Path, config: BuildConfig) -> Path:
    """Gera o vídeo final concatenando os clipes especificados."""

    print("[pdf-to-video] Montando clipes...")
    video_clips: List = []
    last_image: Optional[Path] = None
    for spec in clips:
        if spec.kind == "slide":
            if spec.image_path is None or spec.audio_path is None or spec.duration is None:
                continue
            last_image = spec.image_path
            image_clip = ImageClip(str(spec.image_path)).set_duration(spec.duration)
            image_clip = _ensure_resolution(image_clip, config.resolution)
            audio_clip = AudioFileClip(str(spec.audio_path))
            if config.audio_fadein > 0:
                audio_clip = audio_clip.audio_fadein(config.audio_fadein)
            if config.audio_fadeout > 0:
                audio_clip = audio_clip.audio_fadeout(config.audio_fadeout)
            image_clip = image_clip.set_audio(audio_clip)
            video_clips.append(image_clip)
            print(f"  Slide: {spec.description} | dur={spec.duration:.2f}s | img={spec.image_path.name} | audio={(spec.audio_path.name if spec.audio_path else 'nenhum')}")
        elif spec.kind == "pause":
            if last_image is None or spec.duration is None:
                continue
            pause_clip = ImageClip(str(last_image)).set_duration(spec.duration)
            pause_clip = _ensure_resolution(pause_clip, config.resolution)
            video_clips.append(pause_clip)
            print(f"  Pausa: {spec.duration:.2f}s")
        elif spec.kind == "vignette":
            if spec.audio_path is None:
                continue
            vignette_clip = VideoFileClip(str(spec.audio_path))
            vignette_clip = _ensure_resolution(vignette_clip, config.resolution)
            video_clips.append(vignette_clip)
            print(f"  Vignette: {spec.audio_path.name}")

    if not video_clips:
        raise RuntimeError("Nenhum clipe válido para construir o vídeo.")

    final = concatenate_videoclips(video_clips, method="compose")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if config.bitrate is not None:
        final.write_videofile(
            str(output_path),
            fps=config.fps,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(output_path.with_suffix(".temp-audio.m4a")),
            remove_temp=True,
            threads=4,
            verbose=False,
            logger=None,
            bitrate=config.bitrate,
        )
    else:
        final.write_videofile(
            str(output_path),
            fps=config.fps,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(output_path.with_suffix(".temp-audio.m4a")),
            remove_temp=True,
            threads=4,
            verbose=False,
            logger=None,
            ffmpeg_params=["-crf", str(config.crf), "-preset", str(config.preset)],
        )
    print("[pdf-to-video] Finalização de encoding concluída.")
    final.close()
    for clip in video_clips:
        try:
            clip.close()
        except Exception:
            pass
    return output_path


