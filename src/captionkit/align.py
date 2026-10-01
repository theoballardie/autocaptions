"""Listening to the audio: speech recognition and transcript alignment.

This is the open-source equivalent of the two things YouTube does with sound:

* automatic captions: recognise the speech and time every word
  (``transcribe``);
* auto-sync: take the exact script and line each word up with the moment it
  is spoken (``align``), so the wording stays approved and only the timing
  comes from the audio.

Recognition uses faster-whisper (an implementation of OpenAI's Whisper),
installed with ``pip install "captionkit[audio]"``. Models download on first
use and run locally; no audio leaves the machine.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from .text import tokens


@dataclass
class Word:
    text: str
    start: float
    end: float


def transcribe(audio: str, model: str = "small.en", language: str | None = None) -> list[Word]:
    """Recognise speech in ``audio`` and return timed words."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit('audio features need faster-whisper: pip install "captionkit[audio]"') from None
    recogniser = WhisperModel(model, device="auto", compute_type="auto")
    samples = load_audio(audio)
    segments, _ = recogniser.transcribe(samples, word_timestamps=True, language=language, vad_filter=True)
    words: list[Word] = []
    for segment in segments:
        for w in segment.words or []:
            for part in w.word.strip().split():
                words.append(Word(part, float(w.start), float(w.end)))
    return words


def load_audio(path: str, rate: int = 16000):
    """Decode any audio or video file to mono 16 kHz float samples, as Whisper expects."""
    import av
    import numpy as np

    chunks = []
    resampler = av.AudioResampler(format="s16", layout="mono", rate=rate)
    with av.open(path) as container:
        stream = container.streams.audio[0]
        for frame in container.decode(stream):
            chunks.extend(f.to_ndarray() for f in resampler.resample(frame))
        chunks.extend(f.to_ndarray() for f in resampler.resample(None))
    if not chunks:
        raise SystemExit(f"no audio found in {path}")
    return np.concatenate(chunks, axis=1).reshape(-1).astype(np.float32) / 32768.0


def align(script_words: list[str], heard: list[Word]) -> list[tuple[float, float]]:
    """Give every script word a (start, end), using what the recogniser heard.

    Words are matched after normalising case and punctuation. Where the
    recogniser misheard or missed words, their time is shared out between the
    nearest matched neighbours in proportion to word length, so every script
    word gets a time and the order is always preserved.
    """
    if not script_words:
        return []
    if not heard:
        raise ValueError("no speech was recognised in the audio")

    script_keys = [" ".join(tokens(w)) for w in script_words]
    heard_keys = [" ".join(tokens(w.text)) for w in heard]
    times: list[tuple[float, float] | None] = [None] * len(script_words)

    matcher = SequenceMatcher(None, script_keys, heard_keys, autojunk=False)
    for op, s0, s1, h0, h1 in matcher.get_opcodes():
        if op == "equal":
            for k in range(s1 - s0):
                times[s0 + k] = (heard[h0 + k].start, heard[h0 + k].end)
        elif op == "replace":
            # misheard run: spread the heard span over the script words by length
            span_start, span_end = heard[h0].start, heard[h1 - 1].end
            weights = [max(len(script_words[i]), 1) for i in range(s0, s1)]
            total, t = sum(weights), span_start
            for i, w in zip(range(s0, s1), weights):
                step = (span_end - span_start) * w / total
                times[i] = (t, t + step)
                t += step

    _fill_gaps(script_words, times, heard)
    return times  # type: ignore[return-value]


def _fill_gaps(words: list[str], times: list[tuple[float, float] | None], heard: list[Word]) -> None:
    """Interpolate words the recogniser did not hear between their neighbours."""
    n, i = len(times), 0
    while i < n:
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < n and times[j] is None:
            j += 1
        left = times[i - 1][1] if i > 0 else heard[0].start
        right = times[j][0] if j < n else heard[-1].end
        if right < left:
            right = left
        weights = [max(len(words[k]), 1) for k in range(i, j)]
        total, t = sum(weights), left
        for k, w in zip(range(i, j), weights):
            step = (right - left) * w / total
            times[k] = (t, t + step)
            t += step
        i = j
