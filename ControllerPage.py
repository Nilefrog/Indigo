"""
THE PAGE A PHONE OPENS TO BECOME A CONTROLLER.

Remote.py serves this to any phone that opens the address shown in the game's "Phone Controllers" screen.
It is one self-contained web page (no internet needed), kept inside a Python file so it is bundled with the game automatically.

What it does: draws the game's picture (the game sends it as small JPEGs down the same WebSocket) full-screen, puts big see-through
buttons on top of it, follows every finger, and sends the buttons that are held back to the game. The game tells it whether to
show the fight buttons or the menu buttons, and which player the phone is. The SCREEN button turns the picture off.
Keep BITS in the same order as Remote.BITS.
"""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#0e0e18">
<title>Indigo Controller</title>
<style>
  html, body { margin: 0; height: 100%; background: #0e0e18; overflow: hidden; overscroll-behavior: none;
               touch-action: none; user-select: none; -webkit-user-select: none; -webkit-touch-callout: none;
               -webkit-tap-highlight-color: transparent; font-family: system-ui, sans-serif; }
  canvas { position: fixed; inset: 0; width: 100%; height: 100%; display: block; }
  #rotate { position: fixed; inset: 0; display: none; align-items: center; justify-content: center; text-align: center;
            background: #0e0e18; color: #fff; font-size: 7vw; padding: 10vw; z-index: 5; }
  @media (orientation: portrait) { #rotate { display: flex; } }
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="rotate">Turn your phone sideways to use it as a controller</div>
<script>
"use strict";

// LOGIC-START  (pure functions: no screen, no network. The game's tests run these in Node.)
const BITS = ["left", "right", "up", "down", "jump", "dash", "parry", "heavy", "light", "confirm", "back", "pause"];
const BASE_W = 1280, BASE_H = 720, DEADZONE = 0.30;

// x, y, radius on a 1280 x 720 screen, plus label / colour / which bit of BITS the button sets (no bit = not a game button)
const GAME_BUTTONS = {
  dpad:  { x: 200,  y: 535, r: 150 },
  jump:  { x: 1175, y: 575, r: 105, label: "JUMP",  colour: "#5ad26e" },
  light: { x: 975,  y: 610, r: 92,  label: "LIGHT", colour: "#5096ff" },
  heavy: { x: 985,  y: 410, r: 92,  label: "HEAVY", colour: "#f05a5a" },
  dash:  { x: 1175, y: 345, r: 83,  label: "DASH",  colour: "#f5cd46" },
  parry: { x: 790,  y: 560, r: 83,  label: "PARRY", colour: "#be78f0" },
  pause: { x: 1225, y: 50,  r: 44,  label: "II",    colour: "#dddddd", bit: "pause" },
  view:  { x: 60,   y: 50,  r: 44,  label: "SCREEN", colour: "#6cd4ff", bit: null },
};
const MENU_BUTTONS = {
  dpad:    { x: 200,  y: 535, r: 150 },
  confirm: { x: 1130, y: 560, r: 105, label: "OK",    colour: "#5ad26e" },
  back:    { x: 925,  y: 625, r: 80,  label: "BACK",  colour: "#f06464" },
  start:   { x: 1210, y: 80,  r: 64,  label: "START", colour: "#f5cd46", bit: "pause" },
  view:    { x: 60,   y: 50,  r: 44,  label: "SCREEN", colour: "#6cd4ff", bit: null },
};

function makeLayout(mode, W, H) {
  const src = mode === "game" ? GAME_BUTTONS : MENU_BUTTONS;
  const sx = W / BASE_W, sy = H / BASE_H;
  const out = {};
  for (const name in src) {
    const b = src[name];
    out[name] = { x: b.x * sx, y: b.y * sy, r: b.r, label: b.label, colour: b.colour, bit: ("bit" in b) ? b.bit : name };
  }
  // The buttons are drawn as large as this particular phone allows (the layout above is big already), but never so big that
  // two touch or one runs off the edge of the screen.
  let k = Math.min(sx, sy);
  const items = Object.values(out);
  for (let i = 0; i < items.length; i++) {
    const a = items[i];
    k = Math.min(k, a.x / a.r, (W - a.x) / a.r, a.y / a.r, (H - a.y) / a.r);
    for (let j = i + 1; j < items.length; j++) {
      const b = items[j];
      k = Math.min(k, Math.hypot(a.x - b.x, a.y - b.y) / (a.r + b.r) * 0.97);
    }
  }
  for (const b of items) b.r *= k;
  return out;
}

// Which control is under this point? "dpad", a button's name, or null.
function hitTest(layout, x, y) {
  const p = layout.dpad;
  if (Math.hypot(x - p.x, y - p.y) <= p.r * 1.35) return "dpad";
  let best = null, bestD = Infinity;
  for (const name in layout) {
    if (name === "dpad") continue;
    const b = layout[name], d = Math.hypot(x - b.x, y - b.y);
    if (d <= b.r * 1.2 && d < bestD) { best = name; bestD = d; }
  }
  return best;
}

// fingers: { id: {role, x, y} }  ->  which bits are held, and where the pad's thumb is (for drawing)
function computeHeld(layout, fingers) {
  const held = new Set();
  let vec = [0, 0];
  for (const id in fingers) {
    const f = fingers[id];
    if (f.role === "dpad") {
      const p = layout.dpad;
      let dx = (f.x - p.x) / p.r, dy = (f.y - p.y) / p.r;
      const len = Math.hypot(dx, dy);
      if (len > 1) { dx /= len; dy /= len; }
      vec = [dx, dy];
      if (dx < -DEADZONE) held.add("left");
      if (dx > DEADZONE) held.add("right");
      if (dy < -DEADZONE) held.add("up");
      if (dy > DEADZONE) held.add("down");
    } else if (f.role && layout[f.role] && layout[f.role].bit) {
      held.add(layout[f.role].bit);
    }
  }
  return { held, vec };
}

function maskOf(held) {
  let m = 0;
  for (const name of held) { const i = BITS.indexOf(name); if (i >= 0) m |= (1 << i); }
  return m;
}

// How the game's picture is placed on this screen: as large as possible without cutting anything off, in the middle.
function fitPicture(imgW, imgH, W, H) {
  const s = Math.min(W / imgW, H / imgH);
  return { x: (W - imgW * s) / 2, y: (H - imgH * s) / 2, w: imgW * s, h: imgH * s };
}
// LOGIC-END

const canvas = document.getElementById("c");
const ctx = canvas.getContext("2d");
let W = 0, H = 0, dpr = 1;
let mode = "menu", slot = null, colour = "#8888aa", pname = "";
let status = "connecting";                    // connecting | connected | reconnecting | nokey
let layout = makeLayout(mode, 1280, 720);
const fingers = {};
let heldNow = new Set(), vec = [0, 0], lastMask = -1, lastSent = 0;
let ws = null;
let showScreen = true, picture = null, pictureAt = 0;       // the game's picture (an ImageBitmap or <img>) and when it arrived

function resize() {
  dpr = window.devicePixelRatio || 1;
  W = window.innerWidth; H = window.innerHeight;
  canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
  layout = makeLayout(mode, W, H);
}
window.addEventListener("resize", resize);
window.addEventListener("orientationchange", () => setTimeout(resize, 200));
resize();

// ---------- sending ----------
function send(obj) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); }
function sendMask(force) {
  const m = maskOf(heldNow), now = performance.now();
  if (force || m !== lastMask || now - lastSent > 1000) {      // also once a second, so the game knows we are still here
    lastMask = m; lastSent = now; send({ t: "in", h: m });
  }
}
function recompute() {
  const before = heldNow;
  const r = computeHeld(layout, fingers);
  heldNow = r.held; vec = r.vec;
  if (navigator.vibrate) for (const b of heldNow) if (!before.has(b) && b !== "left" && b !== "right" && b !== "up" && b !== "down") { navigator.vibrate(12); break; }
  sendMask(false);
}
function releaseAll() { for (const id in fingers) delete fingers[id]; heldNow = new Set(); vec = [0, 0]; sendMask(true); }
setInterval(() => sendMask(false), 250);

function toggleScreen() {
  showScreen = !showScreen;
  if (!showScreen) picture = null;
  send({ t: "view", on: showScreen });                          // tells the game to stop (or start) sending pictures
}

// ---------- fingers ----------
let primed = false;
function prime() {                              // the first touch is the browser's permission to do a few things
  if (primed) return; primed = true;
  try { if (navigator.wakeLock) navigator.wakeLock.request("screen").catch(() => {}); } catch (e) {}
  try { const el = document.documentElement; if (el.requestFullscreen) el.requestFullscreen().catch(() => {}); } catch (e) {}
}
function down(id, x, y) {
  const role = hitTest(layout, x, y);
  if (role === "view") { toggleScreen(); return; }              // a tap, not a held button
  fingers[id] = { role, x, y }; recompute();
}
function move(id, x, y) {
  const f = fingers[id]; if (!f) return;
  f.x = x; f.y = y;
  if (f.role !== "dpad") { const h = hitTest(layout, x, y); f.role = (h && h !== "dpad" && h !== "view") ? h : null; }   // sliding thumb switches button
  recompute();
}
function up(id) { if (fingers[id]) { delete fingers[id]; recompute(); } }

canvas.addEventListener("touchstart", e => { e.preventDefault(); prime(); for (const t of e.changedTouches) down(t.identifier, t.clientX, t.clientY); }, { passive: false });
canvas.addEventListener("touchmove", e => { e.preventDefault(); for (const t of e.changedTouches) move(t.identifier, t.clientX, t.clientY); }, { passive: false });
canvas.addEventListener("touchend", e => { e.preventDefault(); for (const t of e.changedTouches) up(t.identifier); }, { passive: false });
canvas.addEventListener("touchcancel", e => { e.preventDefault(); for (const t of e.changedTouches) up(t.identifier); }, { passive: false });
// a mouse works as one finger (trying it on a computer)
let mouseDown = false;
canvas.addEventListener("mousedown", e => { mouseDown = true; down("mouse", e.clientX, e.clientY); });
window.addEventListener("mousemove", e => { if (mouseDown) move("mouse", e.clientX, e.clientY); });
window.addEventListener("mouseup", () => { if (mouseDown) { mouseDown = false; up("mouse"); } });
document.addEventListener("visibilitychange", () => { if (document.hidden) releaseAll(); });
document.addEventListener("contextmenu", e => e.preventDefault());

// ---------- the game's picture ----------
let decoding = false, waiting = null;
function decode(blob) {                          // turns the JPEG into something drawable. If still busy, only the newest waiting one is kept.
  if (decoding) { waiting = blob; return; }
  decoding = true;
  const done = img => {
    if (img) { if (picture && picture.close) picture.close(); picture = img; pictureAt = performance.now(); }
    decoding = false;
    if (waiting) { const b = waiting; waiting = null; decode(b); }
  };
  if (window.createImageBitmap) {
    createImageBitmap(blob).then(done, () => done(null));
  } else {                                       // older browsers
    const url = URL.createObjectURL(blob), img = new Image();
    img.onload = () => { URL.revokeObjectURL(url); done(img); };
    img.onerror = () => { URL.revokeObjectURL(url); done(null); };
    img.src = url;
  }
}

// ---------- connection ----------
function connect() {
  const key = new URLSearchParams(location.search).get("k");
  if (!key) { status = "nokey"; return; }
  const proto = location.protocol === "https:" ? "wss://" : "ws://";
  ws = new WebSocket(proto + location.host + "/ws?k=" + encodeURIComponent(key));
  ws.binaryType = "blob";
  ws.onopen = () => {
    status = "connected";
    send({ t: "hello", name: localStorage.getItem("indigoName") || "" });
    send({ t: "view", on: showScreen });
    sendMask(true);
  };
  ws.onmessage = e => {
    if (typeof e.data !== "string") { if (showScreen) decode(e.data); return; }
    let m; try { m = JSON.parse(e.data); } catch (err) { return; }
    if (m.t !== "state") return;
    const changed = m.mode !== mode;
    mode = m.mode === "game" ? "game" : "menu";
    slot = (m.slot === null || m.slot === undefined) ? null : m.slot;
    colour = m.colour || "#8888aa"; pname = m.name || "";
    if (changed) { layout = makeLayout(mode, W, H); releaseAll(); }
  };
  ws.onclose = () => { status = "reconnecting"; picture = null; releaseAll(); setTimeout(connect, 1000); };
  ws.onerror = () => { try { ws.close(); } catch (err) {} };
}

// ---------- drawing ----------
function circle(x, y, r, fill, stroke, width) {
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.lineWidth = width; ctx.strokeStyle = stroke; ctx.stroke(); }
}
function hexA(hex, a) {
  const n = parseInt(hex.slice(1), 16);
  return "rgba(" + (n >> 16 & 255) + "," + (n >> 8 & 255) + "," + (n & 255) + "," + a + ")";
}
function draw() {
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = "#0e0e18"; ctx.fillRect(0, 0, W, H);

  // the game, as big as fits
  if (picture && showScreen) {
    const iw = picture.width, ih = picture.height, p = fitPicture(iw, ih, W, H);
    ctx.drawImage(picture, p.x, p.y, p.w, p.h);
  }

  for (const name in layout) {
    const b = layout[name];
    if (name === "dpad") {
      circle(b.x, b.y, b.r, "rgba(0,0,0,0.22)", "rgba(255,255,255,0.7)", 4);
      ctx.fillStyle = "rgba(255,255,255,0.85)";
      for (const [dx, dy] of [[0, -1], [0, 1], [-1, 0], [1, 0]]) {
        const tx = b.x + dx * b.r * 0.84, ty = b.y + dy * b.r * 0.84, bx = b.x + dx * b.r * 0.62, by = b.y + dy * b.r * 0.62;
        const px = -dy * b.r * 0.17, py = dx * b.r * 0.17;
        ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(bx + px, by + py); ctx.lineTo(bx - px, by - py); ctx.closePath(); ctx.fill();
      }
      const active = Object.values(fingers).some(f => f.role === "dpad");
      circle(b.x + vec[0] * b.r * 0.62, b.y + vec[1] * b.r * 0.62, b.r * 0.38, "rgba(255,255,255," + (active ? 0.75 : 0.4) + ")", "rgba(0,0,0,0.55)", 3);
    } else {
      const isView = name === "view";
      const on = isView ? showScreen : heldNow.has(b.bit);
      const idle = isView ? 0.28 : 0.2;                           // see-through, so the game shows underneath
      circle(b.x, b.y, b.r, hexA(b.colour, on ? 0.7 : idle), hexA(b.colour, 0.95), 4);
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.font = "bold " + Math.round(b.r * (isView ? 0.30 : 0.42)) + "px system-ui, sans-serif";
      ctx.lineWidth = 4; ctx.strokeStyle = "rgba(0,0,0,0.55)"; ctx.strokeText(b.label, b.x, b.y);
      ctx.fillStyle = "#fff"; ctx.fillText(b.label, b.x, b.y);
      if (isView && !showScreen) { ctx.strokeStyle = "#fff"; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(b.x - b.r * 0.7, b.y + b.r * 0.7); ctx.lineTo(b.x + b.r * 0.7, b.y - b.r * 0.7); ctx.stroke(); }
    }
  }

  // who am I / are we connected: a small label at the top, on a dark pill so it reads over the picture
  let text, tc = "#ffffff";
  if (status === "nokey") { text = "Open the address shown in the game (or scan its code)"; tc = "#f5cd46"; }
  else if (status !== "connected") { text = status === "connecting" ? "Connecting..." : "Reconnecting..."; tc = "#f5cd46"; }
  else if (slot === null) { text = (pname ? pname + " - " : "") + "connected. Join from the character screen"; }
  else { text = "Player " + (slot + 1) + (pname ? " - " + pname : ""); tc = colour; }
  ctx.font = "bold 16px system-ui, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  const tw = ctx.measureText(text).width + 24;
  ctx.fillStyle = "rgba(0,0,0,0.6)"; ctx.fillRect(W / 2 - tw / 2, 8, tw, 28);
  ctx.fillStyle = tc; ctx.fillText(text, W / 2, 22);
  if (status === "connected" && showScreen && !picture) {
    ctx.fillStyle = "rgba(255,255,255,0.6)"; ctx.font = "16px system-ui, sans-serif"; ctx.fillText("Waiting for the game's picture...", W / 2, H / 2);
  }
  // coloured edge = which player you are
  ctx.lineWidth = 6; ctx.strokeStyle = slot === null ? "#3a3a55" : colour; ctx.strokeRect(3, 3, W - 6, H - 6);
  requestAnimationFrame(draw);
}
connect();
draw();
</script>
</body>
</html>
"""
