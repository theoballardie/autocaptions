from autocaptions.cues import Cue
from autocaptions.fix import fix, shift
from autocaptions.lint import check, compare_to_script
from autocaptions.standards import get

P = get("broadcast")


def codes(cues, script=None):
    return {i.code for i in check(cues, P, script)}


def test_clean_file_has_no_issues():
    assert codes([Cue(0, 2.5, ["A short, readable line."]), Cue(2.7, 5, ["And another one."])]) == set()


def test_finds_the_common_faults():
    found = codes([
        Cue(0, 3, ["x" * 50]),                                 # line too long
        Cue(2.5, 3.0, ["Overlapping and far too fast to read"]),  # overlap, too short, too fast
        Cue(3.02, 4.5, ["Tight gap."]),                        # small gap
        Cue(5, 4, ["Backwards."]),                             # bad timing
    ])
    assert {"line-too-long", "overlap", "too-short", "reading-speed", "small-gap", "bad-timing"} <= found


def test_script_mismatch_names_the_word():
    issue = compare_to_script([Cue(0, 2, ["The cat sat"])], "The dog sat")
    assert issue and "'cat'" in issue.message and "'dog'" in issue.message


def test_fix_removes_overlaps_and_extends_short_cues():
    cues = [Cue(0, 2.5, ["First cue here."]), Cue(2.0, 2.3, ["Next."]), Cue(5.0, 6.0, ["Later."])]
    fixed, changes = fix(cues, P)
    assert fixed[0].end <= fixed[1].start - P.min_gap + 1e-9
    assert fixed[1].duration >= P.min_duration - 1e-9
    assert changes
    assert not [i for i in check(fixed, P) if i.code in {"overlap", "small-gap"}]


def test_fix_reflows_long_lines_without_changing_words():
    cue = Cue(0, 4, ["Employers must report the incident to the regulator within ten days"])
    fixed, _ = fix([cue], P)
    assert fixed[0].text == cue.text and len(fixed[0].lines) == 2


def test_shift_moves_and_clamps():
    moved = shift([Cue(0.2, 1.0, ["a"]), Cue(2.0, 3.0, ["b"])], -0.5)
    assert (moved[0].start, moved[1].start) == (0.0, 1.5)
