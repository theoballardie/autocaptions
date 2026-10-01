import json
import zipfile

from autocaptions import formats
from autocaptions.cli import main
from autocaptions.transcript import read_paragraphs, split_sections

SCRIPT = ("Welcome to this short guide. In the next few minutes you will learn how to set up a project, "
          "who to invite, and what happens next.")


def test_build_then_check_against_the_script(tmp_path, capsys):
    script = tmp_path / "script.txt"
    script.write_text(SCRIPT)
    out = tmp_path / "out.srt"
    assert main(["build", str(script), "--duration", "12", "-o", str(out)]) == 0
    assert main(["check", str(out), "--script", str(script)]) == 0
    assert "0 error(s)" in capsys.readouterr().out


def test_check_fails_on_a_reworded_caption(tmp_path):
    script = tmp_path / "script.txt"
    script.write_text(SCRIPT)
    out = tmp_path / "out.srt"
    main(["build", str(script), "--duration", "12", "-o", str(out)])
    out.write_text(out.read_text().replace("project", "workspace"))
    assert main(["check", str(out), "--script", str(script)]) == 1


def test_multi_section_script_with_durations(tmp_path):
    script = tmp_path / "course.md"
    script.write_text("# Chapter 1 - GETTING STARTED\n\nWelcome aboard.\n\n# Chapter 2 - NEXT STEPS\n\nInvite your team.\n")
    durations = tmp_path / "durations.json"
    durations.write_text(json.dumps({"1": 4.0, "2": 5.0}))
    out_dir = tmp_path / "srt"
    assert main(["build", str(script), "--split", r"^Chapter (\d+)\s*-\s*(.*)$", "--durations", str(durations),
                 "--out-dir", str(out_dir), "--name", "part{n}.vtt", "--speak-headings"]) == 0
    first = formats.read(out_dir / "part1.vtt")
    assert first[0].text.startswith("Getting started.")
    assert formats.read(out_dir / "part2.vtt")[-1].end <= 5.0


def test_convert_shift_and_preview(tmp_path):
    script = tmp_path / "s.txt"
    script.write_text(SCRIPT)
    srt = tmp_path / "a.srt"
    main(["build", str(script), "--duration", "12", "-o", str(srt)])
    vtt = tmp_path / "a.vtt"
    assert main(["convert", str(srt), str(vtt)]) == 0 and vtt.read_text().startswith("WEBVTT")
    before = formats.read(srt)[0].start
    assert main(["shift", str(srt), "0.5"]) == 0
    assert abs(formats.read(srt)[0].start - (before + 0.5)) < 1e-6
    html = tmp_path / "p.html"
    assert main(["preview", str(srt), "-o", str(html), "--no-open"]) == 0
    page = html.read_text()
    assert "const DATA = {" in page and "Welcome to this short guide." in page and "font-family: Manrope" in page


def test_docx_scripts_are_read(tmp_path):
    body = ('<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
            '<w:p><w:r><w:t>Chapter 1 - HELLO</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>First line.</w:t></w:r></w:p></w:body></w:document>')
    path = tmp_path / "s.docx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", body)
    sections = split_sections(read_paragraphs(path), r"^Chapter (\d+) - (.*)$")
    assert [(s.key, s.title, s.body) for s in sections] == [("1", "HELLO", "First line.")]
