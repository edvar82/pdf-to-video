## PDF to Video com TTS Automatizado (PT-BR)

Pipeline completo em Python para gerar vídeos de aulas a partir de PDF de slides e roteiro, com narração por TTS usando a API MiniMax (fal.ai).

### 🎯 Workflow Completo

Este projeto oferece dois modos de uso:

1. **Pipeline Automatizado** (Recomendado): Um único comando que executa tudo
2. **Pipeline Manual**: Controle fino de cada etapa

---

## 🚀 Pipeline Automatizado (Modo Rápido)

### Pré-requisitos

1. **Estrutura da pasta da aula:**

```
aulas/aulaX/
  ├── script.docx    # Roteiro com tags [slide_XX]
  └── slides.pdf     # PDF dos slides
```

2. **Configurar API Key:**

```bash
# Windows CMD
set FAL_KEY=sua_chave_aqui

# PowerShell
$env:FAL_KEY="sua_chave_aqui"

# Ou criar arquivo .env na raiz:
FAL_KEY=sua_chave_aqui
```

3. **Instalar dependências:**

```bash
pip install -r requirements.txt
```

### Uso Rápido

```bash
# Executar pipeline completo
python pipeline_completo.py aulas/aula5 --voice-id SEU_VOICE_ID
```

**Pronto!** O script vai:

1. ✅ Processar o `script.docx` e gerar TTS (áudio completo em FLAC)
2. ✅ Separar o áudio automaticamente nos silêncios de 6s (`slide_01.wav`, `slide_02.wav`, ...)
3. ✅ Gerar o vídeo final com slides + áudios sincronizados

### Resultado

```
aulas/aulaX/
  ├── script.docx
  ├── slides.pdf
  ├── audio_completo.flac       ← Gerado (TTS completo)
  ├── audios/                   ← Gerado
  │   ├── slide_01.wav
  │   ├── slide_02.wav
  │   ├── slide_03.wav
  │   └── ...
  └── output.mp4                ← Vídeo final!
```

---

## 📋 Pipeline Manual (Controle Fino)

### Etapa 0: Clonar sua voz (opcional, uma vez)

```bash
python minimaxAPI/clone_voice.py minha_voz.mp3
```

Isso retorna um `VOICE_ID` que você usará no TTS. O ID expira em 7 dias se não for usado.

### Etapa 1: Preparar o roteiro (script.docx)

O `script.docx` deve conter tags especiais que marcam os slides e pausas:

**Formato correto:**

```
[slide_01] [long_pause]
Aula 4: Treinamento de Modelos de Visão Computacional.
Hoje vamos explorar um dos temas mais centrais da visão computacional...

[slide_02] [short_pause]
O conteúdo da aula de hoje está dividido em sete partes principais.
Primeiro, faremos uma introdução aos conceitos básicos...

[slide_03] [short_pause]
Depois, discutiremos como escolher a arquitetura ideal para o problema.
```

**Tags disponíveis:**

- `[slide_01]`, `[slide_02]`, ... → Marca o slide
- `[long_pause]` ou `[short_pause]` → Define o tipo de pausa (ignorada pelo TTS, mas útil para documentação)

### Etapa 2: Gerar TTS com MiniMax

```bash
python minimaxAPI/minimaxAPI.py aulas/aula5/script.docx --voice-id SEU_VOICE_ID --output aulas/aula5/audio_completo.flac
```

**Opções:**

- `--voice-id`: ID da voz (padrão ou clonada)
- `--speed`: Velocidade (0.5-2.0, padrão: 1.0)
- `--pitch`: Tom da voz (-12 a 12, padrão: 0)
- `--sample-rate`: Taxa de amostragem (padrão: 44100Hz)
- `--bitrate`: Taxa de bits (padrão: 256000)
- `--preview-only`: Apenas ver o texto processado sem gerar TTS

**O script vai:**

1. Ler o `.docx`
2. Remover as tags `[slide_XX]` e `[pause]`
3. Adicionar marcadores `<#6#>` (silêncio de 6 segundos) entre os segmentos
4. Gerar o TTS em alta qualidade (FLAC 44100Hz)

### Etapa 3: Separar áudios nos silêncios

```bash
python separate_audios.py --input aulas/aula5/audio_completo.flac --output-dir aulas/aula5/audios --min-silence-sec 5.5
```

**O que faz:**

- Detecta silêncios de ~6 segundos no áudio
- Corta e salva como `slide_01.wav`, `slide_02.wav`, ...
- Os nomes seguem o padrão para sincronizar com os slides do PDF

**Opções úteis:**

- `--min-silence-sec`: Duração mínima do silêncio (padrão: 5.5s)
- `--silence-threshold`: Sensibilidade (0-1, padrão: 0.01)
- `--dry-run`: Ver onde cortaria sem salvar arquivos

### Etapa 4: Gerar o vídeo final

```bash
python generate_video.py aulas/aula5
```

**O script vai:**

1. Renderizar cada página do PDF como imagem
2. Associar cada slide com seu áudio (`slide_01.wav` → slide 1)
3. Concatenar tudo em um vídeo sincronizado

**Opções de qualidade:**

```bash
# Alta qualidade (padrão)
python generate_video.py aulas/aula5 --crf 16 --preset slow

# Qualidade máxima (mais lento)
python generate_video.py aulas/aula5 --crf 14 --preset slower

# Com bitrate fixo
python generate_video.py aulas/aula5 --bitrate 8000k
```

---

## 🎤 Vozes Disponíveis

### Vozes pré-definidas (MiniMax)

- `Wise_Woman` (padrão) - Voz feminina sábia
- Outras vozes disponíveis na documentação da API

### Clonar sua própria voz

```bash
python minimaxAPI/clone_voice.py minha_voz.mp3 --text "Olá, esta é minha voz clonada!"
```

**Requisitos:**

- Áudio com pelo menos 10 segundos
- Formatos aceitos: MP3, WAV, FLAC
- Qualidade clara sem muito ruído de fundo

---

## 📁 Estrutura Completa de uma Aula


```
/aulas/aulaX/
  ├── script.docx              # Roteiro com tags [slide_XX]
  ├── slides.pdf               # PDF dos slides
  ├── audio_completo.flac      # (gerado) TTS completo
  ├── audios/                  # (gerado) Áudios por slide
  │   ├── slide_01.wav
  │   ├── slide_02.wav
  │   ├── slide_03.wav
  │   └── ...
  ├── output/                  # (gerado) Frames renderizados
  │   └── frames/
  │       ├── slide_01.png
  │       ├── slide_02.png
  │       └── ...
  ├── output.mp4               # (gerado) Vídeo final
  └── vignette.mp4             # (opcional) Vídeo de abertura/encerramento
```

---

## ⚙️ Opções Avançadas

### Pipeline Automatizado

```bash
# Pipeline completo
python pipeline_completo.py aulas/aula5 --voice-id SEU_VOICE_ID

# Ajustar velocidade da fala
python pipeline_completo.py aulas/aula5 --voice-id SEU_VOICE_ID --speed 1.1

# Pular etapas (usar arquivos existentes)
python pipeline_completo.py aulas/aula5 --voice-id SEU_VOICE_ID --skip-tts
python pipeline_completo.py aulas/aula5 --voice-id SEU_VOICE_ID --skip-split
python pipeline_completo.py aulas/aula5 --voice-id SEU_VOICE_ID --skip-video

# Nome personalizado para o vídeo
python pipeline_completo.py aulas/aula5 --voice-id SEU_VOICE_ID --output-name aula5_final.mp4
```

### Visualizar texto processado (sem gerar TTS)

```bash
python minimaxAPI/minimaxAPI.py aulas/aula5/script.docx --preview-only
```

Isso mostra como o texto ficará após processar as tags e salva em `script_processed.txt`.

### Testar corte de áudio (dry-run)

```bash
python separate_audios.py --input audio.flac --output-dir test --dry-run
```

Mostra onde o áudio seria cortado sem salvar os arquivos.

---

## 🎛️ Configurações de Qualidade

### Qualidade de Áudio (TTS)

```bash
# Máxima qualidade (FLAC lossless)
python minimaxAPI/minimaxAPI.py script.docx --sample-rate 44100 --bitrate 256000

# MP3 alta qualidade
# (edite minimaxAPI.py linha 154: "format": "mp3")
python minimaxAPI/minimaxAPI.py script.docx --sample-rate 44100 --bitrate 256000
```

### Qualidade de Vídeo

```bash
# Qualidade máxima (arquivo maior, mais lento)
python generate_video.py aulas/aula5 --crf 14 --preset slower --pdf-oversample 3.0

# Qualidade alta (padrão recomendado)
python generate_video.py aulas/aula5 --crf 16 --preset slow --pdf-oversample 2.0

# Qualidade boa (mais rápido)
python generate_video.py aulas/aula5 --crf 20 --preset medium

# Bitrate fixo (para upload/streaming)
python generate_video.py aulas/aula5 --bitrate 8000k
```

**Parâmetros:**

- `--crf`: Qualidade (14-28, menor = melhor qualidade, padrão: 16)
- `--preset`: Velocidade de encoding (ultrafast, fast, medium, slow, slower, padrão: slow)
- `--pdf-oversample`: Qualidade dos slides (1.0-4.0, padrão: 2.0)
- `--bitrate`: Taxa de bits fixa (sobrepõe CRF/preset)

---

## 🔧 Solução de Problemas

### Erro: "FAL_KEY não encontrada"

Configure a variável de ambiente:

```bash
set FAL_KEY=sua_chave_aqui
```

Ou crie um arquivo `.env` na raiz do projeto.

### Áudios não sincronizam com slides

Verifique se:

1. As tags `[slide_XX]` estão corretas no `script.docx`
2. Os silêncios de 6s foram inseridos entre os segmentos
3. Os arquivos foram nomeados como `slide_01.wav`, `slide_02.wav`, etc.

### Áudio cortado incorretamente

Ajuste os parâmetros de detecção:

```bash
# Silêncios mais longos
python separate_audios.py --input audio.flac --min-silence-sec 6.5

# Mais sensível a silêncios
python separate_audios.py --input audio.flac --silence-threshold 0.005

# Ver onde vai cortar antes
python separate_audios.py --input audio.flac --dry-run
```

### Vídeo com qualidade ruim

Aumente a qualidade:

```bash
python generate_video.py aulas/aula5 --crf 14 --preset slower --pdf-oversample 3.0
```

---

## 📚 Exemplos Práticos

### Exemplo 1: Aula nova do zero

```bash
# 1. Clonar sua voz (uma vez)
python minimaxAPI/clone_voice.py minha_voz.mp3
# Anote o VOICE_ID retornado

# 2. Preparar a pasta
mkdir -p aulas/aula6
# Coloque script.docx e slides.pdf na pasta

# 3. Executar pipeline
python pipeline_completo.py aulas/aula6 --voice-id SEU_VOICE_ID

# Pronto! Vídeo em aulas/aula6/output.mp4
```

### Exemplo 2: Regenerar apenas o vídeo

```bash
# Pular TTS e separação de áudios
python pipeline_completo.py aulas/aula6 --voice-id SEU_VOICE_ID --skip-tts --skip-split
```

### Exemplo 3: Ajustar velocidade da narração

```bash
# Fala mais rápida
python minimaxAPI/minimaxAPI.py script.docx --voice-id SEU_VOICE_ID --speed 1.2 --output audio_rapido.flac

# Fala mais lenta
python minimaxAPI/minimaxAPI.py script.docx --voice-id SEU_VOICE_ID --speed 0.9 --output audio_lento.flac
```

---

## 📖 Documentação das APIs

### Scripts Principais

- **`pipeline_completo.py`**: Pipeline automatizado (TTS → Separar → Vídeo)
- **`minimaxAPI/minimaxAPI.py`**: Geração de TTS com MiniMax
- **`minimaxAPI/clone_voice.py`**: Clonagem de voz
- **`separate_audios.py`**: Separação de áudios por silêncios
- **`generate_video.py`**: Geração do vídeo final

### Formato do script.docx

Tags suportadas:

- `[slide_01]`, `[slide_02]`, ... → Marcam slides
- `[long_pause]`, `[short_pause]` → Pausas (documentação)
- `[vignette]` → Insere vídeo de abertura/encerramento
