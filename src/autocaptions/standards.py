"""Caption style profiles: the limits a caption file is built to and checked against."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    name: str
    max_chars: int          # characters per line
    max_lines: int          # lines per cue
    max_cps: float          # reading speed, characters per second
    min_duration: float     # seconds a cue stays up, at least
    max_duration: float     # seconds a cue stays up, at most
    min_gap: float          # seconds between consecutive cues
    description: str = ""


PROFILES: dict[str, Profile] = {
    "broadcast": Profile(
        "broadcast", 42, 2, 17.0, 5 / 6, 7.0, 2 / 24,
        "Common streaming and broadcast practice: 42 characters, two lines, 17 "
        "characters per second, at least 5/6 of a second on screen, a 2 frame gap.",
    ),
    "bbc": Profile(
        "bbc", 37, 2, 15.0, 1.0, 7.0, 2 / 25,
        "Closer to UK broadcast guidance: 37 characters per line and a slower "
        "reading rate (160 to 180 words per minute, about 15 characters per second).",
    ),
    "relaxed": Profile(
        "relaxed", 42, 2, 21.0, 0.7, 8.0, 0.04,
        "Looser limits for internal or fast-paced content.",
    ),
}

DEFAULT_PROFILE = "broadcast"


def get(name: str) -> Profile:
    try:
        return PROFILES[name]
    except KeyError:
        raise SystemExit(f"unknown profile {name!r}; choose from {', '.join(PROFILES)}") from None
