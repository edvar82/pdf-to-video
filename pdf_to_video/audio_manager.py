"""Descoberta e validação de áudios dos slides e cálculo de duração."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from moviepy.editor import AudioFileClip

SLIDE_AUDIO_PATTERN = re.compile(r"^slide_(\d{1,3})\.(wav|mp3|m4a|aac|flac)$", re.IGNORECASE)


def _iter_audio_files(audios_dir: Path) -> Iterable[Path]:
    """Itera sobre arquivos de áudio suportados no diretório informado."""

    if not audios_dir.exists():
        return []
    for path in sorted(audios_dir.iterdir()):
        if not path.is_file():
            continue
        if SLIDE_AUDIO_PATTERN.match(path.name):
            yield path


def _read_audio_duration_seconds(path: Path) -> Optional[float]:
    """Obtém a duração do áudio em segundos usando moviepy."""

    try:
        clip = AudioFileClip(str(path))
        duration = float(clip.duration)
        clip.close()
        return duration
    except Exception:
        return None


def discover_slide_audios(audios_dir: Path) -> Dict[int, Tuple[Path, Optional[float]]]:
    """Mapeia índice do slide para par (caminho, duração)."""

    print("[pdf-to-video] Lendo áudios dos slides...")
    mapping: Dict[int, Tuple[Path, Optional[float]]] = {}
    for audio_path in _iter_audio_files(audios_dir):
        match = SLIDE_AUDIO_PATTERN.match(audio_path.name)
        if not match:
            continue
        index = int(match.group(1))
        duration = _read_audio_duration_seconds(audio_path)
        mapping[index] = (audio_path, duration)
        if duration is not None:
            print(f"  Áudio slide {index:02d}: {audio_path.name} ({duration:.2f}s)")
        else:
            print(f"  Áudio slide {index:02d}: {audio_path.name} (duração desconhecida)")
    if not mapping:
        print("[pdf-to-video] Nenhum áudio encontrado em 'audios/'.")
    return mapping


