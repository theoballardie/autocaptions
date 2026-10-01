import pytest

from autocaptions import build
from autocaptions.align import Word, align
from autocaptions.lint import check
from autocaptions.standards import get

SCRIPT = ("Welcome to this short guide. In the next few minutes you will learn how to set up a project, "
          "who to invite, and what happens next. Most people are up and running in under ten minutes.")


def test_duration_timing_fills_the_video_without_overlaps():
    profile = get("broadcast")
    cues = build.from_script_and_duration(SCRIPT, 18.0, profile)
    assert cues[0].start >= 0 and cues[-1].end <= 18.0
    assert all(b.start >= a.end for a, b in zip(cues, cues[1:]))
    assert not [i for i in check(cues, profile, SCRIPT) if i.level == "error"]


def test_align_exact_words():
    heard = [Word("hello", 0.0, 0.4), Word("world", 0.5, 0.9)]
    assert align(["Hello", "world."], heard) == [(0.0, 0.4), (0.5, 0.9)]


def test_align_misheard_and_missing_words_keep_order():
    script = ["The", "northern", "lights", "observatory", "opens", "at", "dusk"]
    heard = [Word("the", 0.0, 0.2), Word("northern", 0.3, 0.6), Word("light", 0.7, 1.1),
             Word("opens", 1.9, 2.3), Word("at", 2.4, 2.6), Word("dusk", 2.7, 3.0)]
    times = align(script, heard)
    assert len(times) == len(script)
    starts = [t[0] for t in times]
    assert starts == sorted(starts)
    assert times[4] == (1.9, 2.3) and times[6] == (2.7, 3.0)
    assert 0.7 <= times[3][0] <= 1.9  # "observatory", never heard, sits between its neighbours


def test_audio_sync_follows_word_times():
    profile = get("broadcast")
    words = SCRIPT.split()
    heard = [Word(w, i * 0.4, i * 0.4 + 0.3) for i, w in enumerate(words)]
    cues = build.from_script_and_audio(SCRIPT, heard, profile)
    assert cues[0].start == pytest.approx(0.0)
    assert " ".join(c.text for c in cues) == SCRIPT
    assert all(b.start >= a.end for a, b in zip(cues, cues[1:]))


def test_audio_only_builds_from_recognised_words():
    profile = get("broadcast")
    heard = [Word(w, i * 0.35, i * 0.35 + 0.3) for i, w in enumerate(SCRIPT.split())]
    cues = build.from_audio_only(heard, profile)
    assert " ".join(c.text for c in cues) == SCRIPT
