"""Checking caption files against a style profile and, optionally, the script."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .cues import Cue, format_time
from .standards import Profile
from .text import tokens

# Caption files store milliseconds, so allow half a millisecond of rounding.
TOL = 0.0005


@dataclass
class Issue:
    level: str        # "error" or "warning"
    cue: int          # 1-based cue number, 0 for file-level issues
    code: str
    message: str

    def as_dict(self) -> dict:
        return asdict(self)


def check(cues: list[Cue], profile: Profile, script: str | None = None) -> list[Issue]:
    issues: list[Issue] = []

    def add(level: str, n: int, code: str, message: str) -> None:
        issues.append(Issue(level, n, code, message))

    if not cues:
        add("error", 0, "empty-file", "the file has no cues")
        return issues

    for n, cue in enumerate(cues, 1):
        at = format_time(cue.start)
        if not cue.text:
            add("error", n, "empty-cue", f"cue at {at} has no text")
        if cue.end <= cue.start:
            add("error", n, "bad-timing", f"cue at {at} ends before it starts")
            continue
        if len(cue.lines) > profile.max_lines:
            add("error", n, "too-many-lines", f"{len(cue.lines)} lines (max {profile.max_lines})")
        for line in cue.lines:
            if len(line) > profile.max_chars:
                add("error", n, "line-too-long", f"{len(line)} characters (max {profile.max_chars}): {line!r}")
        if cue.duration < profile.min_duration - TOL:
            add("warning", n, "too-short", f"on screen {cue.duration:.2f}s (min {profile.min_duration:.2f}s)")
        if cue.duration > profile.max_duration + TOL:
            add("warning", n, "too-long", f"on screen {cue.duration:.2f}s (max {profile.max_duration:.1f}s)")
        if cue.cps > profile.max_cps + 0.05:
            add("warning", n, "reading-speed", f"{cue.cps:.1f} characters per second (max {profile.max_cps:g})")
        if n > 1:
            previous = cues[n - 2]
            if cue.start < previous.start:
                add("error", n, "out-of-order", f"starts before cue {n - 1}")
            elif cue.start < previous.end - TOL:
                add("error", n, "overlap", f"overlaps cue {n - 1} by {previous.end - cue.start:.3f}s")
            elif cue.start - previous.end < profile.min_gap - TOL and cue.start > previous.end:
                add("warning", n, "small-gap", f"{(cue.start - previous.end) * 1000:.0f}ms after cue {n - 1} "
                                              f"(min {profile.min_gap * 1000:.0f}ms)")

    if script is not None:
        issue = compare_to_script(cues, script)
        if issue:
            issues.append(issue)
    return issues


def compare_to_script(cues: list[Cue], script: str) -> Issue | None:
    """Report the first place the captions stop matching the script word for word."""
    said = tokens(" ".join(c.text for c in cues))
    expected = tokens(script)
    for i, (a, b) in enumerate(zip(said, expected)):
        if a != b:
            context = " ".join(expected[max(0, i - 4): i + 5])
            return Issue("error", 0, "script-mismatch", f"word {i + 1}: captions say {a!r}, script says {b!r} (…{context}…)")
    if len(said) != len(expected):
        return Issue("error", 0, "script-mismatch",
                     f"captions have {len(said)} words, the script has {len(expected)}")
    return None


def summary(cues: list[Cue]) -> dict:
    if not cues:
        return {"cues": 0}
    return {
        "cues": len(cues),
        "first": format_time(cues[0].start),
        "last": format_time(cues[-1].end),
        "peak_cps": round(max(c.cps for c in cues if c.duration > 0), 1),
        "mean_cps": round(sum(c.chars for c in cues) / max(sum(c.duration for c in cues), 1e-9), 1),
    }
