"""Geração automatizada de áudios por slide usando Gemini TTS (Google AI)."""

from __future__ import annotations

import base64
import os
import wave
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from google import genai
from google.genai import types

from pdf_to_video.script_parser import extract_slide_texts


def _ensure_audios_dir(aula_dir: Path) -> Path:
    """Garante a existência do diretório de áudios da aula."""

    out = aula_dir / "audios"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _default_style_instruction() -> str:
    """Instrução padrão de estilo de voz."""

    return (
        "Read aloud in a warm, natural, and friendly tone. "
        "You are a lecture speaker on a Computer Vision class. "
        "Read and speak in Brazilian Portuguese."
    )


def _wave_write(filename: Path, pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> None:
    """Salva bytes PCM como WAV no caminho indicado."""

    with wave.open(str(filename), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def _request_gemini_tts(api_key: str, text: str, voice: str = "Alnilam", model: str = "gemini-2.5-flash-preview-tts", lang: str = "pt-BR") -> bytes:
    """Chama a API do Gemini TTS usando o cliente oficial e retorna PCM (bytes)."""

    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=model,
        contents=_default_style_instruction() + "\n\n" + text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                )
            ),
        ),
    )
    return resp.candidates[0].content.parts[0].inline_data.data


def synthesize_audios_for_aula(aula_dir: Path, voice: str = "Alnilam", model: str = "gemini-2.5-flash-preview-tts", lang: str = "pt-BR") -> None:
    """Gera áudios .wav por slide usando apenas o script.docx da aula."""

    print("[tts] Preparando síntese de voz por slide...")
    load_dotenv()
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("API_KEY não encontrada no .env.")
    docx_candidates = list(aula_dir.glob("script*.docx"))
    if not docx_candidates:
        raise RuntimeError("script.docx não encontrado na pasta da aula.")
    docx_path = docx_candidates[0]
    slide_texts: Dict[int, str] = extract_slide_texts(docx_path)
    if not slide_texts:
        raise RuntimeError("Nenhum texto de slide encontrado no script.")
    audios_dir = _ensure_audios_dir(aula_dir)
    for slide_idx in sorted(slide_texts.keys()):
        text = slide_texts[slide_idx].strip()
        if not text:
            continue
        out_path = audios_dir / f"slide_{slide_idx:02d}.wav"
        if out_path.exists():
            print(f"[tts] Já existe: {out_path.name}, pulando.")
            continue
        print(f"[tts] Sintetizando slide {slide_idx:02d}...")
        pcm = _request_gemini_tts(api_key=api_key, text=text, voice=voice, model=model, lang=lang)
        _wave_write(out_path, pcm, channels=1, rate=24000, sample_width=2)
        print(f"[tts] Gerado: {out_path.name}")


def main() -> None:
    """CLI simples para gerar .wav por slide em uma pasta de aula."""

    import argparse

    parser = argparse.ArgumentParser(description="Gerar .wav por slide a partir de script.docx usando Gemini TTS")
    parser.add_argument("aula_dir", type=str, help="Diretório da aula (contendo script.docx)")
    parser.add_argument("--voice", type=str, default="Alnilam", help="Nome da voz (ex.: Alnilam)")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash-preview-tts", help="Modelo TTS do Gemini a ser usado")
    parser.add_argument("--lang", type=str, default="pt-BR", help="Idioma da fala (ex.: pt-BR)")
    args = parser.parse_args()
    synthesize_audios_for_aula(Path(args.aula_dir), voice=args.voice, model=args.model, lang=args.lang)


if __name__ == "__main__":
    main()


