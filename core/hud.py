"""
The preview window.  ── FROZEN FILE, DO NOT EDIT ──

Draws the skeleton, the per-finger numbers your recognizer is reading, and the
action it decided on.  If the safety layer overruled that decision, both are
shown: what you asked for, and what the robot was actually given.
"""
from __future__ import annotations

import cv2
import numpy as np

from .actions import Action
from .observation import CHAINS, FINGERS, Observation

_FONT = cv2.FONT_HERSHEY_SIMPLEX
_SIDE_COLOR = {"left": (255, 120, 0), "right": (0, 120, 255), "unknown": (160, 160, 160)}
_KEYS_STRIP = 24   # height of the key-help strip along the bottom


def _text(img, s, org, scale=0.55, color=(235, 235, 235), thick=1):
    cv2.putText(img, s, org, _FONT, scale, (0, 0, 0), thick + 2, cv2.LINE_AA)
    cv2.putText(img, s, org, _FONT, scale, color, thick, cv2.LINE_AA)


def _panel(img, x, y, w, h, alpha=0.45):
    x2, y2 = min(x + w, img.shape[1]), min(y + h, img.shape[0])
    if x2 <= x or y2 <= y:
        return
    roi = img[y:y2, x:x2]
    cv2.addWeighted(np.zeros_like(roi), alpha, roi, 1 - alpha, 0, roi)


def draw_skeleton(img, obs: Observation) -> None:
    for hand in obs.hands:
        color = _SIDE_COLOR.get(hand.side, (160, 160, 160))
        for chain in CHAINS:
            for a, b in zip(chain, chain[1:]):
                cv2.line(img, hand.px[a], hand.px[b], color, 2, cv2.LINE_AA)
        for f in FINGERS:
            tip = hand.px[{"thumb": 4, "index": 8, "middle": 12, "ring": 16, "pinky": 20}[f]]
            up = hand.extended.get(f, False)
            cv2.circle(img, tip, 7, (0, 230, 0) if up else (0, 0, 230), cv2.FILLED)
        for p in hand.px:
            cv2.circle(img, p, 2, (240, 240, 240), cv2.FILLED)
        x1, y1, x2, y2 = hand.bbox
        cv2.rectangle(img, (x1 - 8, y1 - 8), (x2 + 8, y2 + 8), color, 1)
        _text(img, f"{hand.side} {hand.score:.2f}", (x1 - 8, y1 - 14), 0.5, color)


def draw_hand_readouts(img, obs: Observation) -> None:
    """Per-hand finger table — the raw numbers the recognizer is working from."""
    if not obs.hands:
        return
    w = 250
    x = img.shape[1] - w - 10
    y = 16
    panel_h = 26 + 22 * len(FINGERS) + 28
    for hand in obs.hands[:2]:
        _panel(img, x - 10, y - 4, w, panel_h)
        color = _SIDE_COLOR.get(hand.side, (160, 160, 160))
        _text(img, f"{hand.side.upper()}  scale {hand.scale:.2f}  p {hand.score:.2f}",
              (x, y + 14), 0.5, color)
        y += 26
        for f in FINGERS:
            up = hand.extended.get(f, False)
            _text(
                img,
                f"{f:<7}{hand.curl[f]:6.1f}deg  {'UP' if up else '--'}",
                (x, y + 14),
                0.5,
                (0, 230, 0) if up else (150, 150, 150),
            )
            y += 22
        up_list = " ".join(f[:3] for f in hand.fingers_up()) or "-"
        _text(img, f"up: {up_list}", (x, y + 14), 0.5)
        y += 28 + 10


def draw_decision(img, requested: Action, effective: Action, reason: str) -> None:
    h = img.shape[0] - _KEYS_STRIP      # sit above the key-help strip
    _panel(img, 0, h - 118, 520, 118, 0.55)
    _text(img, "gesture says", (16, h - 92), 0.5, (170, 170, 170))
    _text(img, requested.name, (16, h - 58), 1.15, requested.color, 2)

    if reason:
        _text(img, f"overruled: {reason}", (16, h - 26), 0.6, (0, 165, 255))
    else:
        _text(
            img,
            f"vx {effective.vx:+.2f}  vy {effective.vy:+.2f}  wz {effective.wz:+.2f}",
            (16, h - 26),
            0.6,
            (200, 200, 200),
        )


def draw_status(img, lines: list[tuple[str, tuple[int, int, int]]]) -> None:
    _panel(img, 0, 0, 430, 26 * len(lines) + 12)
    y = 26
    for text, color in lines:
        _text(img, text, (16, y), 0.6, color)
        y += 26


def draw_keys(img, keys: str) -> None:
    h = img.shape[0]
    _panel(img, 0, h - _KEYS_STRIP, img.shape[1], _KEYS_STRIP, 0.6)
    _text(img, keys, (16, h - 8), 0.45, (170, 170, 170))
