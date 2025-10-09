## PDF to Video (PT-BR)

Script em Python para gerar um vídeo a partir de um PDF de slides, áudios por slide (OBRIGATORIAMENTE em formato `.wav`) e um `script.docx` contendo marcações como `[slide_01]`, `[short_pause]`, `[long_pause]` e `[vignette]`.

### Como funciona

- Renderiza cada página do PDF em imagem PNG numerada (`slide_01.png`, `slide_02.png`, ...).
- Descobre os áudios no diretório `audios/` pelos nomes `slide_XX.wav` (o formato deve ser WAV) e lê suas durações.
- Lê o `script.docx` e interpreta os tokens:
  - `[slide_01]`, `[slide_02]` ...: define o slide e usa o áudio correspondente se existir.
  - `[short_pause]` e `[long_pause]`: adiciona pausas com a última imagem exibida.
  - `[vignette]`: insere o vídeo `vignette.mp4` (se existir na pasta da aula).
- Concatena tudo em um único vídeo final.

Se não houver `script.docx` ou ele não contiver tokens, a ordem dos áudios encontrados é usada como fallback.

### Requisitos

- Python 3.10+
- FFmpeg no sistema (necessário para `moviepy`)

Instale as dependências:

```bash
pip install -r requirements.txt
```

### Uso (simples)

Estrutura esperada de uma pasta de aula:

```
/aula_X/
  arquivo.pdf
  script.docx (opcional)
  audios/
    slide_01.wav
    slide_02.wav
    ... (todos em `.wav`)
  vignette.mp4 (opcional)
```

1. Gerar áudios por slide automaticamente via Gemini TTS (usa API_KEY do .env):

```bash
python tts.py aulas/aula2 --voice Alnilam --model gemini-2.5-flash-preview-tts --lang pt-BR
```

2. Gerar o vídeo com alta qualidade:

```bash
python generate_video.py aulas/aula2
```

Durante a execução, o script imprime logs informando:

- Configurações efetivas (resolução, oversample, CRF/preset ou bitrate)
- Renderização dos frames do PDF com tamanhos gerados
- Descoberta e duração dos áudios por slide
- Sequência de clipes (slides, pausas, vignette)
- Progresso de encoding e caminho do arquivo final

### Observações

- Pausas usam a última imagem do slide exibido como quadro congelado.
- Se um slide tiver áudio, sua duração define a duração do clipe. Caso contrário, usa-se uma duração mínima (`--short-pause`).
- O `script.docx` deve conter tokens entre colchetes, por exemplo:

### Formato de Áudio

Os arquivos de áudio DEVEM estar em formato `.wav` (recomendado PCM 16-bit, 44.1 kHz ou 48 kHz). Caso seus áudios estejam em `.mp3` ou outro formato, converta antes de gerar o vídeo. Sugestão de ferramenta online gratuita:

https://online-audio-converter.com/pt/

Nomeie os arquivos exatamente como `slide_01.wav`, `slide_02.wav`, etc. para que o pipeline consiga associá-los aos slides.

### TTS (opções de voz e idioma)

- Modelo sugerido: `gemini-2.5-flash-preview-tts`
- Vozes pré-definidas: Alnilam, Kore, Puck, Zephyr, Encélado, etc. (consulte o AI Studio)
- Idioma: use `--lang`, ex.: `pt-BR`

```
[slide_01] [long_pause]
Introdução
[vignette]
[slide_02] [short_pause]
```
