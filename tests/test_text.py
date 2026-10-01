from captionkit.text import layout, normalise, replace_dashes, sentences, split_into_cues, tokens


def test_sentences_ignore_abbreviations_and_initials():
    text = "Speak to Mr. Jones, e.g. by email. He replies within 2 days. Ask J. Smith."
    assert sentences(text) == ["Speak to Mr. Jones, e.g. by email.", "He replies within 2 days.", "Ask J. Smith."]


STRANDED = {"the", "a", "an", "to", "of", "and", "in", "for", "with"}


def test_layout_breaks_after_punctuation():
    lines = layout("Pack your bags the night before, or as early as you can", 42)
    assert lines == ["Pack your bags the night before,", "or as early as you can"]


def test_layout_refuses_a_break_that_strands_an_article():
    sentence = "Visitors should collect the map from the front desk before walking up to the castle"
    assert layout(sentence, 42) is None                        # the only fit ends a line on "the"
    assert layout(sentence, 42, strict=False) is not None      # still available as a last resort
    for piece in split_into_cues(sentence, 42):                # so it becomes two cues instead
        for line in layout(piece, 42):
            assert line.split()[-1].lower() not in STRANDED


def test_layout_returns_none_when_too_long():
    assert layout("word " * 40, 42) is None


def test_split_into_cues_fits_every_piece():
    sentence = ("If you are planning a trip somewhere new, it helps to check the weather, "
                "book your travel early, and make a list of everything you need, "
                "so that nothing important is left behind at the last minute.")
    pieces = split_into_cues(sentence, 42)
    assert " ".join(pieces) == sentence
    assert all(layout(p, 42) is not None for p in pieces)


def test_normalise_and_dashes():
    assert normalise("“Hello”  ‘you’…") == "\"Hello\" 'you'..."
    assert replace_dashes("Report it – today") == "Report it, today"


def test_tokens_ignore_case_and_punctuation():
    assert tokens("Don't stop, it's GDPR-compliant!") == ["don't", "stop", "it's", "gdpr", "compliant"]
