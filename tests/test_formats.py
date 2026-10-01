import pytest

from autocaptions.cues import Cue, format_time, parse_time
from autocaptions.formats import parse_srt, parse_vtt, to_srt, to_vtt


def test_timestamps_round_trip():
    assert parse_time("01:02:03,456") == pytest.approx(3723.456)
    assert parse_time("02:03.4") == pytest.approx(123.4)
    assert format_time(3723.456) == "01:02:03,456"
    assert format_time(1.5, ".") == "00:00:01.500"


def test_srt_round_trip():
    cues = [Cue(0.5, 2.0, ["Hello there,", "and welcome."]), Cue(2.2, 4.0, ["Second cue."])]
    again = parse_srt(to_srt(cues))
    assert [(c.start, c.end, c.lines) for c in again] == [(c.start, c.end, c.lines) for c in cues]


def test_srt_tolerates_bom_crlf_and_missing_numbers():
    text = "﻿1\r\n00:00:01,000 --> 00:00:02,000\r\nOne\r\n\r\n00:00:03,000 --> 00:00:04,000\r\nTwo\r\n"
    cues = parse_srt(text)
    assert [c.text for c in cues] == ["One", "Two"]


def test_vtt_skips_notes_ids_and_settings():
    text = ("WEBVTT\n\nNOTE written by hand\n\nintro\n00:01.000 --> 00:02.500 align:start\nHi\n\n"
            "00:00:03.000 --> 00:00:04.000\nBye\n")
    cues = parse_vtt(text)
    assert [(c.start, c.end, c.text) for c in cues] == [(1.0, 2.5, "Hi"), (3.0, 4.0, "Bye")]
    assert to_vtt(cues).startswith("WEBVTT\n\n00:00:01.000 --> 00:00:02.500\nHi")


def test_bad_files_raise():
    with pytest.raises(ValueError):
        parse_srt("1\nnot a timing line\ntext\n")
    with pytest.raises(ValueError):
        parse_vtt("00:00:01.000 --> 00:00:02.000\nNo header\n")
