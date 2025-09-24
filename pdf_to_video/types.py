"""Definições de tipos e estruturas de dados do pipeline de PDF para vídeo."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple, Union


class PauseType(Enum):
    """Tipos de pausa reconhecidos no script."""

    SHORT = "short_pause"
    LONG = "long_pause"


@dataclass(frozen=True)
class SlideToken:
    """Token representando a referência a um slide específico."""

    slide_index: int


@dataclass(frozen=True)
class PauseToken:
    """Token representando uma pausa com duração em segundos."""

    seconds: float


@dataclass(frozen=True)
class VignetteToken:
    """Token representando a inserção de um trecho de vídeo externo (vignette)."""

    pass


ScriptToken = Union[SlideToken, PauseToken, VignetteToken]


@dataclass(frozen=True)
class SlideAsset:
    """Recursos de mídia associados a um slide."""

    index: int
    image_path: Path
    audio_path: Optional[Path]
    audio_duration: Optional[float]


@dataclass(frozen=True)
class ClipSpec:
    """Especificação de um trecho de vídeo a ser renderizado."""

    kind: str
    image_path: Optional[Path]
    audio_path: Optional[Path]
    duration: Optional[float]
    description: Optional[str]


@dataclass(frozen=True)
class BuildConfig:
    """Configurações de construção do vídeo de saída."""

    fps: int
    resolution: Tuple[int, int]
    short_pause_seconds: float
    long_pause_seconds: float
    audio_fadein: float
    audio_fadeout: float
    pdf_oversample: float
    crf: int
    preset: str
    bitrate: Optional[str]


@dataclass(frozen=True)
class AulaPaths:
    """Caminhos relevantes dentro de uma pasta de aula."""

    root: Path
    pdf_path: Path
    docx_path: Optional[Path]
    audios_dir: Path
    vignette_path: Optional[Path]
    output_dir: Path
    frames_dir: Path
    output_video_path: Path


def ensure_positive_seconds(value: float) -> float:
    """Garante que o valor de segundos seja positivo e não nulo."""

    return max(0.0, float(value))


