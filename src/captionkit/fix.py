"""Repairing the faults a checker finds most often, without touching the words."""
from __future__ import annotations

import math

from .cues import Cue, format_time
from .standards import Profile
from .text import layout


def fix(cues: list[Cue], profile: Profile) -> tuple[list[Cue], list[str]]:
    """Return repaired cues and a list of what changed.

    In order: drop empty cues, sort, reflow lines that break the line rules,
    remove overlaps and enforce the minimum gap (by pulling the earlier cue's
    end back), then extend short cues into free time up to the minimum
    duration. Wording is never changed.
    """
    changes: list[str] = []
    out = [Cue(c.start, c.end, list(c.lines)) for c in cues if c.text]
    if len(out) != len(cues):
        changes.append(f"removed {len(cues) - len(out)} empty cue(s)")
    if any(out[i].start > out[i + 1].start for i in range(len(out) - 1)):
        out.sort(key=lambda c: c.start)
        changes.append("sorted cues by start time")

    for n, cue in enumerate(out, 1):
        if len(cue.lines) > profile.max_lines or any(len(l) > profile.max_chars for l in cue.lines):
            lines = layout(cue.text, profile.max_chars) or layout(cue.text, profile.max_chars, strict=False)
            if lines:
                cue.lines = lines
                changes.append(f"cue {n}: reflowed to {len(lines)} line(s)")
            else:
                changes.append(f"cue {n}: too much text to fit {profile.max_lines} lines; split it by hand")
        if cue.end <= cue.start:
            cue.end = cue.start + profile.min_duration
            changes.append(f"cue {n}: end moved after start")

    for n in range(len(out) - 1):
        cue, following = out[n], out[n + 1]
        # round down to the millisecond so the gap survives being written to file
        latest_end = math.floor((following.start - profile.min_gap) * 1000 + 1e-6) / 1000
        if cue.end > latest_end:
            new_end = max(cue.start + 0.1, latest_end)
            if abs(new_end - cue.end) > 1e-6:
                changes.append(f"cue {n + 1}: end {format_time(cue.end)} -> {format_time(new_end)} (overlap or gap)")
                cue.end = new_end

    for n, cue in enumerate(out):
        if cue.duration < profile.min_duration:
            limit = (math.floor((out[n + 1].start - profile.min_gap) * 1000 + 1e-6) / 1000
                     if n + 1 < len(out) else cue.start + profile.min_duration)
            new_end = min(cue.start + profile.min_duration, limit)
            if new_end > cue.end + 1e-6:
                changes.append(f"cue {n + 1}: extended to {new_end - cue.start:.2f}s on screen")
                cue.end = new_end
    return out, changes


def shift(cues: list[Cue], seconds: float) -> list[Cue]:
    """Move every cue by ``seconds`` (negative moves earlier), clamped at zero."""
    return [Cue(max(0.0, c.start + seconds), max(0.0, c.end + seconds), list(c.lines)) for c in cues]
