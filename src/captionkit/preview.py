"""A self-contained HTML page for checking captions against the video in a browser."""
from __future__ import annotations

import base64
import json
import os
from importlib import resources
from pathlib import Path
from urllib.parse import quote

from .cues import Cue
from .standards import PROFILES, Profile


def render(cues: list[Cue], profile: Profile, video_url: str = "", title: str = "Caption preview") -> str:
    data = {
        "title": title,
        "video": video_url,
        "profile": profile.name,
        "profiles": {k: vars(p) for k, p in PROFILES.items()},
        "cues": [{"start": c.start, "end": c.end, "lines": c.lines} for c in cues],
    }
    return (TEMPLATE.replace("/*__FONTS__*/", _font_faces())
            .replace("__DATA__", json.dumps(data).replace("</", "<\\/")))


def _font_faces() -> str:
    """Manrope, embedded so the page looks the same offline (SIL Open Font License, see fonts/OFL.txt)."""
    faces = []
    for weight in (400, 600, 700):
        data = resources.files("captionkit").joinpath(f"fonts/Manrope-{weight}.woff2").read_bytes()
        faces.append("@font-face { font-family: Manrope; font-weight: %d; font-style: normal; font-display: swap; "
                     "src: url(data:font/woff2;base64,%s) format('woff2'); }" % (weight, base64.b64encode(data).decode()))
    return "\n".join(faces)


def write(cues: list[Cue], profile: Profile, out: str | Path, video: str | Path | None = None) -> Path:
    out = Path(out)
    video_url = ""
    if video:
        # relative to the page, so the pair can be moved, shared or served together
        relative = os.path.relpath(Path(video).resolve(), out.resolve().parent)
        video_url = quote(Path(relative).as_posix())
    out.write_text(render(cues, profile, video_url, Path(video).name if video else "Caption preview"), encoding="utf-8")
    return out


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Caption preview</title>
<style>
  /*__FONTS__*/
  :root { --bg:#0f1115; --panel:#171a21; --line:#262b36; --ink:#e7e9ee; --mute:#9aa3b2;
          --ok:#2f9e6b; --warn:#d99a1e; --err:#d9473f; --accent:#5b8def; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font:14px/1.45 Manrope, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  header { display:flex; align-items:center; gap:16px; padding:12px 20px; border-bottom:1px solid var(--line); flex-wrap:wrap; }
  header h1 { font-size:15px; margin:0; font-weight:600; }
  .stat { color:var(--mute); font-variant-numeric:tabular-nums; }
  .stat b { color:var(--ink); font-weight:600; }
  .spacer { flex:1; }
  select, button { background:var(--panel); color:var(--ink); border:1px solid var(--line);
                   border-radius:6px; padding:6px 10px; font:inherit; font-weight:600; cursor:pointer; }
  button:hover, select:hover { border-color:#3a4252; }
  main { display:grid; grid-template-columns:minmax(0,1fr) 380px; height:calc(100vh - 57px); }
  @media (max-width: 900px) { main { grid-template-columns:1fr; height:auto; } }
  .stage { display:flex; flex-direction:column; min-width:0; border-right:1px solid var(--line); }
  .player { position:relative; background:#000; flex:1; min-height:240px; display:flex; align-items:center; justify-content:center; }
  video { max-width:100%; max-height:100%; width:100%; height:100%; object-fit:contain; }
  .drop { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; color:var(--mute);
          text-align:center; padding:24px; pointer-events:none; }
  .caption { position:absolute; left:50%; bottom:7%; transform:translateX(-50%); max-width:90%; text-align:center; pointer-events:none; }
  .caption span { display:inline-block; background:rgba(0,0,0,.78); color:#fff; padding:2px 8px;
                  font-size:clamp(14px, 2.4vw, 26px); line-height:1.35; white-space:pre; }
  .controls { display:flex; gap:8px; align-items:center; padding:10px 14px; border-top:1px solid var(--line); flex-wrap:wrap; }
  .time { font-variant-numeric:tabular-nums; color:var(--mute); min-width:150px; }
  .offset { font-variant-numeric:tabular-nums; }
  .timeline { position:relative; height:46px; margin:0 14px 14px; background:var(--panel); border:1px solid var(--line); border-radius:6px; cursor:pointer; overflow:hidden; }
  .block { position:absolute; top:8px; bottom:8px; border-radius:3px; background:var(--ok); opacity:.85; }
  .block.warn { background:var(--warn); } .block.err { background:var(--err); }
  .head { position:absolute; top:0; bottom:0; width:2px; background:#fff; }
  aside { display:flex; flex-direction:column; min-height:0; }
  .filters { display:flex; gap:8px; padding:10px 14px; border-bottom:1px solid var(--line); align-items:center; }
  .list { overflow:auto; flex:1; }
  .row { padding:10px 14px; border-bottom:1px solid var(--line); cursor:pointer; }
  .row:hover { background:#1b1f27; } .row.now { background:#1d2433; box-shadow:inset 3px 0 0 var(--accent); }
  .row .meta { display:flex; gap:8px; color:var(--mute); font-size:12px; font-variant-numeric:tabular-nums; }
  .row .text { margin-top:4px; white-space:pre-wrap; }
  .tag { font-size:11px; padding:1px 6px; border-radius:10px; border:1px solid currentColor; }
  .tag.warn { color:var(--warn); } .tag.err { color:var(--err); }
  .msg { font-size:12px; margin-top:4px; }
  .msg.warn { color:var(--warn); } .msg.err { color:var(--err); }
  .keys { color:var(--mute); font-size:12px; padding:8px 14px; border-top:1px solid var(--line); }
  kbd { border:1px solid var(--line); border-radius:4px; padding:0 4px; font:11px ui-monospace, monospace; }
  input[type=file] { display:none; }
</style>
</head>
<body>
<header>
  <h1 id="title">Caption preview</h1>
  <span class="stat"><b id="n">0</b> cues</span>
  <span class="stat">peak <b id="peak">-</b> chars/s</span>
  <span class="stat"><b id="nerr">0</b> errors, <b id="nwarn">0</b> warnings</span>
  <span class="spacer"></span>
  <label class="stat">Style <select id="profile"></select></label>
  <button id="openVideo">Open video</button>
  <button id="openCaps">Open captions</button>
  <input type="file" id="videoFile" accept="video/*,audio/*">
  <input type="file" id="capsFile" accept=".srt,.vtt">
</header>
<main>
  <section class="stage">
    <div class="player" id="player">
      <video id="video" playsinline></video>
      <div class="drop" id="drop">Drop a video and a caption file (.srt or .vtt) here,<br>or use Open video and Open captions.</div>
      <div class="caption" id="caption"></div>
    </div>
    <div class="controls">
      <button id="play">Play</button>
      <button id="prev" title="Previous cue (J)">Prev cue</button>
      <button id="next" title="Next cue (L)">Next cue</button>
      <span class="time" id="time">00:00:00.000</span>
      <span class="spacer"></span>
      <span>Offset <b class="offset" id="offset">0.00s</b></span>
      <button data-nudge="-0.1">-0.1s</button><button data-nudge="0.1">+0.1s</button>
      <button id="save">Download SRT</button>
    </div>
    <div class="timeline" id="timeline"><div class="head" id="head"></div></div>
  </section>
  <aside>
    <div class="filters">
      <label><input type="checkbox" id="onlyIssues"> Problems only</label>
    </div>
    <div class="list" id="list"></div>
    <div class="keys"><kbd>Space</kbd> play &middot; <kbd>J</kbd>/<kbd>L</kbd> previous/next cue &middot;
      <kbd>[</kbd>/<kbd>]</kbd> nudge 0.1s (<kbd>Shift</kbd> for 1s)</div>
  </aside>
</main>
<script>
const DATA = __DATA__;
const $ = (id) => document.getElementById(id);
const video = $("video");
let cues = DATA.cues, offset = 0, issues = [], profile = DATA.profiles[DATA.profile];

function fmt(t, sep = ".") {
  t = Math.max(0, t); const ms = Math.round(t * 1000);
  const h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, s = Math.floor(ms / 1000) % 60;
  return [h, m, s].map(v => String(v).padStart(2, "0")).join(":") + sep + String(ms % 1000).padStart(3, "0");
}
function parseTime(s) {
  const m = s.trim().match(/^(?:(\d+):)?(\d{1,2}):(\d{1,2})[,.](\d{1,3})$/);
  if (!m) throw new Error("bad timestamp " + s);
  return (+(m[1] || 0)) * 3600 + (+m[2]) * 60 + (+m[3]) + (+(m[4] + "00").slice(0, 3)) / 1000;
}
function parseCaptions(text) {
  text = text.replace(/^﻿/, "").replace(/\r\n?/g, "\n");
  const out = [];
  for (let block of text.trim().split(/\n\s*\n/)) {
    let lines = block.split("\n");
    if (/^(WEBVTT|NOTE|STYLE|REGION)/.test(lines[0])) continue;
    if (!lines[0].includes("-->")) lines = lines.slice(1);
    if (!lines.length || !lines[0].includes("-->")) continue;
    const [a, b] = lines[0].split("-->");
    out.push({ start: parseTime(a), end: parseTime(b.trim().split(/\s+/)[0]), lines: lines.slice(1) });
  }
  return out;
}
const text = (c) => c.lines.join(" ").trim();
function lint() {
  const p = profile, out = [];
  cues.forEach((c, i) => {
    const n = i + 1, d = c.end - c.start, chars = text(c).length;
    const add = (level, code, message) => out.push({ level, cue: n, code, message });
    if (!chars) add("error", "empty-cue", "no text");
    if (d <= 0) { add("error", "bad-timing", "ends before it starts"); return; }
    if (c.lines.length > p.max_lines) add("error", "too-many-lines", c.lines.length + " lines (max " + p.max_lines + ")");
    c.lines.forEach(l => { if (l.length > p.max_chars) add("error", "line-too-long", l.length + " characters (max " + p.max_chars + ")"); });
    if (d < p.min_duration - 1e-6) add("warning", "too-short", d.toFixed(2) + "s on screen (min " + p.min_duration.toFixed(2) + "s)");
    if (d > p.max_duration + 1e-6) add("warning", "too-long", d.toFixed(2) + "s on screen (max " + p.max_duration + "s)");
    if (chars / d > p.max_cps + 0.05) add("warning", "reading-speed", (chars / d).toFixed(1) + " chars/s (max " + p.max_cps + ")");
    if (i) {
      const prev = cues[i - 1];
      if (c.start < prev.end - 1e-6) add("error", "overlap", "overlaps cue " + i + " by " + (prev.end - c.start).toFixed(3) + "s");
      else if (c.start > prev.end && c.start - prev.end < p.min_gap - 1e-6) add("warning", "small-gap", Math.round((c.start - prev.end) * 1000) + "ms after cue " + i);
    }
  });
  return out;
}
function levelOf(n) {
  const mine = issues.filter(x => x.cue === n);
  return mine.some(x => x.level === "error") ? "err" : mine.length ? "warn" : "";
}
function render() {
  issues = lint();
  $("n").textContent = cues.length;
  const speeds = cues.filter(c => c.end > c.start).map(c => text(c).length / (c.end - c.start));
  $("peak").textContent = speeds.length ? Math.max(...speeds).toFixed(1) : "-";
  $("nerr").textContent = issues.filter(x => x.level === "error").length;
  $("nwarn").textContent = issues.filter(x => x.level === "warning").length;
  const only = $("onlyIssues").checked, list = $("list");
  list.innerHTML = "";
  cues.forEach((c, i) => {
    const n = i + 1, lvl = levelOf(n);
    if (only && !lvl) return;
    const row = document.createElement("div");
    row.className = "row"; row.dataset.n = n;
    const cps = c.end > c.start ? (text(c).length / (c.end - c.start)).toFixed(1) : "-";
    row.innerHTML = '<div class="meta"><span>#' + n + '</span><span>' + fmt(c.start + offset) + '</span><span>' +
      (c.end - c.start).toFixed(2) + 's</span><span>' + cps + ' ch/s</span>' +
      (lvl ? '<span class="tag ' + lvl + '">' + (lvl === "err" ? "error" : "warning") + '</span>' : "") + '</div>';
    const body = document.createElement("div"); body.className = "text"; body.textContent = c.lines.join("\n");
    row.appendChild(body);
    issues.filter(x => x.cue === n).forEach(x => {
      const m = document.createElement("div"); m.className = "msg " + (x.level === "error" ? "err" : "warn");
      m.textContent = x.message; row.appendChild(m);
    });
    row.onclick = () => { video.currentTime = c.start + offset + 0.01; };
    list.appendChild(row);
  });
  drawTimeline();
}
function total() { return video.duration || (cues.length ? cues[cues.length - 1].end + offset + 1 : 1); }
function drawTimeline() {
  const tl = $("timeline"); tl.querySelectorAll(".block").forEach(b => b.remove());
  const T = total();
  cues.forEach((c, i) => {
    const b = document.createElement("div");
    b.className = "block " + levelOf(i + 1);
    b.style.left = ((c.start + offset) / T * 100) + "%";
    b.style.width = Math.max(0.15, (c.end - c.start) / T * 100) + "%";
    b.title = "#" + (i + 1) + "  " + text(c);
    tl.appendChild(b);
  });
}
function current(t) { return cues.findIndex(c => t >= c.start + offset && t < c.end + offset); }
function hasVideo() { return video.readyState > 0 && !video.error; }
function prompt(message) { const d = $("drop"); d.innerHTML = message; d.style.display = message ? "flex" : "none"; }
function tick() {
  const t = video.currentTime, i = hasVideo() ? current(t) : -1;
  const box = $("caption"); box.innerHTML = "";
  if (i >= 0) { const s = document.createElement("span"); s.textContent = cues[i].lines.join("\n"); box.appendChild(s); }
  $("time").textContent = fmt(t) + (i >= 0 ? "   #" + (i + 1) : "");
  $("head").style.left = (t / total() * 100) + "%";
  document.querySelectorAll(".row.now").forEach(r => r.classList.remove("now"));
  const row = document.querySelector('.row[data-n="' + (i + 1) + '"]');
  if (row) { row.classList.add("now"); if (!video.paused) row.scrollIntoView({ block: "nearest" }); }
  requestAnimationFrame(tick);
}
function jump(dir) {
  const t = video.currentTime;
  const target = dir > 0 ? cues.find(c => c.start + offset > t + 0.05) : [...cues].reverse().find(c => c.start + offset < t - 0.3);
  if (target) video.currentTime = target.start + offset + 0.01;
}
function nudge(s) { offset = Math.round((offset + s) * 100) / 100; $("offset").textContent = offset.toFixed(2) + "s"; render(); }
function download() {
  const srt = cues.map((c, i) => (i + 1) + "\n" + fmt(c.start + offset, ",") + " --> " + fmt(c.end + offset, ",") + "\n" + c.lines.join("\n")).join("\n\n") + "\n";
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([srt], { type: "text/plain" }));
  a.download = (DATA.title.replace(/\.[^.]+$/, "") || "captions") + (offset ? "-shifted" : "") + ".srt";
  a.click();
}
function loadVideo(file) { video.src = URL.createObjectURL(file); $("title").textContent = file.name; prompt(""); }
function loadCaptions(file) {
  file.text().then(t => { cues = parseCaptions(t); offset = 0; nudge(0); if (!hasVideo()) prompt(NEED_VIDEO); });
}
const NEED_VIDEO = "Captions loaded. Now add the video:<br>drop it here or use Open video.";

Object.keys(DATA.profiles).forEach(k => {
  const o = document.createElement("option"); o.value = k; o.textContent = k; $("profile").appendChild(o);
});
$("profile").value = DATA.profile;
$("profile").onchange = (e) => { profile = DATA.profiles[e.target.value]; render(); };
$("onlyIssues").onchange = render;
$("play").onclick = () => video.paused ? video.play() : video.pause();
video.onplay = () => $("play").textContent = "Pause"; video.onpause = () => $("play").textContent = "Play";
video.onloadedmetadata = () => { prompt(""); drawTimeline(); };
video.onerror = () => prompt("This video could not be played here.<br>Use Open video to choose it, or drop it in.");
$("prev").onclick = () => jump(-1); $("next").onclick = () => jump(1);
document.querySelectorAll("[data-nudge]").forEach(b => b.onclick = () => nudge(+b.dataset.nudge));
$("save").onclick = download;
$("timeline").onclick = (e) => { const r = e.currentTarget.getBoundingClientRect(); video.currentTime = (e.clientX - r.left) / r.width * total(); };
$("openVideo").onclick = () => $("videoFile").click(); $("openCaps").onclick = () => $("capsFile").click();
$("videoFile").onchange = (e) => e.target.files[0] && loadVideo(e.target.files[0]);
$("capsFile").onchange = (e) => e.target.files[0] && loadCaptions(e.target.files[0]);
$("player").ondragover = (e) => e.preventDefault();
$("player").ondrop = (e) => {
  e.preventDefault();
  for (const f of e.dataTransfer.files) /\.(srt|vtt)$/i.test(f.name) ? loadCaptions(f) : loadVideo(f);
};
document.addEventListener("keydown", (e) => {
  if (e.target.tagName === "SELECT" || e.target.tagName === "INPUT") return;
  if (e.code === "Space") { e.preventDefault(); $("play").click(); }
  else if (e.key === "j" || e.key === "J") jump(-1);
  else if (e.key === "l" || e.key === "L") jump(1);
  else if (e.key === "[" || e.key === "{") nudge(e.shiftKey ? -1 : -0.1);
  else if (e.key === "]" || e.key === "}") nudge(e.shiftKey ? 1 : 0.1);
});
if (DATA.video) { video.src = DATA.video; $("title").textContent = DATA.title; prompt(""); }
else if (cues.length) prompt(NEED_VIDEO);
render(); tick();
</script>
</body>
</html>
"""
