"""The caption cue and timestamp helpers shared by every module."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Cue:
    """One caption on screen: when it appears, when it goes, what it says."""

    start: float
    end: float
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(line.strip() for line in self.lines if line.strip())

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def chars(self) -> int:
        """Characters a viewer reads, excluding line breaks."""
        return len(self.text)

    @property
    def cps(self) -> float:
        """Reading speed in characters per second."""
        return self.chars / self.duration if self.duration > 0 else float("inf")


_TIME = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{1,2})[,.](\d{1,3})$")


def parse_time(value: str) -> float:
    """Parse ``HH:MM:SS,mmm`` (SRT) or ``[HH:]MM:SS.mmm`` (WebVTT) to seconds."""
    match = _TIME.match(value.strip())
    if not match:
        raise ValueError(f"not a timestamp: {value!r}")
    hours, minutes, seconds, millis = match.groups()
    millis = (millis + "00")[:3]
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def format_time(seconds: float, separator: str = ",") -> str:
    """Format seconds as ``HH:MM:SS,mmm`` (or with ``.`` for WebVTT)."""
    total = int(round(max(0.0, seconds) * 1000))
    hours, total = divmod(total, 3_600_000)
    minutes, total = divmod(total, 60_000)
    secs, millis = divmod(total, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"
