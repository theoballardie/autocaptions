"""autocaptions command line."""
from __future__ import annotations

import argparse
import json
import re
import sys
import webbrowser
from pathlib import Path

from . import __version__, build, formats, media, preview, standards
from .fix import fix, shift
from .lint import check, summary
from .text import normalise, replace_dashes
from .transcript import read_paragraphs, sentence_case, split_sections


def _script_text(section, a: argparse.Namespace, fixes: dict[str, str]) -> tuple[str, tuple[str, ...]]:
    """Narration for one section, plus the lines that should be paused like headings."""
    upper = set(a.keep_upper.split(",")) if a.keep_upper else set()
    lines, headings = [], []
    title = section.title.strip()
    if title.isupper():
        title = sentence_case(title, upper)
    if a.speak_headings and title:
        title = title if title.endswith((".", "?", "!", ":")) else title + "."
        lines.append(title)
        headings.append(title)
    for raw in section.lines:
        line = normalise(raw)
        line = fixes.get(line.rstrip(". "), fixes.get(line, line))
        line = re.sub(r"^[-\u2013\u2014\u2022*]\s*", "", line)   # list bullets
        if a.no_dashes:
            line = replace_dashes(line)
        if not line:
            continue
        if a.caps_headings and line.isupper() and any(ch.isalpha() for ch in line):
            line = sentence_case(line, upper)
            if not line.endswith((".", "?", "!", ":")):
                line += "."
            headings.append(line)
        lines.append(line)
    return " ".join(lines), tuple(headings)


def cmd_build(a: argparse.Namespace) -> int:
    profile = standards.get(a.profile)
    sections = split_sections(read_paragraphs(a.script), a.split, a.stop_at, a.skip)
    durations = json.loads(Path(a.durations).read_text()) if a.durations else {}
    fixes = json.loads(Path(a.fixes).read_text()) if a.fixes else {}
    out_dir = Path(a.out_dir) if a.out_dir else None
    if len(sections) > 1 and not out_dir:
        raise SystemExit("this script has several sections; give --out-dir")
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    heard = None
    if a.audio:
        if len(sections) > 1:
            raise SystemExit("--audio aligns one recording to one script; build sections one at a time")
        from .align import transcribe
        heard = transcribe(a.audio, a.model, a.language)

    for section in sections:
        text, headings = _script_text(section, a, fixes)
        if heard is not None:
            cues = build.from_script_and_audio(text, heard, profile, headings, media_duration(a))
            source = "audio"
        else:
            seconds = a.duration or durations.get(section.key) or (media_duration(a) if a.media else None)
            if not seconds:
                raise SystemExit(f"no duration for section {section.key or '(whole script)'}: "
                                 "use --duration, --durations, --media or --audio")
            cues = build.from_script_and_duration(text, float(seconds), profile, headings)
            source = f"{float(seconds):.2f}s"
        target = (out_dir / a.name.format(n=section.key, key=section.key)) if out_dir else Path(a.output)
        formats.write(cues, target)
        s = summary(cues)
        print(f"{target}  {s.get('cues', 0)} cues  timed by {source}  peak {s.get('peak_cps', '-')} chars/s")
    return 0


def media_duration(a: argparse.Namespace) -> float | None:
    source = a.media or a.audio
    return media.duration(source) if source else None


def cmd_transcribe(a: argparse.Namespace) -> int:
    from .align import transcribe
    profile = standards.get(a.profile)
    heard = transcribe(a.audio, a.model, a.language)
    cues = build.from_audio_only(heard, profile, media.duration(a.audio))
    formats.write(cues, a.output)
    print(f"{a.output}  {len(cues)} cues from {len(heard)} recognised words")
    return 0


def cmd_check(a: argparse.Namespace) -> int:
    profile = standards.get(a.profile)
    script = None
    if a.script:
        sections = split_sections(read_paragraphs(a.script), None)
        script = sections[0].body
    worst = 0
    reports = []
    for path in a.captions:
        cues = formats.read(path)
        issues = check(cues, profile, script)
        errors = sum(i.level == "error" for i in issues)
        warnings = len(issues) - errors
        worst = max(worst, 2 if errors else (1 if warnings and a.strict else 0))
        if a.json:
            reports.append({"file": str(path), "summary": summary(cues), "issues": [i.as_dict() for i in issues]})
            continue
        s = summary(cues)
        print(f"{path}: {s.get('cues', 0)} cues, peak {s.get('peak_cps', '-')} chars/s, "
              f"{errors} error(s), {warnings} warning(s) [{profile.name}]")
        for i in issues:
            where = f"cue {i.cue}" if i.cue else "file"
            print(f"  {i.level:7} {where:>8}  {i.code:15} {i.message}")
    if a.json:
        print(json.dumps(reports if len(reports) > 1 else reports[0], indent=2))
    return 1 if worst else 0


def cmd_fix(a: argparse.Namespace) -> int:
    cues, changes = fix(formats.read(a.captions), standards.get(a.profile))
    formats.write(cues, a.output or a.captions)
    print("\n".join(changes) if changes else "nothing to fix")
    return 0


def cmd_convert(a: argparse.Namespace) -> int:
    formats.write(formats.read(a.source), a.target)
    print(f"{a.source} -> {a.target}")
    return 0


def cmd_shift(a: argparse.Namespace) -> int:
    formats.write(shift(formats.read(a.captions), a.seconds), a.output or a.captions)
    print(f"shifted by {a.seconds:+.3f}s")
    return 0


def cmd_preview(a: argparse.Namespace) -> int:
    cues = formats.read(a.captions)
    out = Path(a.output or Path(a.captions).with_suffix(".preview.html"))
    preview.write(cues, standards.get(a.profile), out, a.video)
    print(f"preview: {out}")
    if not a.no_open:
        webbrowser.open(out.resolve().as_uri())
    return 0


def cmd_duration(a: argparse.Namespace) -> int:
    result = {Path(p).stem: round(media.duration(p), 3) for p in a.media}
    print(json.dumps(result, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="autocaptions", description="Build, check and preview SRT and WebVTT captions.")
    p.add_argument("--version", action="version", version=f"autocaptions {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    profiles = list(standards.PROFILES)

    b = sub.add_parser("build", help="captions from a script, timed by duration or by the audio")
    b.add_argument("script", help=".txt, .md or .docx narration script")
    b.add_argument("-o", "--output", default="captions.srt", help="output file (.srt or .vtt)")
    timing = b.add_argument_group("timing (choose one)")
    timing.add_argument("--audio", help="time captions to this recording (YouTube-style auto-sync)")
    timing.add_argument("--duration", type=float, help="running time in seconds")
    timing.add_argument("--media", help="read the running time from this audio or video file")
    timing.add_argument("--durations", help="JSON of {section key: seconds} for a multi-section script")
    sections = b.add_argument_group("multi-video scripts")
    sections.add_argument("--split", help=r'regex for section headings, e.g. "^Chapter (\d+)\s*[-:]\s*(.*)$"')
    sections.add_argument("--out-dir", help="folder for one file per section")
    sections.add_argument("--name", default="{n}.srt", help="file name pattern, {n} is the section key")
    sections.add_argument("--speak-headings", action="store_true", help="headings are read aloud, so caption them")
    sections.add_argument("--keep-upper", help="comma-separated acronyms to keep in capitals when sentence-casing")
    sections.add_argument("--caps-headings", action="store_true",
                          help="ALL CAPS lines are spoken sub-headings: sentence-case them and pause after them")
    sections.add_argument("--stop-at", help="regex: narration ends at the first matching line after the last heading")
    sections.add_argument("--skip", help="regex: drop matching lines (production notes, labels)")
    sections.add_argument("--fixes", help="JSON of exact line replacements, applied before captioning")
    b.add_argument("--profile", choices=profiles, default=standards.DEFAULT_PROFILE)
    b.add_argument("--no-dashes", action="store_true", help="rewrite spaced dashes as commas")
    b.add_argument("--model", default="small.en", help="Whisper model for --audio")
    b.add_argument("--language", help="spoken language code for --audio, e.g. en")
    b.set_defaults(func=cmd_build)

    t = sub.add_parser("transcribe", help="automatic captions from audio alone, like YouTube's auto captions")
    t.add_argument("audio")
    t.add_argument("-o", "--output", default="captions.srt")
    t.add_argument("--profile", choices=profiles, default=standards.DEFAULT_PROFILE)
    t.add_argument("--model", default="small.en")
    t.add_argument("--language")
    t.set_defaults(func=cmd_transcribe)

    c = sub.add_parser("check", help="check captions against a style profile (and optionally the script)")
    c.add_argument("captions", nargs="+")
    c.add_argument("--profile", choices=profiles, default=standards.DEFAULT_PROFILE)
    c.add_argument("--script", help="fail if the captions do not reproduce this script word for word")
    c.add_argument("--strict", action="store_true", help="treat warnings as failures")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_check)

    f = sub.add_parser("fix", help="repair overlaps, gaps, short cues and long lines")
    f.add_argument("captions")
    f.add_argument("-o", "--output", help="write here instead of in place")
    f.add_argument("--profile", choices=profiles, default=standards.DEFAULT_PROFILE)
    f.set_defaults(func=cmd_fix)

    v = sub.add_parser("convert", help="convert between SRT and WebVTT")
    v.add_argument("source")
    v.add_argument("target")
    v.set_defaults(func=cmd_convert)

    s = sub.add_parser("shift", help="move every cue earlier or later")
    s.add_argument("captions")
    s.add_argument("seconds", type=float)
    s.add_argument("-o", "--output")
    s.set_defaults(func=cmd_shift)

    w = sub.add_parser("preview", help="open the captions over the video in a browser")
    w.add_argument("captions")
    w.add_argument("--video", help="video or audio to play underneath")
    w.add_argument("-o", "--output", help="HTML file to write")
    w.add_argument("--profile", choices=profiles, default=standards.DEFAULT_PROFILE)
    w.add_argument("--no-open", action="store_true")
    w.set_defaults(func=cmd_preview)

    d = sub.add_parser("duration", help="print the running time of media files as JSON")
    d.add_argument("media", nargs="+")
    d.set_defaults(func=cmd_duration)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
