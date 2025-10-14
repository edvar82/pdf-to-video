import argparse
import math
import os
from pathlib import Path
from typing import List, Tuple

import numpy as np
from moviepy.editor import AudioFileClip


def compute_rms_windows(
	audio: np.ndarray,
	fps: int,
	frame_ms: float = 50.0,
) -> Tuple[np.ndarray, float]:
	"""
	Calcula RMS por janelas fixas ao longo do áudio.

	Parâmetros:
	  - audio: array shape (n amostras, n canais) com valores float em [-1, 1]
	  - fps: taxa de amostragem
	  - frame_ms: tamanho da janela em milissegundos

	Retorna:
	  - rms por janela (shape: [n_janelas])
	  - duração de cada janela em segundos
	"""
	if audio.ndim == 1:
		audio = audio[:, None]

	window_size = max(1, int(fps * (frame_ms / 1000.0)))
	if window_size <= 0:
		raise ValueError("frame_ms muito pequeno para o fps fornecido")

	total_samples = audio.shape[0]
	n_windows = total_samples // window_size
	usable = n_windows * window_size
	if usable == 0:
		return np.array([]), frame_ms / 1000.0

	trimmed = audio[:usable]
	# reshape para janelas: (n_windows, window_size, n_channels)
	windows = trimmed.reshape(n_windows, window_size, -1)
	# RMS por janela (agregando canais)
	rms = np.sqrt(np.mean(np.square(windows), axis=(1, 2)))
	win_sec = window_size / float(fps)
	return rms, win_sec


def compute_rms_windows_streaming(
	clip: AudioFileClip,
	fps: int,
	frame_ms: float = 50.0,
) -> Tuple[np.ndarray, float]:
	"""
	Versão streaming do cálculo de RMS por janelas, evitando materializar o áudio inteiro
	em memória e compatível com NumPy>=2 (não depende de geradores sendo stackados).

	Retorna (rms_por_janela, duracao_da_janela_em_segundos).
	"""
	window_size = max(1, int(fps * (frame_ms / 1000.0)))
	if window_size <= 0:
		raise ValueError("frame_ms muito pequeno para o fps fornecido")

	rms_list: List[float] = []
	buffer: np.ndarray | None = None

	# Definimos um tamanho de chunk explícito para evitar None na versão do moviepy
	# Escolhemos múltiplos da janela para simplificar o processamento
	chunk_size = max(window_size * 20, fps)  # ~1s ou mais, dependendo do frame e fps

	for chunk in clip.iter_chunks(fps=fps, quantize=False, chunksize=chunk_size):
		if chunk is None:
			continue
		# garantir shape 2D (amostras, canais)
		if isinstance(chunk, np.ndarray):
			if chunk.ndim == 1:
				chunk = chunk[:, None]
		else:
			# caso extremo: converter para np.array
			chunk = np.asarray(chunk)
			if chunk.ndim == 1:
				chunk = chunk[:, None]
		if chunk.size == 0:
			continue

		buffer = chunk if buffer is None else np.vstack((buffer, chunk))

		# enquanto houver amostras suficientes para uma janela
		while buffer.shape[0] >= window_size:
			win = buffer[:window_size]
			# RMS agregando canais
			r = float(np.sqrt(np.mean(np.square(win))))
			rms_list.append(r)
			buffer = buffer[window_size:]

	win_sec = window_size / float(fps)
	return np.array(rms_list, dtype=np.float32), win_sec


def detect_silences(
	audio: np.ndarray,
	fps: int,
	min_silence_sec: float = 6.0,
	silence_rms_thresh: float = 0.01,
	frame_ms: float = 50.0,
	merge_gap_sec: float = 0.3,
) -> List[Tuple[float, float]]:
	"""
	Detecta trechos de silêncio contínuo com duração >= min_silence_sec.

	- silence_rms_thresh: limiar de RMS abaixo do qual consideramos "silêncio".
	- frame_ms: tamanho de janela para cálculo de RMS.
	- merge_gap_sec: se existirem silêncios separados por buracos < merge_gap_sec,
					 agrupamos como um silêncio contínuo.

	Retorna lista de (inicio_s, fim_s) em segundos.
	"""
	rms, win_sec = compute_rms_windows(audio, fps, frame_ms)
	if rms.size == 0:
		return []

	silent_mask = rms <= silence_rms_thresh
	# Agrupar runs de True contíguos
	silences: List[Tuple[int, int]] = []
	start = None
	for i, is_silent in enumerate(silent_mask):
		if is_silent:
			if start is None:
				start = i
		else:
			if start is not None:
				silences.append((start, i))
				start = None
	if start is not None:
		silences.append((start, len(silent_mask)))

	# Filtrar por duração mínima
	min_windows = int(math.ceil(min_silence_sec / win_sec))
	silences = [(s, e) for (s, e) in silences if (e - s) >= min_windows]

	if not silences:
		return []

	# Mesclar silêncios próximos
	merged: List[Tuple[int, int]] = []
	gap_windows = int(math.floor(merge_gap_sec / win_sec))
	cur_s, cur_e = silences[0]
	for s, e in silences[1:]:
		if s - cur_e <= gap_windows:
			cur_e = e
		else:
			merged.append((cur_s, cur_e))
			cur_s, cur_e = s, e
	merged.append((cur_s, cur_e))

	# Converter para segundos
	return [(s * win_sec, e * win_sec) for (s, e) in merged]


def detect_silences_from_rms(
	rms: np.ndarray,
	win_sec: float,
	min_silence_sec: float = 6.0,
	silence_rms_thresh: float = 0.01,
	merge_gap_sec: float = 0.3,
) -> List[Tuple[float, float]]:
	"""
	Detecta silêncios a partir de uma sequência de RMS por janela.
	Retorna lista de (inicio_s, fim_s).
	"""
	if rms.size == 0:
		return []

	silent_mask = rms <= silence_rms_thresh

	# Agrupar runs de True contíguos
	silences: List[Tuple[int, int]] = []
	start = None
	for i, is_silent in enumerate(silent_mask):
		if is_silent:
			if start is None:
				start = i
		else:
			if start is not None:
				silences.append((start, i))
				start = None
	if start is not None:
		silences.append((start, len(silent_mask)))

	# Filtrar por duração mínima
	min_windows = int(math.ceil(min_silence_sec / win_sec))
	silences = [(s, e) for (s, e) in silences if (e - s) >= min_windows]

	if not silences:
		return []

	# Mesclar silêncios próximos
	merged: List[Tuple[int, int]] = []
	gap_windows = int(math.floor(merge_gap_sec / win_sec))
	cur_s, cur_e = silences[0]
	for s, e in silences[1:]:
		if s - cur_e <= gap_windows:
			cur_e = e
		else:
			merged.append((cur_s, cur_e))
			cur_s, cur_e = s, e
	merged.append((cur_s, cur_e))

	return [(s * win_sec, e * win_sec) for (s, e) in merged]


def split_points_from_silences(
	duration: float,
	silences: List[Tuple[float, float]],
	start_pad: float = 0.0,
	end_pad: float = 0.0,
) -> List[Tuple[float, float]]:
	"""
	Cria intervalos de fala a partir dos silêncios detectados.
	Ex.: [0, s1_start], [s1_end, s2_start], ..., [last_end, duration]
	"""
	if not silences:
		# Um único segmento cobrindo tudo, com padding aplicado e truncado aos limites
		seg_start = max(0.0, 0.0 - start_pad)
		seg_end = min(duration, duration + end_pad)
		if seg_end - seg_start <= 1e-3:
			return []
		return [(seg_start, seg_end)]

	points: List[Tuple[float, float]] = []
	prev = 0.0  # início do trecho de fala atual (antes do silêncio)
	for (s_start, s_end) in silences:
		# segmento de fala termina pouco depois do início do silêncio (end_pad)
		seg_end = min(duration, s_start + max(0.0, end_pad))
		# início do segmento de fala com um pequeno pre-roll (start_pad)
		seg_start = max(0.0, prev - max(0.0, start_pad))
		# evitar sobreposição com o segmento anterior
		if points:
			seg_start = max(seg_start, points[-1][1])
		if seg_end - seg_start > 1e-3:
			points.append((seg_start, seg_end))
		# próximo trecho de fala inicia após o fim do silêncio
		prev = max(prev, s_end)

	# último segmento após o último silêncio até o fim
	if prev < duration:
		seg_start = max(0.0, prev - max(0.0, start_pad))
		if points:
			seg_start = max(seg_start, points[-1][1])
		seg_end = duration
		if seg_end - seg_start > 1e-3:
			points.append((seg_start, seg_end))

	return points


def export_segments(
	src_path: Path,
	out_dir: Path,
	segments: List[Tuple[float, float]],
	fps: int,
	codec: str = "pcm_s16le",
) -> List[Path]:
	out_paths: List[Path] = []
	base = src_path.stem
	for idx, (t1, t2) in enumerate(segments, start=1):
		# Formato: slide_01, slide_02, slide_03, etc.
		out_path = out_dir / f"slide_{idx:02d}.wav"
		with AudioFileClip(str(src_path)) as clip:
			sub = clip.subclip(t1, t2)
			sub.write_audiofile(
				str(out_path),
				fps=fps,
				codec=codec,
				verbose=False,
				logger=None,
			)
		out_paths.append(out_path)
	return out_paths


def process_file(
	file_path: Path,
	out_dir: Path,
	min_silence_sec: float,
	silence_rms_thresh: float,
	frame_ms: float,
	merge_gap_sec: float,
	target_detection_fps: int | None,
	dry_run: bool,
) -> List[Path]:
	out_dir.mkdir(parents=True, exist_ok=True)
	with AudioFileClip(str(file_path)) as clip:
		# Para detecção, podemos reduzir FPS para acelerar
		det_fps = target_detection_fps or int(getattr(clip, "fps", 44100))
		rms, win_sec = compute_rms_windows_streaming(clip, fps=det_fps, frame_ms=frame_ms)
		silences = detect_silences_from_rms(
			rms=rms,
			win_sec=win_sec,
			min_silence_sec=min_silence_sec,
			silence_rms_thresh=silence_rms_thresh,
			merge_gap_sec=merge_gap_sec,
		)
		# Aplicar padding para evitar cortes precoces
		segments = split_points_from_silences(
			clip.duration,
			silences,
			start_pad=getattr(args_holder, "start_pad", 0.0),
			end_pad=getattr(args_holder, "end_pad", 0.0),
		)

		if dry_run:
			print(f"[DRY-RUN] {file_path.name}: {len(silences)} silêncio(s) longo(s) encontrado(s)")
			for (s, e) in silences:
				print(f"  silêncio entre {s:.2f}s e {e:.2f}s (dur={e-s:.2f}s)")
			print(f"  Geraria {len(segments)} segmento(s):")
			for i, (a, b) in enumerate(segments, 1):
				print(f"    {i}: {a:.2f}s -> {b:.2f}s (dur={b-a:.2f}s)")
			return []

		# Para export, manter fps de saída igual ao original do arquivo
		export_fps = int(getattr(clip, "fps", det_fps))
		return export_segments(file_path, out_dir, segments, fps=export_fps)


def is_audio_file(path: Path) -> bool:
	return path.suffix.lower() in {".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg"}


def parse_args() -> argparse.Namespace:
	p = argparse.ArgumentParser(
		description=(
			"Divide áudios em segmentos usando detecção de silêncio contínuo (ex.: ~6s).\n"
			"Ex.: arquivo.wav -> arquivo.1.wav, arquivo.2.wav, ..."
		)
	)
	g_input = p.add_mutually_exclusive_group(required=True)
	g_input.add_argument("--input", type=str, help="Arquivo de áudio para processar")
	g_input.add_argument(
		"--input-dir", type=str, help="Diretório contendo áudios a processar (recursivo)"
	)
	p.add_argument(
		"--output-dir",
		type=str,
		default=None,
		help="Diretório de saída (padrão: ao lado do arquivo ou subpasta 'segments')",
	)
	p.add_argument(
		"--min-silence-sec",
		type=float,
		default=5.5,
		help="Duração mínima (s) para considerar silêncio longo (padrão: 5.5)",
	)
	p.add_argument(
		"--silence-threshold",
		type=float,
		default=0.01,
		help="Limiar RMS para silêncio (0-1). Menor = mais sensível (padrão: 0.01)",
	)
	p.add_argument(
		"--frame-ms",
		type=float,
		default=50.0,
		help="Tamanho da janela (ms) para RMS (padrão: 50 ms)",
	)
	p.add_argument(
		"--merge-gap-sec",
		type=float,
		default=0.3,
		help="Une silêncios separados por buracos < X seg (padrão: 0.3)",
	)
	p.add_argument(
		"--detection-fps",
		type=int,
		default=16000,
		help="FPS para detecção (downsample). Maior = mais preciso, mais lento (padrão: 16000)",
	)
	p.add_argument(
		"--start-pad",
		type=float,
		default=0.15,
		help="Antecipação (s) no INÍCIO de cada segmento de fala (pre-roll). Evita cortar o ataque da fala (padrão: 0.15s)",
	)
	p.add_argument(
		"--end-pad",
		type=float,
		default=0.25,
		help="Extensão (s) no FIM de cada segmento de fala (post-roll). Evita cortar o final da fala (padrão: 0.25s)",
	)
	p.add_argument(
		"--dry-run",
		action="store_true",
		help="Não salva arquivos, apenas mostra onde cortaria",
	)
	return p.parse_args()


def main():
	args = parse_args()

	# Disponibiliza args para uso em funções internas sem alterar muitas assinaturas
	global args_holder
	args_holder = args

	targets: List[Path] = []
	if args.input:
		targets = [Path(args.input)]
	else:
		root = Path(args.input_dir)
		if not root.exists():
			raise SystemExit(f"Diretório não encontrado: {root}")
		for p in root.rglob("*"):
			if p.is_file() and is_audio_file(p):
				targets.append(p)

	if not targets:
		raise SystemExit("Nenhum arquivo de áudio encontrado para processar.")

	for file_path in targets:
		base_out = Path(args.output_dir) if args.output_dir else None
		if base_out is None:
			# se processando vários, cria subpasta 'segments' ao lado do arquivo
			base_out = file_path.parent / "segments"
		out_dir = base_out

		print(f"Processando: {file_path}")
		generated = process_file(
			file_path=file_path,
			out_dir=out_dir,
			min_silence_sec=args.min_silence_sec,
			silence_rms_thresh=args.silence_threshold,
			frame_ms=args.frame_ms,
			merge_gap_sec=args.merge_gap_sec,
			target_detection_fps=args.detection_fps,
			dry_run=args.dry_run,
		)
		if not args.dry_run:
			print(f"  -> {len(generated)} segmento(s) salvo(s) em: {out_dir}")


if __name__ == "__main__":
	main()

