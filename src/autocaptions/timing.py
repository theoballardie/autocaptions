"""Timing captions.

Two ways, mirroring what video platforms do:

* ``by_duration`` shares a known running time across the cues by length,
  giving pauses their own time. Good when you have the script and the video
  length but no audio to listen to.
* ``by_words`` uses word timestamps from speech recognition (see ``align``),
  the same idea as YouTube's auto-sync: the captions follow the voice.
"""
from __future__ import annotations

from dataclasses import dataclass

from .cues import Cue
from .standards import Profile
from .text import layout


@dataclass
class Piece:
    text: str
    new_sentence: bool = False
    heading: bool = False


@dataclass
class Pacing:
    lead_in: float = 0.6        # narration rarely starts on frame one
    tail: float = 0.4
    sentence_pause: float = 0.32
    heading_pause: float = 0.7
    early: float = 0.12         # captions land a touch before the word, never after
    comfortable_min: float = 1.2
    comfortable_max: float = 6.5


def _cue(start: float, end: float, text: str, profile: Profile) -> Cue:
    lines = layout(text, profile.max_chars)
    if lines is None:
        raise ValueError(f"cue cannot be laid out in {profile.max_lines} lines: {text!r}")
    return Cue(start, end, lines)


def by_duration(pieces: list[Piece], duration: float, profile: Profile, pacing: Pacing = Pacing()) -> list[Cue]:
    """Spread the pieces across ``duration`` seconds."""
    if not pieces:
        return []
    gap = profile.min_gap
    pause = [0.0] * len(pieces)
    for i, piece in enumerate(pieces[1:], 1):
        if piece.heading or pieces[i - 1].heading:
            pause[i] = pacing.heading_pause
        elif piece.new_sentence:
            pause[i] = pacing.sentence_pause
        else:
            pause[i] = gap

    lo, hi = pacing.comfortable_min, pacing.comfortable_max
    window = duration - pacing.lead_in - pacing.tail
    speak = window - sum(pause)
    if speak < len(pieces) * lo:  # short video: give the pauses back
        room = window - len(pieces) * lo
        scale = max(0.0, room / sum(pause)) if sum(pause) else 0.0
        pause = [p * scale for p in pause]
        speak = window - sum(pause)

    weight = [max(len(p.text), 12) for p in pieces]
    total = sum(weight)
    dur = [max(lo, min(hi, speak * w / total)) for w in weight]
    for _ in range(400):
        drift = sum(dur) - speak
        if abs(drift) < 0.01:
            break
        flexible = [i for i, d in enumerate(dur) if (drift > 0 and d > lo + 0.01) or (drift < 0 and d < hi - 0.01)]
        if not flexible:
            break
        for i in flexible:
            dur[i] = max(lo, min(hi, dur[i] - drift / len(flexible)))

    cues, t = [], pacing.lead_in
    for piece, p, d in zip(pieces, pause, dur):
        t += p
        cues.append(_cue(max(0.0, t - pacing.early), max(0.0, t + d - pacing.early), piece.text, profile))
        t += d
    return cues


def by_words(pieces: list[Piece], word_times: list[tuple[float, float]], profile: Profile,
             duration: float | None = None) -> list[Cue]:
    """Time each piece from the start of its first word to the end of its last.

    ``word_times`` holds one (start, end) per word of the pieces, in order.
    Cues are then stretched towards the minimum duration where the next cue
    leaves room, and never allowed to overlap.
    """
    counts = [len(p.text.split()) for p in pieces]
    if sum(counts) != len(word_times):
        raise ValueError(f"{sum(counts)} words in the pieces but {len(word_times)} word timings")
    cues, i = [], 0
    for piece, n in zip(pieces, counts):
        start, end = word_times[i][0], word_times[i + n - 1][1]
        cues.append(_cue(start, max(end, start + 0.1), piece.text, profile))
        i += n
    for k, cue in enumerate(cues):
        limit = cues[k + 1].start - profile.min_gap if k + 1 < len(cues) else (duration or cue.end + 1.0)
        want = max(cue.end + 0.25, cue.start + profile.min_duration)  # linger a moment after the last word
        cue.end = max(cue.end, min(want, limit))
    return cues
