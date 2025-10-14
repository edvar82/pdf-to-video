import os
import sys
import argparse
import fal_client
from pathlib import Path


def clone_voice(audio_path: str, preview_text: str = None, model: str = "speech-02-hd", 
                noise_reduction: bool = True, volume_normalization: bool = True):
    """
    Clona uma voz a partir de um arquivo de áudio.
    
    Args:
        audio_path: Caminho para o arquivo de áudio (mínimo 10 segundos)
        preview_text: Texto para gerar preview com a voz clonada
        model: Modelo TTS para o preview (speech-02-hd, speech-02-turbo, etc.)
        noise_reduction: Habilitar redução de ruído
        volume_normalization: Habilitar normalização de volume
    
    Returns:
        dict: Resposta da API com voice_id e preview_audio_url
    """
    
    # Verificar se o arquivo existe
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {audio_path}")
    
    print(f"📤 Fazendo upload do áudio: {audio_path}")
    
    # Upload do arquivo para o fal.ai
    audio_url = fal_client.upload_file(audio_path)
    print(f"✅ Upload concluído: {audio_url}")
    
    # Preparar argumentos
    arguments = {
        "audio_url": audio_url,
        "noise_reduction": noise_reduction,
        "need_volume_normalization": volume_normalization,
        "model": model
    }
    
    # Adicionar texto de preview se fornecido
    if preview_text:
        arguments["text"] = preview_text
    else:
        # Usar texto padrão em português
        arguments["text"] = "Olá, este é um preview da sua voz clonada! Espero que você goste do resultado."
    
    print(f"\n🔄 Clonando voz com modelo {model}...")
    print("⏳ Isso pode levar alguns segundos...\n")
    
    # Fazer requisição de clonagem
    def on_queue_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                print(f"   {log['message']}")
    
    result = fal_client.subscribe(
        "fal-ai/minimax/voice-clone",
        arguments=arguments,
        with_logs=True,
        on_queue_update=on_queue_update,
    )
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Clone uma voz e obtenha o voice_id para usar no TTS MiniMax"
    )
    parser.add_argument(
        "audio_path",
        help="Caminho para o arquivo de áudio (mínimo 10 segundos)"
    )
    parser.add_argument(
        "--text",
        default=None,
        help="Texto para o preview de áudio (opcional)"
    )
    parser.add_argument(
        "--model",
        default="speech-02-hd",
        choices=["speech-02-hd", "speech-02-turbo", "speech-01-hd", "speech-01-turbo"],
        help="Modelo TTS para o preview (padrão: speech-02-hd)"
    )
    parser.add_argument(
        "--no-noise-reduction",
        action="store_true",
        help="Desabilitar redução de ruído"
    )
    parser.add_argument(
        "--no-volume-normalization",
        action="store_true",
        help="Desabilitar normalização de volume"
    )
    
    args = parser.parse_args()
    
    # Verificar se FAL_KEY está configurado
    if not os.getenv("FAL_KEY"):
        print("❌ Erro: Variável de ambiente FAL_KEY não está configurada!")
        print("\nConfigure com:")
        print("  set FAL_KEY=sua_chave_aqui  (Windows CMD)")
        print("  $env:FAL_KEY=\"sua_chave_aqui\"  (PowerShell)")
        sys.exit(1)
    
    try:
        result = clone_voice(
            audio_path=args.audio_path,
            preview_text=args.text,
            model=args.model,
            noise_reduction=not args.no_noise_reduction,
            volume_normalization=not args.no_volume_normalization
        )
        
        print("\n" + "="*60)
        print("✨ VOZ CLONADA COM SUCESSO! ✨")
        print("="*60)
        
        # Extrair voice_id da resposta
        voice_id = result.get("voice_id")
        preview_audio = result.get("preview_audio", {})
        preview_url = preview_audio.get("url") if isinstance(preview_audio, dict) else None
        
        if voice_id:
            print(f"\n🎤 VOICE_ID: {voice_id}")
            print("\n📝 Use este ID no seu script TTS:")
            print(f'''
result = fal_client.subscribe(
    "fal-ai/minimax/preview/speech-2.5-hd",
    arguments={{
        "text": "Seu texto aqui",
        "voice_setting": {{
            "voice_id": "{voice_id}",
            "speed": 1,
            "vol": 1,
            "pitch": 0
        }}
    }}
)
''')
        
        if preview_url:
            print(f"\n🔊 Preview de áudio: {preview_url}")
        
        print("\n⚠️  IMPORTANTE:")
        print("   - Este voice_id expira em 7 dias se não for usado")
        print("   - Use-o em pelo menos 1 requisição TTS para mantê-lo ativo")
        print("="*60 + "\n")
        
        # Mostrar resposta completa
        print("📄 Resposta completa da API:")
        print(result)
        
    except FileNotFoundError as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro ao clonar voz: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
