"""From script (or audio) to finished caption cues."""
from __future__ import annotations

from .align import Word, align
from .cues import Cue
from .fix import fix
from .standards import Profile
from .text import normalise, sentences, split_into_cues
from .timing import Pacing, Piece, by_duration, by_words


def pieces_from_text(text: str, profile: Profile, headings: tuple[str, ...] = ()) -> list[Piece]:
    """Split narration into caption-sized pieces, remembering sentence starts."""
    heads = {h.strip() for h in headings if h.strip()}
    pieces: list[Piece] = []
    for sentence in sentences(normalise(text)):
        for i, part in enumerate(split_into_cues(sentence, profile.max_chars)):
            pieces.append(Piece(part, new_sentence=(i == 0), heading=part.strip() in heads))
    return pieces


def from_script_and_duration(text: str, duration: float, profile: Profile,
                             headings: tuple[str, ...] = (), pacing: Pacing = Pacing()) -> list[Cue]:
    cues = by_duration(pieces_from_text(text, profile, headings), duration, profile, pacing)
    return fix(cues, profile)[0]


def from_script_and_audio(text: str, heard: list[Word], profile: Profile,
                          headings: tuple[str, ...] = (), duration: float | None = None) -> list[Cue]:
    """YouTube-style auto-sync: the script's words, timed by the audio."""
    pieces = pieces_from_text(text, profile, headings)
    words = [w for p in pieces for w in p.text.split()]
    cues = by_words(pieces, align(words, heard), profile, duration)
    return fix(cues, profile)[0]


def from_audio_only(heard: list[Word], profile: Profile, duration: float | None = None) -> list[Cue]:
    """YouTube-style automatic captions: words and timing both from the audio."""
    if not heard:
        return []
    text = " ".join(w.text for w in heard)
    pieces = pieces_from_text(text, profile)
    piece_words = [w for p in pieces for w in p.text.split()]
    if len(piece_words) != len(heard):  # normalising changed word boundaries; realign
        times = align(piece_words, heard)
    else:
        times = [(w.start, w.end) for w in heard]
    cues = by_words(pieces, times, profile, duration)
    return fix(cues, profile)[0]
