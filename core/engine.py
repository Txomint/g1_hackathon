"""
The main loop.  ── FROZEN FILE, DO NOT EDIT ──

Reads frames, runs the hand tracker, asks your recognizer for an action, lets
the safety layer review it, sends it to the robot (or not), and draws the
preview.  Also owns the keyboard.
"""
from __future__ import annotations

import importlib
import time
import traceback
from datetime import datetime
from pathlib import Path

import cv2

from . import hud
from .actions import NONE, STOP, Action
from .camera import FrameSource, ImageFolder
from .hand_tracker import HandTracker
from .robot import G1Driver, NullRobot
from .safety import SafetyGovernor

CAPTURE_DIR = Path(__file__).resolve().parents[1] / "captures"

KEY_HELP = "q quit   SPACE arm/disarm   e stop   s snapshot   r reload gestures   n/p image"


def load_recognizer(module_name: str):
    """Import `module_name` and instantiate its GestureRecognizer."""
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise SystemExit(
            f"Could not import {module_name!r}: {exc}\n"
            "--impl takes either a module name (participant.gestures) or a path "
            "to a .py file (teams/red/gestures.py)."
        ) from None
    importlib.reload(module)
    if not hasattr(module, "GestureRecognizer"):
        raise SystemExit(
            f"{module_name} has no class named GestureRecognizer — "
            "the entry point is fixed, do not rename it."
        )
    return module.GestureRecognizer(), module


class Engine:
    def __init__(
        self,
        source: FrameSource,
        robot: NullRobot | G1Driver,
        impl: str = "participant.gestures",
        max_hands: int = 2,
        detect_hz: float = 20.0,
        mirror: bool = False,
        display: bool = True,
        static: bool = False,
        model_path: str | None = None,
    ) -> None:
        self.source = source
        self.robot = robot
        self.impl = impl
        self.mirror = mirror
        self.display = display
        self.period = 1.0 / max(detect_hz, 1.0)
        self.tracker = HandTracker(
            **({"model_path": model_path} if model_path else {}),
            max_hands=max_hands,
            static=static,
        )
        self.governor = SafetyGovernor(requires_arming=robot.connected)
        self.recognizer, _ = load_recognizer(impl)
        self._errors = 0
        self._fps = 0.0

    # ── recognizer call, isolated from the rest of the loop ───────────────────

    def _decide(self, obs) -> Action:
        try:
            action = self.recognizer.update(obs)
        except Exception:
            self._errors += 1
            if self._errors <= 3:
                traceback.print_exc()
                print(
                    f"[engine] {self.impl}.GestureRecognizer.update() raised — "
                    "treating this frame as NONE",
                    flush=True,
                )
            return NONE
        if action is None:
            return NONE
        if not isinstance(action, Action):
            self._errors += 1
            if self._errors <= 3:
                print(
                    f"[engine] update() returned {action!r}, which is not an Action. "
                    "Return one of the constants from core.actions, or custom_action().",
                    flush=True,
                )
            return NONE
        return action

    def _reload(self) -> None:
        self.governor.disarm()
        try:
            self.recognizer, _ = load_recognizer(self.impl)
            self._errors = 0
            print(f"[engine] reloaded {self.impl} (disarmed — press SPACE to re-arm)", flush=True)
        except Exception:
            traceback.print_exc()
            print("[engine] reload failed — keeping the previous recognizer", flush=True)

    def _snapshot(self, frame) -> None:
        CAPTURE_DIR.mkdir(exist_ok=True)
        path = CAPTURE_DIR / f"{datetime.now():%Y%m%d-%H%M%S-%f}.jpg"
        cv2.imwrite(str(path), frame)
        print(f"[engine] saved {path}", flush=True)

    # ── the loop ──────────────────────────────────────────────────────────────

    def run(self) -> None:
        t0 = time.monotonic()
        last_t = 0.0
        no_frame_since = None
        window = "G1 gesture control"

        while True:
            loop_start = time.monotonic()
            ok, frame = self.source.read()
            now = loop_start - t0

            if not ok or frame is None:
                if no_frame_since is None:
                    no_frame_since = now
                elif now - no_frame_since > 5.0:
                    print("[engine] no frames for 5 s — giving up", flush=True)
                    break
                effective, reason = self.governor.review(NONE, now)
                self.robot.apply(effective)
                if self._wait(loop_start, window, None):
                    break
                continue
            no_frame_since = None

            if self.mirror:
                frame = cv2.flip(frame, 1)

            dt = now - last_t
            last_t = now
            obs = self.tracker.observe(frame, now, dt)
            self.governor.note_frame(now, bool(obs.hands))

            requested = self._decide(obs)
            effective, reason = self.governor.review(requested, now)
            self.robot.apply(effective)

            if dt > 0:
                self._fps = 0.8 * self._fps + 0.2 / dt

            if self.display:
                self._render(window, frame, obs, requested, effective, reason)
            if self._wait(loop_start, window, frame):
                break

    def _render(self, window, frame, obs, requested, effective, reason) -> None:
        hud.draw_skeleton(frame, obs)
        hud.draw_hand_readouts(frame, obs)

        if self.robot.connected:
            armed = self.governor.armed
            mode = ("ROBOT LIVE — ARMED", (0, 0, 255)) if armed else ("ROBOT LIVE — disarmed", (0, 200, 255))
        else:
            mode = ("NO-ROBOT MODE (nothing will move)", (0, 220, 0))

        lines = [
            mode,
            (f"{self.source.name}   {self._fps:4.1f} fps   hands {len(obs.hands)}", (200, 200, 200)),
        ]
        if isinstance(self.source, ImageFolder):
            lines.append((f"image {self.source.position}", (200, 200, 120)))
        if self.mirror:
            lines.append(("--mirror on: left/right labels are flipped", (0, 165, 255)))
        hud.draw_status(frame, lines)
        hud.draw_decision(frame, requested, effective, reason)
        hud.draw_keys(frame, KEY_HELP)
        cv2.imshow(window, frame)

    def _wait(self, loop_start: float, window: str, frame) -> bool:
        """Pace the loop and handle keys.  Returns True when it is time to quit."""
        remaining = self.period - (time.monotonic() - loop_start)
        if not self.display:
            if remaining > 0:
                time.sleep(remaining)
            return False

        key = cv2.waitKey(max(1, int(remaining * 1000))) & 0xFF
        if key in (ord("q"), 27):
            return True
        if key == ord(" "):
            armed = self.governor.toggle_arm()
            print(f"[engine] {'ARMED' if armed else 'disarmed'}", flush=True)
        elif key == ord("e"):
            self.governor.disarm()
            self.robot.apply(STOP)
            print("[engine] emergency stop — disarmed", flush=True)
        elif key == ord("s") and frame is not None:
            self._snapshot(frame)
        elif key == ord("r"):
            self._reload()
        elif key in (ord("n"), ord("p")) and isinstance(self.source, ImageFolder):
            self.source.step(1 if key == ord("n") else -1)
        return False

    def close(self) -> None:
        self.robot.shutdown()
        self.tracker.close()
        self.source.release()
        if self.display:
            cv2.destroyAllWindows()
