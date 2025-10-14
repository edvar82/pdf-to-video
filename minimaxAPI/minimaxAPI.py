"""
Script para processar arquivo .docx de roteiro de aula e gerar TTS com pausas.

O script:
1. Lê um arquivo .docx com formato [slide_XX] [pause_type]
2. Remove as tags de slide e pause
3. Adiciona <#6#> (silêncio de 6 segundos) entre os segmentos
4. Envia para a API fal.ai MiniMax para gerar o áudio TTS

Uso:
    python process_script_to_tts.py <caminho_docx> [--voice-id VOICE_ID] [--output output.mp3]

Exemplo:
    python process_script_to_tts.py aula4.docx --voice-id Voicec41c71871760411371
    python process_script_to_tts.py aula4.docx --output audio_aula4.mp3
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List

import fal_client
from docx import Document
from dotenv import load_dotenv


def load_docx(file_path: str) -> str:
    """
    Carrega o conteúdo de um arquivo .docx.
    
    Args:
        file_path: Caminho para o arquivo .docx
        
    Returns:
        str: Texto completo do documento
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    
    doc = Document(file_path)
    
    # Extrair todos os parágrafos
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:  # Ignorar parágrafos vazios
            paragraphs.append(text)
    
    return "\n".join(paragraphs)


def process_script(text: str) -> str:
    """
    Processa o roteiro removendo tags e adicionando marcadores de silêncio.
    
    Formato de entrada:
        [slide_01] [long_pause]
        Texto do slide 1
        [vignette]
        [slide_02] [short_pause]
        Texto do slide 2
    
    Formato de saída:
        Texto do slide 1
        <#6#>
        Texto do slide 2
    
    Remove as tags: [slide_XX], [long_pause], [short_pause], [vignette]
    
    Args:
        text: Texto bruto do roteiro
        
    Returns:
        str: Texto processado com marcadores <#6#> (exceto no início)
    """
    # Dividir o texto em linhas
    lines = text.split('\n')
    
    processed_lines = []
    current_segment = []
    is_first_segment = True
    
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
        
        # Verificar se a linha contém tags [slide_XX], [pause] ou [vignette]
        if re.search(r'\[slide_\d+\]', line) or re.search(r'\[(long_pause|short_pause)\]', line) or re.search(r'\[vignette\]', line):
            # Se já temos um segmento acumulado, adicionar
            if current_segment:
                # Não adicionar <#6#> antes do primeiro segmento
                if not is_first_segment:
                    processed_lines.append("<#6#>")
                
                processed_lines.append(" ".join(current_segment))
                current_segment = []
                is_first_segment = False
            continue
        
        # Adicionar linha ao segmento atual
        current_segment.append(line)
    
    # Adicionar último segmento
    if current_segment:
        if not is_first_segment:
            processed_lines.append("<#6#>")
        processed_lines.append(" ".join(current_segment))
    
    return "\n".join(processed_lines)


def generate_tts(text: str, voice_id: str = "Voicec41c71871760411371", 
                 speed: float = 1.0, volume: float = 1.0, pitch: int = 0,
                 sample_rate: int = 44100, bitrate: int = 256000) -> dict:
    """
    Gera áudio TTS usando a API fal.ai MiniMax com alta qualidade.
    
    Args:
        text: Texto processado com marcadores <#6#>
        voice_id: ID da voz (padrão ou clonada)
        speed: Velocidade da fala (0.5-2.0)
        volume: Volume (0-10)
        pitch: Tom da voz (-12 a 12)
        sample_rate: Taxa de amostragem (8000, 16000, 22050, 24000, 32000, 44100)
        bitrate: Taxa de bits (32000, 64000, 128000, 256000)
        
    Returns:
        dict: Resultado da API com URL do áudio
    """
    print("🔄 Enviando para API fal.ai MiniMax...")
    print(f"📝 Tamanho do texto: {len(text)} caracteres")
    print(f"🎵 Qualidade: {sample_rate}Hz / {bitrate/1000}kbps")
    
    def on_queue_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                print(f"   {log['message']}")
    
    result = fal_client.subscribe(
        "fal-ai/minimax/preview/speech-2.5-hd",
        arguments={
            "text": text,
            "voice_setting": {
                "voice_id": voice_id,
                "speed": speed,
                "vol": volume,
                "pitch": pitch
            },
            "audio_setting": {
                "sample_rate": sample_rate,
                "bitrate": bitrate,
                "format": "flac",
                "channel": 1
            },
            "output_format": "url"
        },
        with_logs=True,
        on_queue_update=on_queue_update,
    )
    
    return result


def download_audio(url: str, output_path: str):
    """
    Baixa o áudio gerado.
    
    Args:
        url: URL do áudio
        output_path: Caminho para salvar o arquivo
    """
    import requests
    
    print(f"\n📥 Baixando áudio...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"✅ Áudio salvo em: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Processa roteiro .docx e gera TTS com pausas"
    )
    parser.add_argument(
        "docx_path",
        help="Caminho para o arquivo .docx com o roteiro"
    )
    parser.add_argument(
        "--voice-id",
        default="Voicec41c71871760411371",
        help="ID da voz para TTS (use o ID obtido do clone_voice.py ou uma voz padrão)"
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Velocidade da fala (0.5-2.0, padrão: 1.0)"
    )
    parser.add_argument(
        "--volume",
        type=float,
        default=1.0,
        help="Volume (0-10, padrão: 1.0)"
    )
    parser.add_argument(
        "--pitch",
        type=int,
        default=0,
        help="Tom da voz (-12 a 12, padrão: 0)"
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=44100,
        choices=[8000, 16000, 22050, 24000, 32000, 44100],
        help="Taxa de amostragem (padrão: 44100Hz - máxima qualidade)"
    )
    parser.add_argument(
        "--bitrate",
        type=int,
        default=256000,
        choices=[32000, 64000, 128000, 256000],
        help="Taxa de bits (padrão: 256000 - máxima qualidade)"
    )
    parser.add_argument(
        "--output",
        help="Caminho para salvar o áudio (padrão: mesmo nome do .docx com .mp3)"
    )
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="Apenas mostrar o texto processado sem gerar TTS"
    )
    
    args = parser.parse_args()
    
    # Carregar variáveis de ambiente
    load_dotenv()
    api_key = os.getenv("FAL_KEY")
    if not api_key and not args.preview_only:
        print("❌ Erro: FAL_KEY não encontrada!")
        print("\nConfigure com:")
        print("  set FAL_KEY=sua_chave_aqui  (Windows CMD)")
        sys.exit(1)
    
    if not args.preview_only:
        fal_client.api_key = api_key
    
    try:
        # 1. Carregar o arquivo .docx
        print(f"📖 Carregando arquivo: {args.docx_path}")
        raw_text = load_docx(args.docx_path)
        print(f"✅ Arquivo carregado: {len(raw_text)} caracteres")
        
        # 2. Processar o texto
        print("\n🔧 Processando texto...")
        processed_text = process_script(raw_text)
        
        # Contar segmentos
        num_segments = processed_text.count("<#6#>")
        print(f"✅ Texto processado: {num_segments} segmentos encontrados")
        
        # Mostrar preview
        print("\n" + "="*60)
        print("📝 PREVIEW DO TEXTO PROCESSADO:")
        print("="*60)
        
        # Mostrar primeiros 500 caracteres
        preview = processed_text[:500]
        if len(processed_text) > 500:
            preview += "\n\n... (truncado para preview) ..."
        print(preview)
        print("="*60 + "\n")
        
        if args.preview_only:
            print("ℹ️  Modo preview-only ativado. Não gerando TTS.")
            # Salvar texto processado em arquivo
            output_txt = Path(args.docx_path).stem + "_processed.txt"
            with open(output_txt, 'w', encoding='utf-8') as f:
                f.write(processed_text)
            print(f"💾 Texto processado salvo em: {output_txt}")
            return
        
        # 3. Gerar TTS
        result = generate_tts(
            text=processed_text,
            voice_id=args.voice_id,
            speed=args.speed,
            volume=args.volume,
            pitch=args.pitch,
            sample_rate=args.sample_rate,
            bitrate=args.bitrate
        )
        
        # 4. Extrair URL do áudio
        audio_data = result.get("audio", {})
        audio_url = audio_data.get("url") if isinstance(audio_data, dict) else None
        duration_ms = result.get("duration_ms", 0)
        
        if not audio_url:
            print("❌ Erro: URL do áudio não encontrada na resposta")
            print(f"Resposta completa: {result}")
            sys.exit(1)
        
        # Detectar extensão do arquivo a partir da URL
        from urllib.parse import urlparse
        url_path = urlparse(audio_url).path
        audio_extension = Path(url_path).suffix or ".mp3"  # fallback para .mp3
        
        print("\n" + "="*60)
        print("✨ ÁUDIO GERADO COM SUCESSO! ✨")
        print("="*60)
        print(f"\n🎵 URL do áudio: {audio_url}")
        print(f"⏱️  Duração: {duration_ms / 1000:.1f} segundos ({duration_ms / 60000:.1f} minutos)")
        
        # 5. Baixar áudio se output foi especificado
        if args.output:
            download_audio(audio_url, args.output)
        else:
            # Gerar nome automaticamente com a extensão correta
            output_path = Path(args.docx_path).stem + f"_audio{audio_extension}"
            download_audio(audio_url, output_path)
        
        print("\n💡 Próximos passos:")
        print("   1. Use seu script de corte de áudio para detectar os silêncios de 6s")
        print("   2. Sincronize os segmentos de áudio com os slides")
        print("="*60 + "\n")
        
    except FileNotFoundError as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao processar: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
