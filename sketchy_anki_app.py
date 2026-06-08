#!/usr/bin/env python3
"""Local app for turning labeled Sketchy-style images into Anki decks.

Run:
    python3 scripts/sketchy_anki_app.py

Then open the printed localhost URL. The app keeps uploaded images in the
browser until you click "Build Anki deck"; only the generated deck is written
temporarily on the Python side.
"""

from __future__ import annotations

import base64
import argparse
import hashlib
import html
import json
import os
import random
import re
import sqlite3
import tempfile
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.parse import urlparse


APP_HOST = "127.0.0.1"
APP_PORT = 8765


HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sketchy Symbols to Anki</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f7f4;
      --ink: #1d1d1f;
      --muted: #64645f;
      --line: #d9d6cc;
      --panel: #ffffff;
      --accent: #1769aa;
      --accent-dark: #0d4776;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    header {
      padding: 20px 28px 14px;
      border-bottom: 1px solid var(--line);
      background: #fff;
      position: sticky;
      top: 0;
      z-index: 5;
    }
    h1 {
      font-size: 22px;
      margin: 0 0 4px;
      letter-spacing: 0;
    }
    .sub {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }
    main {
      display: grid;
      grid-template-columns: minmax(340px, 440px) minmax(0, 1fr);
      gap: 18px;
      padding: 18px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-width: 0;
    }
    h2 {
      font-size: 15px;
      margin: 0 0 12px;
    }
    label {
      display: block;
      font-size: 13px;
      font-weight: 650;
      margin: 12px 0 6px;
    }
    input[type="text"], input[type="number"], textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      font: inherit;
      background: #fff;
      color: var(--ink);
    }
    input[type="file"] {
      width: 100%;
      font-size: 13px;
    }
    textarea {
      min-height: 260px;
      resize: vertical;
      line-height: 1.35;
    }
    button {
      border: 1px solid var(--accent);
      background: var(--accent);
      color: white;
      border-radius: 6px;
      padding: 9px 12px;
      font: inherit;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary {
      background: #fff;
      color: var(--accent);
    }
    button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .row {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .row > * { flex: 1; }
    .actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 12px;
    }
    .hint {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
      margin-top: 7px;
    }
    .image-stage {
      position: relative;
      width: 100%;
      background: #191713;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      min-height: 260px;
    }
    #labeledImg {
      display: block;
      width: 100%;
      height: auto;
    }
    .marker {
      position: absolute;
      width: 18px;
      height: 18px;
      margin-left: -9px;
      margin-top: -9px;
      border-radius: 999px;
      border: 2px solid #fff;
      background: #1769aa;
      color: #fff;
      font-size: 10px;
      line-height: 14px;
      text-align: center;
      pointer-events: none;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.45);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 12px;
      margin-top: 14px;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #fff;
    }
    .card-head {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      margin-bottom: 8px;
    }
    .badge {
      flex: 0 0 auto;
      background: #efeee8;
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 12px;
      font-weight: 700;
    }
    .symbol-title {
      font-weight: 750;
      overflow-wrap: anywhere;
    }
    .card textarea {
      min-height: 72px;
      font-size: 13px;
    }
    .coords {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 6px;
      margin-top: 8px;
    }
    .coords label {
      margin: 0;
      font-size: 11px;
      color: var(--muted);
      font-weight: 600;
    }
    .coords input {
      padding: 7px;
      font-size: 12px;
    }
    canvas.preview {
      width: 100%;
      aspect-ratio: 1 / 1;
      object-fit: contain;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #f2f1ed;
      margin-top: 10px;
    }
    .status {
      margin-top: 10px;
      padding: 9px 10px;
      border-radius: 6px;
      background: #eef6ff;
      color: #123b5d;
      font-size: 13px;
      display: none;
    }
    .status.error {
      background: #fff0f0;
      color: #7c1717;
    }
    @media (max-width: 920px) {
      main { grid-template-columns: 1fr; }
      header { position: static; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Sketchy Symbols to Anki</h1>
    <p class="sub">Make science-first flashcards from a labeled sketch, a clean sketch, and a numbered symbol list.</p>
  </header>
  <main>
    <section>
      <h2>Inputs</h2>
      <label for="deckName">Deck name</label>
      <input id="deckName" type="text" value="Pacemaker Action Potential">

      <label for="labeledFile">Labeled sketch image</label>
      <input id="labeledFile" type="file" accept="image/*">

      <label for="cleanFile">Unlabeled sketch image</label>
      <input id="cleanFile" type="file" accept="image/*">

      <label for="symbolText">Numbered symbol list</label>
      <textarea id="symbolText" placeholder="1.
Ramp:
Phase 4 of the pacemaker cardiac action potential is marked by a slow, spontaneous depolarization"></textarea>

      <div class="row">
        <div>
          <label for="defaultCrop">Default crop size</label>
          <input id="defaultCrop" type="number" value="260" min="80" max="900">
        </div>
        <div>
          <label for="tags">Tags</label>
          <input id="tags" type="text" value="Sketchy Cardio">
        </div>
      </div>

      <div class="actions">
        <button id="parseBtn">Parse symbols</button>
        <button id="buildBtn" disabled>Build Anki deck</button>
      </div>
      <div id="status" class="status"></div>

      <p class="hint">
        After parsing, choose a symbol number, then click its number bubble on the labeled image.
        The app crops from the clean image at the same spot. Edit the drafted front/answer/hook before export.
      </p>
    </section>

    <section>
      <h2>Place Symbol Crops</h2>
      <div class="row">
        <select id="activeSymbol"></select>
        <button id="nextUnplaced" class="secondary">Next unplaced</button>
      </div>
      <div class="image-stage" id="stage">
        <img id="labeledImg" alt="Upload the labeled sketch to place crop centers">
      </div>
      <div class="grid" id="cards"></div>
    </section>
  </main>

  <script>
    const state = {
      labeledImage: null,
      cleanImage: null,
      labeledDataUrl: "",
      cleanDataUrl: "",
      cards: []
    };

    const $ = (id) => document.getElementById(id);
    const statusBox = $("status");

    function setStatus(message, isError = false) {
      statusBox.textContent = message;
      statusBox.className = "status" + (isError ? " error" : "");
      statusBox.style.display = "block";
    }

    function hideStatus() {
      statusBox.style.display = "none";
    }

    function normalizeScienceText(text) {
      return text
        .replace(/Na\s*\n\s*\+/g, "Na+")
        .replace(/Ca\s*\n\s*2\s*\+/g, "Ca2+")
        .replace(/K\s*\n\s*\+/g, "K+")
        .replace(/\s*→\s*/g, " -> ")
        .replace(/[ \t]+\n/g, "\n")
        .replace(/\n{2,}/g, "\n")
        .replace(/\s+/g, " ")
        .trim();
    }

    function parseSymbols(raw) {
      const text = raw.replace(/\r/g, "").trim();
      const regex = /(?:^|\n)\s*(\d+)\.\s*\n?\s*([^:\n]+):\s*\n([\s\S]*?)(?=\n\s*\d+\.\s*\n|$)/g;
      const out = [];
      let match;
      while ((match = regex.exec(text)) !== null) {
        const number = Number(match[1]);
        const symbol = match[2].trim();
        let meaning = match[3].trim();
        meaning = meaning.replace(new RegExp("\\n\\s*" + number + "\\s*$"), "");
        meaning = normalizeScienceText(meaning);
        out.push(makeDraftCard(number, symbol, meaning));
      }
      return out;
    }

    function sentenceCase(s) {
      if (!s) return s;
      return s.charAt(0).toUpperCase() + s.slice(1);
    }

    function stripPeriod(s) {
      return s.replace(/[.;]\s*$/, "").trim();
    }

    function makeDraftCard(number, symbol, meaning) {
      const clean = stripPeriod(meaning);
      let front = `What key fact is associated with ${clean}?`;
      let answer = clean;

      let m = clean.match(/^(.+?)\s+is marked by\s+(.+)$/i);
      if (m) {
        front = `What is marked by ${stripPeriod(m[2])}?`;
        answer = sentenceCase(stripPeriod(m[1]));
      } else if ((m = clean.match(/^(.+?)\s+is due to\s+(.+)$/i))) {
        front = `What is ${stripPeriod(m[1])} due to?`;
        answer = sentenceCase(stripPeriod(m[2]));
      } else if ((m = clean.match(/^(.+?)\s+is the\s+(.+)$/i))) {
        front = `What is ${stripPeriod(m[2])}?`;
        answer = sentenceCase(stripPeriod(m[1]));
      } else if ((m = clean.match(/^(.+?)\s+reflects\s+(.+)$/i))) {
        front = `What does ${stripPeriod(m[1])} reflect?`;
        answer = sentenceCase(stripPeriod(m[2]));
      } else if ((m = clean.match(/^(.+?)\s+lacks\s+(.+)$/i))) {
        front = `Which phases are absent from ${stripPeriod(m[1])}?`;
        answer = sentenceCase(stripPeriod(m[2]));
      } else if ((m = clean.match(/^(.+?)\s+has\s+(.+)$/i))) {
        front = `What does ${stripPeriod(m[1])} have?`;
        answer = sentenceCase(stripPeriod(m[2]));
      } else if ((m = clean.match(/^(.+?)\s*->\s*(.+)$/))) {
        front = `What does ${stripPeriod(m[1])} lead to?`;
        answer = sentenceCase(stripPeriod(m[2]));
      }

      return {
        number,
        symbol,
        meaning: clean,
        front,
        answer,
        hook: `${symbol} = ${clean}`,
        x: "",
        y: "",
        crop: Number($("defaultCrop").value || 260),
        placed: false,
        symbolImage: ""
      };
    }

    function readImageFile(input, callback) {
      const file = input.files && input.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        const img = new Image();
        img.onload = () => callback(reader.result, img);
        img.src = reader.result;
      };
      reader.readAsDataURL(file);
    }

    $("labeledFile").addEventListener("change", () => {
      readImageFile($("labeledFile"), (dataUrl, img) => {
        state.labeledDataUrl = dataUrl;
        state.labeledImage = img;
        $("labeledImg").src = dataUrl;
        renderMarkers();
      });
    });

    $("cleanFile").addEventListener("change", () => {
      readImageFile($("cleanFile"), (dataUrl, img) => {
        state.cleanDataUrl = dataUrl;
        state.cleanImage = img;
        refreshAllPreviews();
      });
    });

    $("parseBtn").addEventListener("click", () => {
      const cards = parseSymbols($("symbolText").value);
      if (!cards.length) {
        setStatus("I could not find any numbered symbols. Check that entries look like: 1. newline Symbol: newline Meaning.", true);
        return;
      }
      hideStatus();
      state.cards = cards.sort((a, b) => a.number - b.number);
      renderSymbolSelect();
      renderCards();
      renderMarkers();
      $("buildBtn").disabled = false;
      setStatus(`Parsed ${state.cards.length} symbols. Click each number bubble on the labeled image to place crops.`);
    });

    $("nextUnplaced").addEventListener("click", selectNextUnplaced);

    function renderSymbolSelect() {
      const sel = $("activeSymbol");
      sel.innerHTML = "";
      for (const card of state.cards) {
        const opt = document.createElement("option");
        opt.value = card.number;
        opt.textContent = `${card.number}. ${card.symbol}`;
        sel.appendChild(opt);
      }
    }

    function activeCard() {
      const n = Number($("activeSymbol").value);
      return state.cards.find((card) => card.number === n);
    }

    function selectNextUnplaced() {
      const card = state.cards.find((c) => !c.placed);
      if (card) {
        $("activeSymbol").value = card.number;
        document.querySelector(`[data-card-number="${card.number}"]`)?.scrollIntoView({behavior: "smooth", block: "center"});
      }
    }

    $("stage").addEventListener("click", (event) => {
      if (!state.labeledImage) return;
      const img = $("labeledImg");
      const rect = img.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) return;
      const card = activeCard();
      if (!card) return;
      const nx = (event.clientX - rect.left) / rect.width;
      const ny = (event.clientY - rect.top) / rect.height;
      card.x = Math.round(nx * state.labeledImage.naturalWidth);
      card.y = Math.round(ny * state.labeledImage.naturalHeight);
      card.placed = true;
      updateCardInputs(card);
      updatePreview(card);
      renderMarkers();
      selectNextUnplaced();
    });

    function renderMarkers() {
      document.querySelectorAll(".marker").forEach((el) => el.remove());
      if (!state.labeledImage) return;
      const stage = $("stage");
      const img = $("labeledImg");
      const rect = img.getBoundingClientRect();
      const stageRect = stage.getBoundingClientRect();
      for (const card of state.cards) {
        if (!card.placed || card.x === "" || card.y === "") continue;
        const marker = document.createElement("div");
        marker.className = "marker";
        marker.textContent = card.number;
        marker.style.left = `${(Number(card.x) / state.labeledImage.naturalWidth) * rect.width + rect.left - stageRect.left}px`;
        marker.style.top = `${(Number(card.y) / state.labeledImage.naturalHeight) * rect.height + rect.top - stageRect.top}px`;
        stage.appendChild(marker);
      }
    }

    window.addEventListener("resize", renderMarkers);

    function renderCards() {
      const root = $("cards");
      root.innerHTML = "";
      for (const card of state.cards) {
        const el = document.createElement("div");
        el.className = "card";
        el.dataset.cardNumber = card.number;
        el.innerHTML = `
          <div class="card-head">
            <div>
              <div class="symbol-title">${escapeHtml(card.symbol)}</div>
              <div class="hint">Original: ${escapeHtml(card.meaning)}</div>
            </div>
            <span class="badge">#${card.number}</span>
          </div>
          <label>Front question</label>
          <textarea data-field="front"></textarea>
          <label>Answer</label>
          <textarea data-field="answer"></textarea>
          <label>Sketch memory hook</label>
          <textarea data-field="hook"></textarea>
          <div class="coords">
            <div><label>X</label><input type="number" data-field="x"></div>
            <div><label>Y</label><input type="number" data-field="y"></div>
            <div><label>Crop px</label><input type="number" min="80" max="900" data-field="crop"></div>
            <div><label>Use</label><button type="button" class="secondary" data-select="${card.number}">Select</button></div>
          </div>
          <canvas class="preview" width="360" height="360" data-preview="${card.number}"></canvas>
        `;
        root.appendChild(el);
        updateCardInputs(card);
        el.querySelectorAll("textarea,input").forEach((input) => {
          input.addEventListener("input", () => {
            const field = input.dataset.field;
            if (field === "x" || field === "y" || field === "crop") {
              card[field] = input.value === "" ? "" : Number(input.value);
              card.placed = card.x !== "" && card.y !== "";
              updatePreview(card);
              renderMarkers();
            } else {
              card[field] = input.value;
            }
          });
        });
        el.querySelector(`[data-select="${card.number}"]`).addEventListener("click", () => {
          $("activeSymbol").value = card.number;
        });
      }
      refreshAllPreviews();
    }

    function updateCardInputs(card) {
      const el = document.querySelector(`[data-card-number="${card.number}"]`);
      if (!el) return;
      for (const field of ["front", "answer", "hook", "x", "y", "crop"]) {
        const input = el.querySelector(`[data-field="${field}"]`);
        if (input) input.value = card[field];
      }
    }

    function refreshAllPreviews() {
      for (const card of state.cards) updatePreview(card);
    }

    function updatePreview(card) {
      const canvas = document.querySelector(`[data-preview="${card.number}"]`);
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#f2f1ed";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#64645f";
      ctx.font = "16px system-ui";
      ctx.textAlign = "center";
      if (!state.cleanImage) {
        ctx.fillText("Upload clean image", canvas.width / 2, canvas.height / 2);
        return;
      }
      if (!card.placed || card.x === "" || card.y === "") {
        ctx.fillText("Click labeled image to place crop", canvas.width / 2, canvas.height / 2);
        return;
      }
      const scaleX = state.cleanImage.naturalWidth / state.labeledImage.naturalWidth;
      const scaleY = state.cleanImage.naturalHeight / state.labeledImage.naturalHeight;
      const crop = Number(card.crop || $("defaultCrop").value || 260);
      const cx = Number(card.x) * scaleX;
      const cy = Number(card.y) * scaleY;
      const size = crop * Math.max(scaleX, scaleY);
      const sx = Math.max(0, Math.min(state.cleanImage.naturalWidth - size, cx - size / 2));
      const sy = Math.max(0, Math.min(state.cleanImage.naturalHeight - size, cy - size / 2));
      ctx.drawImage(state.cleanImage, sx, sy, size, size, 0, 0, canvas.width, canvas.height);
      card.symbolImage = canvas.toDataURL("image/png");
    }

    $("buildBtn").addEventListener("click", async () => {
      if (!state.cleanDataUrl || !state.labeledDataUrl) {
        setStatus("Upload both labeled and clean images first.", true);
        return;
      }
      refreshAllPreviews();
      const missing = state.cards.filter((card) => !card.symbolImage);
      if (missing.length) {
        setStatus(`Place crops for all symbols first. Missing: ${missing.map((c) => c.number).join(", ")}`, true);
        return;
      }
      const payload = {
        deckName: $("deckName").value.trim() || "Sketchy Symbols",
        tags: $("tags").value.trim(),
        fullImage: state.cleanDataUrl,
        cards: state.cards.map((card) => ({
          number: card.number,
          symbol: card.symbol,
          front: card.front,
          answer: card.answer,
          hook: card.hook,
          symbolImage: card.symbolImage
        }))
      };
      setStatus("Building deck...");
      const res = await fetch("/build", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        setStatus(await res.text(), true);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${safeName(payload.deckName)}.apkg`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setStatus(`Built ${payload.cards.length} cards. Your .apkg download should start now.`);
    });

    function escapeHtml(s) {
      return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function safeName(s) {
      return s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "sketchy_deck";
    }
  </script>
</body>
</html>
"""


def data_url_to_bytes(data_url: str) -> bytes:
    match = re.match(r"^data:[^;]+;base64,(.*)$", data_url, re.S)
    if not match:
        raise ValueError("Expected a base64 data URL.")
    return base64.b64decode(match.group(1))


def safe_filename(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return cleaned or fallback


def field_checksum(text: str) -> int:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return int(digest, 16)


def anki_id() -> int:
    return int(time.time() * 1000) + random.randint(1, 999)


def json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def create_schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        CREATE TABLE col (
            id              integer primary key,
            crt             integer not null,
            mod             integer not null,
            scm             integer not null,
            ver             integer not null,
            dty             integer not null,
            usn             integer not null,
            ls              integer not null,
            conf            text not null,
            models          text not null,
            decks           text not null,
            dconf           text not null,
            tags            text not null
        );
        CREATE TABLE notes (
            id              integer primary key,
            guid            text not null,
            mid             integer not null,
            mod             integer not null,
            usn             integer not null,
            tags            text not null,
            flds            text not null,
            sfld            integer not null,
            csum            integer not null,
            flags           integer not null,
            data            text not null
        );
        CREATE TABLE cards (
            id              integer primary key,
            nid             integer not null,
            did             integer not null,
            ord             integer not null,
            mod             integer not null,
            usn             integer not null,
            type            integer not null,
            queue           integer not null,
            due             integer not null,
            ivl             integer not null,
            factor          integer not null,
            reps            integer not null,
            lapses          integer not null,
            left            integer not null,
            odue            integer not null,
            odid            integer not null,
            flags           integer not null,
            data            text not null
        );
        CREATE TABLE revlog (
            id              integer primary key,
            cid             integer not null,
            usn             integer not null,
            ease            integer not null,
            ivl             integer not null,
            lastIvl         integer not null,
            factor          integer not null,
            time            integer not null,
            type            integer not null
        );
        CREATE TABLE graves (
            usn             integer not null,
            oid             integer not null,
            type            integer not null
        );
        CREATE INDEX ix_notes_usn on notes (usn);
        CREATE INDEX ix_cards_usn on cards (usn);
        CREATE INDEX ix_cards_nid on cards (nid);
        CREATE INDEX ix_cards_sched on cards (did, queue, due);
        CREATE INDEX ix_revlog_usn on revlog (usn);
        CREATE INDEX ix_revlog_cid on revlog (cid);
        CREATE INDEX ix_revlog_id on revlog (id);
        """
    )


def insert_collection_metadata(db: sqlite3.Connection, deck_name: str, deck_id: int, model_id: int) -> None:
    now = int(time.time())
    model = {
        str(model_id): {
            "id": model_id,
            "name": "Science-first Sketchy Symbol",
            "type": 0,
            "mod": now,
            "usn": -1,
            "sortf": 0,
            "did": deck_id,
            "tmpls": [
                {
                    "name": "Card 1",
                    "ord": 0,
                    "qfmt": "{{Front}}",
                    "afmt": "{{FrontSide}}<hr id=answer>{{Back}}",
                    "did": None,
                    "bqfmt": "",
                    "bafmt": "",
                }
            ],
            "flds": [
                {"name": "Front", "ord": 0, "sticky": False, "rtl": False, "font": "Arial", "size": 20},
                {"name": "Back", "ord": 1, "sticky": False, "rtl": False, "font": "Arial", "size": 20},
            ],
            "css": (
                ".card { font-family: Arial, sans-serif; font-size: 20px; text-align: left; color: #1d1d1f; "
                "background-color: #ffffff; line-height: 1.35; }\n"
                ".answer { font-size: 22px; font-weight: 700; }\n"
                ".hook { margin-top: 12px; color: #333; }\n"
                "img.symbol { max-width: 520px; width: 95%; border-radius: 6px; }\n"
                "img.full-sketch { max-width: 900px; width: 100%; border-radius: 6px; }\n"
            ),
            "latexPre": "",
            "latexPost": "",
            "req": [[0, "all", [0]]],
            "tags": [],
        }
    }
    decks = {
        "1": {
            "id": 1,
            "name": "Default",
            "desc": "",
            "dyn": 0,
            "collapsed": False,
            "browserCollapsed": False,
            "conf": 1,
            "extendNew": 10,
            "extendRev": 50,
            "mod": now,
            "usn": -1,
        },
        str(deck_id): {
            "id": deck_id,
            "name": deck_name,
            "desc": "",
            "dyn": 0,
            "collapsed": False,
            "browserCollapsed": False,
            "conf": 1,
            "extendNew": 10,
            "extendRev": 50,
            "mod": now,
            "usn": -1,
        },
    }
    dconf = {
        "1": {
            "id": 1,
            "name": "Default",
            "mod": now,
            "usn": -1,
            "maxTaken": 60,
            "autoplay": True,
            "timer": 0,
            "replayq": True,
            "new": {
                "bury": True,
                "delays": [1, 10],
                "initialFactor": 2500,
                "ints": [1, 4, 7],
                "order": 1,
                "perDay": 20,
                "separate": True,
            },
            "rev": {"bury": True, "ease4": 1.3, "ivlFct": 1, "maxIvl": 36500, "perDay": 200},
            "lapse": {"delays": [10], "leechAction": 0, "leechFails": 8, "minInt": 1, "mult": 0},
        }
    }
    conf = {"nextPos": 1, "estTimes": True, "activeDecks": [deck_id], "sortType": "noteFld", "timeLim": 0}
    db.execute(
        "INSERT INTO col VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (1, now, now, now * 1000, 11, 0, -1, 0, json_dumps(conf), json_dumps(model), json_dumps(decks), json_dumps(dconf), "{}"),
    )


def make_back_html(answer: str, hook: str, symbol_filename: str, full_filename: str) -> str:
    return (
        '<div class="answer">Answer: '
        + html.escape(answer)
        + "</div>"
        + '<div class="hook"><b>Sketch memory hook:</b> '
        + html.escape(hook)
        + "</div><br>"
        + f'<img class="symbol" src="{html.escape(symbol_filename)}"><br><br>'
        + '<div><b>Full sketch:</b></div>'
        + f'<img class="full-sketch" src="{html.escape(full_filename)}">'
    )


def build_apkg(deck_name: str, tags: str, full_image: str, cards: Iterable[Dict[str, str]]) -> bytes:
    deck_id = random.randint(10**12, 10**13 - 1)
    model_id = random.randint(10**12, 10**13 - 1)
    now = int(time.time())
    tag_text = " ".join(safe_filename(t, "") for t in tags.split() if t.strip())

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "collection.anki2"
        db = sqlite3.connect(db_path)
        try:
            create_schema(db)
            insert_collection_metadata(db, deck_name, deck_id, model_id)

            media_map: Dict[str, str] = {}
            media_files: List[Tuple[str, bytes]] = []
            full_filename = "full_sketch.png"
            media_map["0"] = full_filename
            media_files.append(("0", data_url_to_bytes(full_image)))

            due = 1
            for index, card in enumerate(cards, start=1):
                symbol = str(card.get("symbol", f"symbol_{index}"))
                number = str(card.get("number", index))
                front = str(card.get("front", "")).strip()
                answer = str(card.get("answer", "")).strip()
                hook = str(card.get("hook", "")).strip()
                if not front or not answer:
                    raise ValueError(f"Card {number} is missing a front or answer.")

                symbol_filename = f"symbol_{number}_{safe_filename(symbol.lower(), 'symbol')}.png"
                media_index = str(index)
                media_map[media_index] = symbol_filename
                media_files.append((media_index, data_url_to_bytes(str(card.get("symbolImage", "")))))

                back = make_back_html(answer, hook, symbol_filename, full_filename)
                note_id = anki_id() + index
                card_id = note_id + 100000
                fields = front + "\x1f" + back
                db.execute(
                    "INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        note_id,
                        hashlib.sha1(f"{deck_name}:{number}:{front}".encode("utf-8")).hexdigest()[:10],
                        model_id,
                        now,
                        -1,
                        f" {tag_text} " if tag_text else " ",
                        fields,
                        front,
                        field_checksum(front),
                        0,
                        "",
                    ),
                )
                db.execute(
                    "INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (card_id, note_id, deck_id, 0, now, -1, 0, 0, due, 0, 0, 0, 0, 0, 0, 0, 0, ""),
                )
                due += 1
            db.commit()
        finally:
            db.close()

        apkg_path = temp_path / "deck.apkg"
        with zipfile.ZipFile(apkg_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(db_path, "collection.anki2")
            zf.writestr("media", json_dumps(media_map))
            for media_index, media_bytes in media_files:
                zf.writestr(media_index, media_bytes)
        return apkg_path.read_bytes()


class SketchyAnkiHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path != "/":
            self.send_error(404)
            return
        body = HTML_PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/build":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            deck_name = str(payload.get("deckName", "Sketchy Symbols")).strip() or "Sketchy Symbols"
            apkg = build_apkg(
                deck_name=deck_name,
                tags=str(payload.get("tags", "")),
                full_image=str(payload["fullImage"]),
                cards=payload.get("cards", []),
            )
        except Exception as exc:
            message = f"Could not build deck: {exc}".encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)
            return

        filename = safe_filename(deck_name.lower(), "sketchy_deck") + ".apkg"
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(apkg)))
        self.end_headers()
        self.wfile.write(apkg)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Sketchy-symbols-to-Anki web app.")
    parser.add_argument("--host", default=os.environ.get("SKETCHY_ANKI_HOST", APP_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("SKETCHY_ANKI_PORT", APP_PORT)))
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), SketchyAnkiHandler)
    print(f"Sketchy Symbols to Anki is running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
