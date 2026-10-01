"""Reading narration scripts and splitting them into one section per video."""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass
class Section:
    key: str                                   # e.g. "1" for "Chapter 1"; "" for a single video
    title: str                                 # heading text, if any
    lines: list[str] = field(default_factory=list)  # narration, one entry per script line

    @property
    def body(self) -> str:
        return " ".join(self.lines)


def _docx_paragraphs(path: Path) -> list[str]:
    root = ElementTree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    paragraphs = []
    for p in root.iter(_W + "p"):
        parts = []
        for node in p.iter():
            if node.tag == _W + "t":
                parts.append(node.text or "")
            elif node.tag == _W + "tab":
                parts.append(" ")
            elif node.tag == _W + "br":
                parts.append("\n")
        paragraphs.append("".join(parts))
    return paragraphs


def read_paragraphs(path: str | Path) -> list[str]:
    """Paragraphs of a .txt, .md or .docx script."""
    path = Path(path)
    if path.suffix.lower() == ".docx":
        return _docx_paragraphs(path)
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".md":
        text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)          # heading markers
        text = re.sub(r"[*_`]{1,3}([^*_`]+)[*_`]{1,3}", r"\1", text)  # emphasis
    return re.split(r"\n\s*\n|\n", text)


def sentence_case(text: str, keep_upper: set[str] = frozenset()) -> str:
    """Convert an ALL CAPS heading to sentence case, keeping listed acronyms."""
    words = text.lower().split()
    out = []
    for i, word in enumerate(words):
        bare = re.sub(r"[^\w]", "", word).upper()
        out.append(word.upper() if bare in keep_upper else (word.capitalize() if i == 0 else word))
    return " ".join(out)


def split_sections(paragraphs: list[str], pattern: str | None, stop_at: str | None = None,
                   skip: str | None = None) -> list[Section]:
    """Split a script at headings matching ``pattern``.

    The pattern's first group is the section key (e.g. the chapter number) and
    an optional second group is the title. With no pattern the whole script is
    one section. ``stop_at`` ends the narration at the first matching line
    after the last heading (a quiz, an appendix); ``skip`` drops matching
    lines anywhere (production notes, on-screen labels).
    """
    heading = re.compile(pattern) if pattern else None
    stop = re.compile(stop_at) if stop_at else None
    drop = re.compile(skip) if skip else None
    lines = [line.strip() for p in paragraphs for line in p.split("\n") if line.strip()]

    if heading is None:
        kept = []
        for line in lines:
            if stop and stop.match(line):
                break
            if not (drop and drop.match(line)):
                kept.append(line)
        return [Section("", "", kept)]

    heads = [i for i, line in enumerate(lines) if heading.match(line)]
    if not heads:
        raise SystemExit(f"no headings matched {pattern!r}")
    sections: list[Section] = []
    for i, line in enumerate(lines):
        match = heading.match(line)
        if match:
            title = (match.group(2) if heading.groups > 1 else "") or ""
            sections.append(Section(match.group(1), title.strip(), []))
        elif sections:
            if stop and i > heads[-1] and stop.match(line):
                break
            if not (drop and drop.match(line)):
                sections[-1].lines.append(line)
    return sections
