"""
The safety layer.  ── FROZEN FILE, DO NOT EDIT ──

Everything your recognizer returns passes through here before it can reach the
robot.  There is no flag to switch it off and no way to opt out of it from
`participant/gestures.py`.

What it guarantees:

  * velocities never exceed the limits in core/actions.py;
  * the robot is stopped whenever the program has gone blind — no camera frame
    for STALE_FRAME_S, or no hand detected anywhere in frame for NO_HAND_STOP_S;
  * in robot mode nothing moves until a human arms it from the keyboard, and
    one keypress disarms it again.

What it does NOT guarantee: that the action you chose was the right one.  If
your recognizer reads a coffee mug as FORWARD, this layer will happily clamp
that to 0.40 m/s and send it.  Deciding *correctly* is your job; that is what
phase 1 is for and what phase 2 attacks.
"""
from __future__ import annotations

from dataclasses import replace

from .actions import NONE, STOP, VX_MAX, VY_MAX, WZ_MAX, Action

STALE_FRAME_S = 0.8
"""Stop if no camera frame has arrived for this long."""

NO_HAND_STOP_S = 1.0
"""Stop if no hand has been detected for this long, whatever was last commanded.

This is why a gesture cannot 'latch': walk out of frame and the robot stops on
its own within a second.  It is a floor, not a substitute for your own logic —
it says nothing about the case where a hand *is* visible and is misread.
"""


def clamp(action: Action) -> Action:
    """Re-apply the global speed limits to any action, built-in or custom."""
    return replace(
        action,
        vx=max(-VX_MAX, min(VX_MAX, action.vx)),
        vy=max(-VY_MAX, min(VY_MAX, action.vy)),
        wz=max(-WZ_MAX, min(WZ_MAX, action.wz)),
    )


class SafetyGovernor:
    def __init__(self, requires_arming: bool) -> None:
        self.requires_arming = requires_arming
        self.armed = not requires_arming
        self._last_frame_t = 0.0
        self._last_hand_t = 0.0
        self._started = False

    # ── keyboard hooks ────────────────────────────────────────────────────────

    def toggle_arm(self) -> bool:
        if self.requires_arming:
            self.armed = not self.armed
        return self.armed

    def disarm(self) -> None:
        if self.requires_arming:
            self.armed = False

    # ── per-frame bookkeeping ─────────────────────────────────────────────────

    def note_frame(self, t: float, hands_present: bool) -> None:
        self._started = True
        self._last_frame_t = t
        if hands_present:
            self._last_hand_t = t

    def review(self, requested: Action, t: float) -> tuple[Action, str]:
        """Return the action that may actually be sent, plus why it was changed.

        The reason is "" when `requested` passed through untouched.
        """
        if not self._started:
            return STOP, "STARTING UP"
        if self.requires_arming and not self.armed:
            return STOP, "DISARMED"
        if t - self._last_frame_t > STALE_FRAME_S:
            return STOP, "NO CAMERA"
        if t - self._last_hand_t > NO_HAND_STOP_S:
            return STOP, "NO HAND"
        if requested is NONE or requested.name == "NONE":
            return STOP, ""
        return clamp(requested), ""
