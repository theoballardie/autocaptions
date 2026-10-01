"""Read and write SRT and WebVTT."""
from __future__ import annotations

import re
from pathlib import Path

from .cues import Cue, format_time, parse_time

_ARROW = re.compile(r"^\s*(\S+)\s*-->\s*(\S+)(.*)$")


def _blocks(text: str) -> list[list[str]]:
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    return [block.split("\n") for block in re.split(r"\n\s*\n", text.strip()) if block.strip()]


def parse_srt(text: str) -> list[Cue]:
    cues: list[Cue] = []
    for number, block in enumerate(_blocks(text), 1):
        lines = list(block)
        if lines and lines[0].strip().isdigit():
            lines = lines[1:]
        if not lines or "-->" not in lines[0]:
            raise ValueError(f"SRT block {number} has no timing line: {block[:2]!r}")
        match = _ARROW.match(lines[0])
        if not match:
            raise ValueError(f"SRT block {number} has a malformed timing line: {lines[0]!r}")
        cues.append(Cue(parse_time(match.group(1)), parse_time(match.group(2)), [l.rstrip() for l in lines[1:]]))
    return cues


def parse_vtt(text: str) -> list[Cue]:
    blocks = _blocks(text)
    if not blocks or not blocks[0][0].startswith("WEBVTT"):
        raise ValueError("WebVTT files must start with 'WEBVTT'")
    cues: list[Cue] = []
    for block in blocks[1:]:
        if block[0].startswith(("NOTE", "STYLE", "REGION")):
            continue
        lines = list(block)
        if "-->" not in lines[0]:
            lines = lines[1:]  # cue identifier
        if not lines:
            continue
        match = _ARROW.match(lines[0])
        if not match:
            raise ValueError(f"malformed WebVTT timing line: {lines[0]!r}")
        cues.append(Cue(parse_time(match.group(1)), parse_time(match.group(2)), [l.rstrip() for l in lines[1:]]))
    return cues


def to_srt(cues: list[Cue]) -> str:
    blocks = [
        f"{i}\n{format_time(c.start)} --> {format_time(c.end)}\n" + "\n".join(c.lines)
        for i, c in enumerate(cues, 1)
    ]
    return "\n\n".join(blocks) + "\n"


def to_vtt(cues: list[Cue]) -> str:
    blocks = [
        f"{format_time(c.start, '.')} --> {format_time(c.end, '.')}\n" + "\n".join(c.lines)
        for c in cues
    ]
    return "WEBVTT\n\n" + "\n\n".join(blocks) + "\n"


def read(path: str | Path) -> list[Cue]:
    text = Path(path).read_text(encoding="utf-8-sig")
    if Path(path).suffix.lower() == ".vtt" or text.lstrip().startswith("WEBVTT"):
        return parse_vtt(text)
    return parse_srt(text)


def write(cues: list[Cue], path: str | Path) -> None:
    path = Path(path)
    content = to_vtt(cues) if path.suffix.lower() == ".vtt" else to_srt(cues)
    path.write_text(content, encoding="utf-8")
