"""
Pipeline completo automatizado para geração de vídeos de aulas.

Este script automatiza todo o processo:
1. Processa o script.docx e gera TTS com a API MiniMax
2. Separa o áudio nos silêncios de 6s gerando slide_01.wav, slide_02.wav, etc.
3. Gera o vídeo final a partir do PDF e áudios

Uso:
    python pipeline_completo.py aulas/aula5 --voice-id SEU_VOICE_ID

Requisitos na pasta da aula:
    aulas/aulaX/
        ├── script.docx       (roteiro com tags [slide_XX])
        ├── arquivo.pdf       (slides da aula)
        └── (gerados automaticamente:)
            ├── audio_completo.flac
            ├── audios/
            │   ├── slide_01.wav
            │   ├── slide_02.wav
            │   └── ...
            └── output.mp4
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional


def find_docx(aula_dir: Path) -> Optional[Path]:
    """Encontra o primeiro arquivo .docx na pasta da aula."""
    docx_files = list(aula_dir.glob("*.docx"))
    if not docx_files:
        return None
    if len(docx_files) > 1:
        print(f"⚠️  Aviso: Múltiplos .docx encontrados, usando: {docx_files[0].name}")
    return docx_files[0]


def find_pdf(aula_dir: Path) -> Optional[Path]:
    """Encontra o primeiro arquivo .pdf na pasta da aula."""
    pdf_files = list(aula_dir.glob("*.pdf"))
    if not pdf_files:
        return None
    if len(pdf_files) > 1:
        print(f"⚠️  Aviso: Múltiplos .pdf encontrados, usando: {pdf_files[0].name}")
    return pdf_files[0]


def run_command(cmd: list[str], description: str, cwd: Optional[Path] = None):
    """Executa um comando e exibe o progresso."""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    print(f"$ {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd=cwd, capture_output=False, text=True)
    
    if result.returncode != 0:
        print(f"\n❌ Erro ao executar: {description}")
        sys.exit(1)
    
    print(f"✅ {description} - Concluído!\n")


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline completo: Script -> TTS -> Separar Áudios -> Gerar Vídeo"
    )
    parser.add_argument(
        "aula_dir",
        type=str,
        help="Diretório da aula (ex: aulas/aula5)"
    )
    parser.add_argument(
        "--voice-id",
        default="Voicec41c71871760411371",
        help="ID da voz para TTS (obtenha com clone_voice.py)"
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Velocidade da fala (0.5-2.0, padrão: 1.0)"
    )
    parser.add_argument(
        "--skip-tts",
        action="store_true",
        help="Pular geração de TTS (usar áudio existente)"
    )
    parser.add_argument(
        "--skip-split",
        action="store_true",
        help="Pular separação de áudios (usar áudios existentes)"
    )
    parser.add_argument(
        "--skip-video",
        action="store_true",
        help="Pular geração de vídeo"
    )
    parser.add_argument(
        "--output-name",
        default="output.mp4",
        help="Nome do arquivo de vídeo final (padrão: output.mp4)"
    )
    
    args = parser.parse_args()
    
    # Validar diretório da aula
    aula_dir = Path(args.aula_dir)
    if not aula_dir.exists():
        print(f"❌ Erro: Diretório não encontrado: {aula_dir}")
        sys.exit(1)
    
    print("="*60)
    print("🎬 PIPELINE COMPLETO DE GERAÇÃO DE VÍDEO")
    print("="*60)
    print(f"📁 Diretório da aula: {aula_dir}")
    
    # 1. Verificar arquivos necessários
    docx_path = find_docx(aula_dir)
    pdf_path = find_pdf(aula_dir)
    
    if not docx_path:
        print(f"❌ Erro: Nenhum arquivo .docx encontrado em {aula_dir}")
        print("   O script.docx deve conter o roteiro com tags [slide_XX]")
        sys.exit(1)
    
    if not pdf_path:
        print(f"❌ Erro: Nenhum arquivo .pdf encontrado em {aula_dir}")
        sys.exit(1)
    
    print(f"📄 Script: {docx_path.name}")
    print(f"📊 PDF: {pdf_path.name}")
    print(f"🎤 Voice ID: {args.voice_id}")
    
    # Definir caminhos
    audio_completo = aula_dir / "audio_completo.flac"
    audios_dir = aula_dir / "audios"
    
    # 2. ETAPA 1: Gerar TTS
    if not args.skip_tts:
        cmd_tts = [
            "python",
            "minimaxAPI/minimaxAPI.py",
            str(docx_path),
            "--voice-id", args.voice_id,
            "--speed", str(args.speed),
            "--output", str(audio_completo)
        ]
        run_command(cmd_tts, "ETAPA 1/3: Gerando TTS com MiniMax")
    else:
        print(f"\n⏩ Pulando geração de TTS (usando áudio existente)")
        if not audio_completo.exists():
            print(f"❌ Erro: Áudio não encontrado: {audio_completo}")
            sys.exit(1)
    
    # 3. ETAPA 2: Separar áudios
    if not args.skip_split:
        # Criar diretório de audios se não existir
        audios_dir.mkdir(exist_ok=True)
        
        cmd_split = [
            "python",
            "separate_audios.py",
            "--input", str(audio_completo),
            "--output-dir", str(audios_dir),
            "--min-silence-sec", "5.5"
        ]
        run_command(cmd_split, "ETAPA 2/3: Separando áudios nos silêncios")
    else:
        print(f"\n⏩ Pulando separação de áudios (usando áudios existentes)")
        if not audios_dir.exists() or not list(audios_dir.glob("slide_*.wav")):
            print(f"❌ Erro: Áudios não encontrados em: {audios_dir}")
            sys.exit(1)
    
    # 4. ETAPA 3: Gerar vídeo
    if not args.skip_video:
        cmd_video = [
            "python",
            "generate_video.py",
            str(aula_dir),
            "--output-name", args.output_name
        ]
        run_command(cmd_video, "ETAPA 3/3: Gerando vídeo final")
    else:
        print(f"\n⏩ Pulando geração de vídeo")
    
    # 5. Resumo final
    print("\n" + "="*60)
    print("✨ PIPELINE CONCLUÍDO COM SUCESSO! ✨")
    print("="*60)
    
    output_video = aula_dir / args.output_name
    if output_video.exists():
        print(f"\n🎥 Vídeo gerado: {output_video}")
        print(f"📁 Áudios individuais: {audios_dir}/")
        print(f"🎵 Áudio completo: {audio_completo}")
    
    print("\n💡 Estrutura final:")
    print(f"""
    {aula_dir.name}/
      ├── {docx_path.name}
      ├── {pdf_path.name}
      ├── audio_completo.flac
      ├── audios/
      │   ├── slide_01.wav
      │   ├── slide_02.wav
      │   └── ...
      └── {args.output_name}
    """)
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
