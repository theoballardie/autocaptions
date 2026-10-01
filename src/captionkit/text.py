"""Turning prose into caption-sized pieces with natural line breaks.

Line breaks follow the rules human captioners use: break after punctuation or
before a conjunction, preposition or relative clause, and never between an
article and its noun ("the / report") or straight after a preposition.
"""
from __future__ import annotations

import re

ARTICLES = {"a", "an", "the"}
PREPOSITIONS = {
    "of", "in", "on", "at", "to", "for", "with", "from", "by", "as", "into", "under", "over",
    "about", "between", "through", "during", "against", "within", "without", "upon", "across", "per",
}
CONJUNCTIONS = {"and", "but", "or", "so", "yet", "nor"}
SUBORDINATORS = {
    "which", "that", "because", "if", "when", "while", "although", "though", "whether",
    "since", "unless", "after", "before", "where", "who", "whose",
}
ABBREVIATIONS = {"e.g", "i.e", "etc", "dr", "mr", "mrs", "ms", "ltd", "no", "vs", "approx", "st"}

_SMART = {"‘": "'", "’": "'", "“": '"', "”": '"', "…": "...",
          " ": " ", "​": "", "﻿": ""}


def normalise(text: str, plain_quotes: bool = True) -> str:
    """Collapse whitespace and, optionally, replace typographic quotes."""
    if plain_quotes:
        for smart, plain in _SMART.items():
            text = text.replace(smart, plain)
    return re.sub(r"\s+", " ", text).strip()


def replace_dashes(text: str) -> str:
    """Rewrite spaced en/em dashes as commas, for styles that avoid dashes."""
    text = re.sub(r"\s+[–—]\s+", ", ", text)
    return text.replace("—", ", ").replace("–", "-")


def sentences(text: str) -> list[str]:
    """Split text into sentences without breaking on abbreviations or initials."""
    out, buffer, tokens = [], "", text.split(" ")
    for i, token in enumerate(tokens):
        buffer = (buffer + " " + token).strip()
        if not re.search(r"[.!?][\"')\]]?$", token):
            continue
        stem = re.sub(r"[\"')\]]", "", token)[:-1].lower()
        if stem in ABBREVIATIONS or re.fullmatch(r"[0-9]|[a-zA-Z]", stem):
            continue
        following = tokens[i + 1] if i + 1 < len(tokens) else ""
        if following and not (following[0].isupper() or following[0] in "\"'("):
            continue
        out.append(buffer)
        buffer = ""
    if buffer.strip():
        out.append(buffer.strip())
    return out


def break_score(words: list[str], k: int) -> float:
    """How good a break is between ``words[k-1]`` and ``words[k]``. Higher is better."""
    if k <= 0 or k >= len(words):
        return -1e9
    before, after = words[k - 1], words[k]
    b = before.lower().strip(".,;:!?()\"'")
    a = after.lower().strip(".,;:!?()\"'")
    score = 0.0
    if before.endswith((",", ";", ":")):
        score += 60
    elif before.endswith((".", "!", "?")):
        score += 80
    if a in CONJUNCTIONS:
        score += 34
    elif a in SUBORDINATORS:
        score += 26
    elif a in PREPOSITIONS:
        score += 16
    elif a in ARTICLES:
        score += 8
    if b in ARTICLES:
        score -= 100
    if b in PREPOSITIONS:
        score -= 55
    if b in CONJUNCTIONS:
        score -= 45
    if before.endswith("("):
        score -= 120
    if after.startswith(")"):
        score -= 120
    if re.fullmatch(r"\(?\d{4}\)?[.,)]?", after):  # keep "Act 1998" together
        score -= 70
    return score


# A break scoring below this leaves a line ending on "the", "of", "and" and so on.
BAD_BREAK = -40


def layout(text: str, max_chars: int = 42, strict: bool = True) -> list[str] | None:
    """Lay text out as one or two balanced lines, or None if it cannot fit.

    With ``strict`` (the default) a layout whose only possible break would
    strand an article, preposition or conjunction at a line end counts as not
    fitting, so callers split the text into two cues instead.
    """
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    candidates = [
        k for k in range(1, len(words))
        if len(" ".join(words[:k])) <= max_chars and len(" ".join(words[k:])) <= max_chars
    ]
    if not candidates:
        return None
    best, best_k = -1e9, candidates[0]
    for k in candidates:
        top, bottom = len(" ".join(words[:k])), len(" ".join(words[k:]))
        score = break_score(words, k) - abs(top - bottom) * 0.55
        if min(top, bottom) < 12:  # no stranded one-word line
            score -= 30
        if score > best:
            best, best_k = score, k
    if strict and break_score(words, best_k) < BAD_BREAK:
        return None
    return [" ".join(words[:best_k]), " ".join(words[best_k:])]


def split_into_cues(sentence: str, max_chars: int = 42) -> list[str]:
    """Split one sentence into cue-sized pieces at the best available breaks."""

    def split(words: list[str]) -> list[list[str]]:
        if layout(" ".join(words), max_chars) is not None:
            return [words]
        fits = [k for k in range(1, len(words)) if layout(" ".join(words[:k]), max_chars) is not None] or [1]
        longest = max(fits)
        best, best_k = -1e9, longest
        for k in fits:
            if k < longest * 0.55:  # keep cues from fragmenting
                continue
            score = break_score(words, k) + k * 1.2
            if score > best:
                best, best_k = score, k
        return [words[:best_k]] + split(words[best_k:])

    return [" ".join(part) for part in split(sentence.split())]


def tokens(text: str) -> list[str]:
    """Words for comparison: lower case, punctuation stripped."""
    return [t for t in re.sub(r"[^\w'\s-]", " ", text.lower()).replace("-", " ").split() if t]
