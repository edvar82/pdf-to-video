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
    
    segments = []
    current_segment = []
    
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
        
        # Verificar se a linha contém tag de slide (marca início de novo segmento)
        if re.search(r'\[slide_\d+\]', line):
            # Salvar segmento anterior se houver conteúdo
            if current_segment:
                segments.append(" ".join(current_segment))
                current_segment = []
            
            # Limpar todas as tags desta linha
            cleaned_line = re.sub(r'\[slide_\d+\]', '', line)
            cleaned_line = re.sub(r'\[(long_pause|short_pause)\]', '', cleaned_line)
            cleaned_line = re.sub(r'\[vignette\]', '', cleaned_line)
            cleaned_line = cleaned_line.strip()
            
            # Se tinha conteúdo além das tags, adiciona ao novo segmento
            if cleaned_line:
                current_segment.append(cleaned_line)
        
        # Verificar se tem tags de pause/vignette sem slide
        elif re.search(r'\[(long_pause|short_pause|vignette)\]', line):
            # Remove as tags
            cleaned_line = re.sub(r'\[(long_pause|short_pause|vignette)\]', '', line)
            cleaned_line = cleaned_line.strip()
            
            # Se tinha conteúdo, adiciona ao segmento atual
            if cleaned_line:
                current_segment.append(cleaned_line)
        
        else:
            # Linha normal sem tags
            current_segment.append(line)
    
    # Adicionar último segmento
    if current_segment:
        segments.append(" ".join(current_segment))
    
    # Juntar segmentos com marcador <#6#>
    return "\n<#6#>\n".join(segments)


def split_text_for_tts(text: str, max_chars: int = 4500) -> List[str]:
    """
    Divide texto longo em chunks menores respeitando os marcadores <#6#>.
    
    Se o texto for menor que max_chars, retorna uma lista com o texto único.
    Caso contrário, quebra nos marcadores <#6#> sem ultrapassar o limite.
    
    IMPORTANTE: Adiciona <#6#> no início de chunks intermediários (exceto o primeiro)
    para manter a separação quando os áudios forem combinados.
    
    Args:
        text: Texto processado com marcadores <#6#>
        max_chars: Tamanho máximo de cada chunk (default: 4500 para margem de segurança)
        
    Returns:
        List[str]: Lista de chunks de texto
    """
    if len(text) <= max_chars:
        return [text]
    
    # Dividir pelo marcador de silêncio
    parts = text.split("\n<#6#>\n")
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for i, part in enumerate(parts):
        part_size = len(part)
        # +7 para o marcador \n<#6#>\n que será adicionado entre partes
        separator_size = 7 if current_chunk else 0
        
        # Se adicionar esta parte ultrapassar o limite E já temos algo no chunk
        if current_size + part_size + separator_size > max_chars and current_chunk:
            # Salvar chunk atual
            chunk_text = "\n<#6#>\n".join(current_chunk)
            chunks.append(chunk_text)
            
            # Iniciar novo chunk com esta parte
            current_chunk = [part] if part else []
            current_size = part_size
        else:
            # Adicionar ao chunk atual
            current_chunk.append(part)
            current_size += part_size + separator_size
    
    # Adicionar último chunk
    if current_chunk:
        chunk_text = "\n<#6#>\n".join(current_chunk)
        chunks.append(chunk_text)
    
    # IMPORTANTE: Adicionar <#6#> no início dos chunks 2, 3, etc.
    # Isso garante que haverá uma pausa de 6s entre os chunks quando combinados
    for i in range(1, len(chunks)):
        chunks[i] = "<#6#>\n" + chunks[i]
    
    return chunks


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


def generate_and_combine_audio(text: str, voice_id: str, output_path: str, **tts_kwargs) -> dict:
    """
    Gera áudio TTS dividindo em chunks se necessário e combina os resultados.
    
    Args:
        text: Texto processado
        voice_id: ID da voz
        output_path: Caminho para salvar o áudio final
        **tts_kwargs: Argumentos adicionais para generate_tts (speed, volume, etc.)
        
    Returns:
        dict: Informações sobre o áudio gerado
    """
    chunks = split_text_for_tts(text)
    
    if len(chunks) == 1:
        # Texto não precisa ser dividido
        print(f"📝 Texto cabe em um único áudio ({len(text)} caracteres)")
        result = generate_tts(text, voice_id, **tts_kwargs)
        audio_url = result.get("audio", {}).get("url")
        if audio_url:
            download_audio(audio_url, output_path)
        return result
    
    # Precisa dividir em múltiplos áudios
    print(f"⚠️  Texto muito longo ({len(text)} caracteres)")
    print(f"📦 Dividindo em {len(chunks)} partes para processamento")
    
    temp_audio_paths = []
    total_duration_ms = 0
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\n🔄 Processando parte {i}/{len(chunks)} ({len(chunk)} caracteres)...")
        result = generate_tts(chunk, voice_id, **tts_kwargs)
        
        audio_data = result.get("audio", {})
        audio_url = audio_data.get("url") if isinstance(audio_data, dict) else None
        
        if not audio_url:
            raise RuntimeError(f"Erro ao gerar áudio da parte {i}")
        
        # Salvar áudio temporário
        temp_path = f"{output_path}.part{i}.flac"
        download_audio(audio_url, temp_path)
        temp_audio_paths.append(temp_path)
        
        duration_ms = result.get("duration_ms", 0)
        total_duration_ms += duration_ms
    
    # Combinar áudios usando moviepy
    print(f"\n🔗 Combinando {len(temp_audio_paths)} áudios...")
    try:
        from moviepy.editor import AudioFileClip, concatenate_audioclips
        
        audio_clips = []
        for temp_path in temp_audio_paths:
            audio_clip = AudioFileClip(temp_path)
            audio_clips.append(audio_clip)
        
        # Concatenar áudios (não precisa adicionar silêncio, já está no texto!)
        combined = concatenate_audioclips(audio_clips)
        
        # Exportar áudio combinado
        combined.write_audiofile(output_path, codec='flac', verbose=False, logger=None)
        
        # Fechar clipes
        for clip in audio_clips:
            clip.close()
        combined.close()
        
        print(f"✅ Áudios combinados em: {output_path}")
        
        # Remover arquivos temporários
        for temp_path in temp_audio_paths:
            Path(temp_path).unlink(missing_ok=True)
        
        return {
            "audio": {"url": f"file://{output_path}"},
            "duration_ms": total_duration_ms,
            "chunks": len(chunks)
        }
    
    except Exception as e:
        print(f"⚠️  Erro ao combinar áudios: {e}")
        print(f"   Mantendo áudios separados.")
        print(f"   Arquivos salvos como: {output_path}.part1.flac, {output_path}.part2.flac, etc.")
        return {
            "audio": {"url": f"file://{temp_audio_paths[0]}"},
            "duration_ms": total_duration_ms,
            "chunks": len(chunks),
            "temp_files": temp_audio_paths
        }


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
        num_segments = processed_text.count("\n<#6#>\n") + 1  # +1 porque não tem marcador antes do primeiro
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
        
        # Determinar caminho de saída
        if args.output:
            output_path = args.output
        else:
            output_path = Path(args.docx_path).stem + "_audio.flac"
        
        # 3. Gerar TTS (com divisão automática se necessário)
        tts_kwargs = {
            'speed': args.speed,
            'volume': args.volume,
            'pitch': args.pitch,
            'sample_rate': args.sample_rate,
            'bitrate': args.bitrate
        }
        
        result = generate_and_combine_audio(
            text=processed_text,
            voice_id=args.voice_id,
            output_path=output_path,
            **tts_kwargs
        )
        
        # 4. Mostrar resultado
        duration_ms = result.get("duration_ms", 0)
        num_chunks = result.get("chunks", 1)
        
        print("\n" + "="*60)
        print("✨ ÁUDIO GERADO COM SUCESSO! ✨")
        print("="*60)
        if num_chunks > 1:
            print(f"📦 Texto dividido em {num_chunks} partes e combinado")
        print(f"⏱️  Duração: {duration_ms / 1000:.1f} segundos ({duration_ms / 60000:.1f} minutos)")
        print(f"📁 Áudio salvo em: {output_path}")
        
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
