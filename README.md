# captionkit

Build, check and preview SRT and WebVTT captions, from a script or straight from the audio.

captionkit turns a narration script into captions that read well, follow the voice and pass broadcast-style checks. It covers both of the jobs video platforms do with sound:

- **Auto-sync:** you supply the exact script and the recording, and every word is lined up with the moment it is spoken. The wording stays exactly as approved, and only the timing comes from the audio.
- **Automatic captions:** with no script, speech recognition writes the words and times them.

Both run locally with [Whisper](https://github.com/openai/whisper), through [faster-whisper](https://github.com/SYSTRAN/faster-whisper). No audio leaves the machine.

## Features

- **Readable line breaks.** Lines break after punctuation or before "and", "which" and "because", and never between "the" and its noun or straight after a preposition. Lines are balanced, and long sentences become several captions.
- **Three ways to time.** To the audio (`--audio`), across a known running time (`--duration`, `--media`), or per video from a JSON of durations for a script that covers several videos.
- **Checks.** Line length, lines per caption, reading speed, minimum and maximum time on screen, gaps and overlaps. Optionally, it confirms the captions reproduce the script word for word, so a caption can never quietly reword an approved script.
- **Fixes.** Repairs overlaps, gaps that are too small, captions that are too short and lines that are too long, without changing a word.
- **Preview.** A single HTML page that plays the video with the captions over it, colours a timeline by problem, lists every caption with its reading speed, lets you nudge the timing in 0.1 second steps and downloads the corrected file. Drag any video and caption file onto it, or open it with `captionkit preview`.
- **Scripts in plain text, Markdown or Word (.docx).** A script that covers several videos can be split at headings such as `Chapter 3 - Sharing your work`, with options to skip stage directions and stop before an appendix.
- **SRT and WebVTT,** read and written, with conversion and time shifting.

## Install

```bash
git clone https://github.com/theoballardie/captionkit.git
cd captionkit
pip install -e .              # build, check, fix, convert, shift, preview
pip install -e ".[audio]"     # adds speech recognition for --audio and transcribe
```

Python 3.10 or later. The audio extra downloads a Whisper model the first time it runs (`small.en` by default, about 460 MB).

## Quick start

```bash
# captions timed to the recording (auto-sync)
captionkit build script.docx --audio narration.mp4 -o narration.srt

# captions from the audio alone (automatic captions)
captionkit transcribe narration.mp4 -o narration.srt

# no audio to hand: spread the script across the running time
captionkit build script.txt --media narration.mp4 -o narration.srt

# check against the style and the script, then open the preview
captionkit check narration.srt --script script.docx
captionkit preview narration.srt --video narration.mp4
```

### A script that covers several videos

```bash
captionkit build series.docx \
  --split '^Chapter (\d+)\s*-\s*(.*)$' \
  --durations durations.json \
  --out-dir captions --name 'chapter{n}.srt' \
  --caps-headings --skip '^\[.*\]$' --stop-at '^Appendix'
```

Each heading starts a new video, and `{n}` is the number it captures. `durations.json` maps those numbers to seconds, and `captionkit duration *.mp4` prints one for you.

## Style profiles

| Profile | Characters per line | Lines | Reading speed | On screen | Gap |
|---|---|---|---|---|---|
| `broadcast` (default) | 42 | 2 | 17 characters/s | 0.83 to 7 s | 2 frames |
| `bbc` | 37 | 2 | 15 characters/s | 1 to 7 s | 2 frames |
| `relaxed` | 42 | 2 | 21 characters/s | 0.7 to 8 s | 40 ms |

`broadcast` follows common streaming guidance: 42 characters, two lines, 17 characters per second and five sixths of a second minimum. `bbc` follows the slower UK broadcast rate of 160 to 180 words per minute.

## Commands

| Command | Does |
|---|---|
| `build` | Captions from a script, timed by audio, duration or a durations file |
| `transcribe` | Captions from audio alone |
| `check` | Reports problems; exits 1 on errors (or on warnings with `--strict`); `--json` for CI |
| `fix` | Repairs timing and layout faults in place, or to `-o` |
| `convert` | SRT to WebVTT and back |
| `shift` | Moves every caption by a number of seconds |
| `preview` | Writes and opens the browser preview |
| `duration` | Prints the running time of media files as JSON |

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Credits

Written by Theo Ballardie. The preview page uses [Manrope](https://github.com/googlefonts/manrope) by The Manrope Project Authors, under the SIL Open Font License 1.1 (see `src/captionkit/fonts/OFL.txt`).

## Licence

MIT. See [LICENSE](LICENSE).
