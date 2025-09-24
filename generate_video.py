"""CLI para converter aulas em vídeo a partir de PDF, áudios e script.docx."""

from __future__ import annotations

import argparse
from pathlib import Path

from pdf_to_video.pipeline import build_aula_paths, run_pipeline
from pdf_to_video.types import BuildConfig


def parse_args() -> argparse.Namespace:
    """Lê argumentos de linha de comando."""

    parser = argparse.ArgumentParser(description="Gerar vídeo de aula a partir de PDF e áudios.")
    parser.add_argument("aula_dir", type=str, help="Diretório da aula contendo PDF, audios/ e script.docx")
    parser.add_argument("--fps", type=int, default=30, help="FPS do vídeo de saída")
    parser.add_argument("--width", type=int, default=1920, help="Largura do vídeo de saída")
    parser.add_argument("--height", type=int, default=1080, help="Altura do vídeo de saída")
    parser.add_argument("--short-pause", type=float, default=0.8, help="Duração de [short_pause] em segundos")
    parser.add_argument("--long-pause", type=float, default=1.6, help="Duração de [long_pause] em segundos")
    parser.add_argument("--fadein", type=float, default=0.05, help="Fade in de áudio em segundos")
    parser.add_argument("--fadeout", type=float, default=0.05, help="Fade out de áudio em segundos")
    parser.add_argument("--output-name", type=str, default="output.mp4", help="Nome do arquivo de saída")
    parser.add_argument("--pdf-oversample", type=float, default=2.0, help="Fator de oversample do render do PDF")
    parser.add_argument("--crf", type=int, default=16, help="Qualidade CRF do x264 (menor é melhor)")
    parser.add_argument("--preset", type=str, default="slow", help="Preset do x264 (ultrafast..placebo)")
    parser.add_argument("--bitrate", type=str, default=None, help="Bitrate alvo ex.: 8000k (sobrepõe CRF/preset)")
    return parser.parse_args()


def main() -> None:
    """Ponto de entrada da CLI."""

    args = parse_args()
    aula_dir = Path(args.aula_dir)
    config = BuildConfig(
        fps=args.fps,
        resolution=(args.width, args.height),
        short_pause_seconds=float(args.short_pause),
        long_pause_seconds=float(args.long_pause),
        audio_fadein=float(args.fadein),
        audio_fadeout=float(args.fadeout),
        pdf_oversample=float(args.pdf_oversample),
        crf=int(args.crf),
        preset=str(args.preset),
        bitrate=str(args.bitrate) if args.bitrate is not None else None,
    )
    paths = build_aula_paths(aula_dir, output_name=args.output_name)
    print("[pdf-to-video] Iniciando com as seguintes configurações:")
    print(f"  Aula: {aula_dir}")
    print(f"  Resolução: {config.resolution[0]}x{config.resolution[1]} @ {config.fps}fps")
    print(f"  Oversample do PDF: {config.pdf_oversample}")
    if config.bitrate is None:
        print(f"  Qualidade (x264): CRF={config.crf}, preset={config.preset}")
    else:
        print(f"  Bitrate: {config.bitrate}")
    print(f"  Pausas: short={config.short_pause_seconds}s, long={config.long_pause_seconds}s")
    output = run_pipeline(paths, config)
    print(f"[pdf-to-video] Vídeo gerado: {output}")


if __name__ == "__main__":
    main()


