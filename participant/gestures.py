"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  THIS IS YOUR FILE.  Everything you write for phase 1 goes in here.          ║
╚══════════════════════════════════════════════════════════════════════════════╝

You get one `Observation` per camera frame and you return one `Action`.  That is
the whole interface.  Nothing else in the repository needs to change — and
nothing else in the repository *may* change: `core/` is frozen and the judges
run your work against a clean copy of it.

Two rules you must not break:

    1. the class is called `GestureRecognizer`
    2. it has a method `update(self, obs) -> Action`

Break either and the launcher will refuse to start.  Everything below those two
lines is yours: add methods, add constants, add whole modules next to this file
and import them.

What you are given, per frame (full details in core/observation.py):

    obs.hands          detected hands, largest first — may be empty, may be >1
    obs.any_hand       the largest hand, or None
    obs.hand("left")   a specific side, or None
    obs.t, obs.dt      seconds since start, seconds since the last frame
    obs.width/height   frame size in pixels
    obs.frame          the camera image itself, BGR numpy array (optional use,
                       see "Bring your own model" below)

    hand.extended      {"thumb": bool, "index": bool, ...}   convenience
    hand.curl          {"thumb": 12.4, "index": 151.0, ...}  degrees, 0 = straight
    hand.fingers_up()  ["index"]
    hand.count_up()    1
    hand.px            21 landmarks in pixels
    hand.world         21 landmarks in metres, scale-invariant
    hand.scale         hand size / frame size — a rough distance proxy
    hand.score         MediaPipe's confidence, 0..1
    hand.side          "left" / "right" — for an unmirrored image; verify it

What you may return (full list in core/actions.py):

    STOP  FORWARD  BACKWARD  LEFT  RIGHT  ROTATE_LEFT  ROTATE_RIGHT
    NONE                      -> "I cannot read the operator"
    your own actions          -> defined in this file, see "YOUR CUSTOM ACTIONS"
                                 below.  You never edit core/actions.py.

NONE and STOP both leave the robot standing still, and they are not the same
thing.  STOP means you recognised the stop gesture.  NONE means you recognised
nothing.  The test suite scores them separately, so returning STOP when you are
merely confused will cost you.
"""
from __future__ import annotations

from pathlib import Path  # noqa: F401  (for loading your own model's files)

import cv2  # noqa: F401
import numpy as np

from core.actions import (  # noqa: F401  (imported for you to use)
    BUILTIN,
    BACKWARD,
    FORWARD,
    LEFT,
    NONE,
    RIGHT,
    ROTATE_LEFT,
    ROTATE_RIGHT,
    STOP,
    Action,
    custom_action,
)
from core.observation import FINGERS, Hand, Observation  # noqa: F401


# ══════════════════════════════════════════════════════════════════════════════
#  EDIT FROM HERE
# ══════════════════════════════════════════════════════════════════════════════

# ── Tuning ────────────────────────────────────────────────────────────────────
# `hand.extended` is filled in by core/hand_tracker.py using a single fixed
# curl threshold for every finger.  It is a reasonable first guess and not much
# more.  When it starts disagreeing with what you see in the preview window,
# stop using it and threshold `hand.curl` yourself with numbers you picked —
# per finger if you need to.

MIN_SCORE = 0.5      # ignore hands MediaPipe is less sure about than this
MIN_SCALE = 0.05     # ignore hands smaller than this fraction of the frame


def is_up(hand: Hand, finger: str) -> bool:
    """Is one finger extended?

    Currently just forwards to the tracker's default. Replace the body with
    your own test — `hand.curl[finger]` is the raw signal, and
    `hand.world` / `hand.px` are there if an angle threshold is not enough.
    """
    return hand.extended.get(finger, False)


def pattern(hand: Hand) -> tuple[bool, bool, bool, bool, bool]:
    """(thumb, index, middle, ring, pinky) as five booleans."""
    return tuple(is_up(hand, f) for f in FINGERS)  # type: ignore[return-value]


# ══════════════════════════════════════════════════════════════════════════════
#  YOUR CUSTOM ACTIONS START HERE
# ══════════════════════════════════════════════════════════════════════════════
# The seven built-in actions are fixed.  When a gesture of yours needs a motion
# they do not cover, define a new action here, in this file.  Do NOT edit
# core/actions.py: it is frozen and the judges run a clean copy of it, so an
# action you add there disappears when you are judged.
#
# Build each one with `define_action(name, vx=, vy=, wz=, color=)`:
#
#     name   whatever you like; it is upper-cased.  It is what the preview window
#            shows, and the folder name the test suite expects for it
#            (testing/cases/DIAGONAL_LEFT/...).  Must be unique and must not
#            be a built-in name (STOP, FORWARD, ...).
#     vx     forward (+) / backward (-)       m/s    at most ±0.40
#     vy     step left (+) / step right (-)   m/s    at most ±0.25
#     wz     turn left (+) / turn right (-)   rad/s  at most ±0.50
#     color  BGR colour for the preview text  (optional)
#
# Anything faster than the limits is cut down to them, so a custom action
# cannot make the robot faster than the built-ins.  All-zero velocities are
# allowed: the robot holds still but the preview shows your action's name,
# which is handy for a gesture that only acknowledges the operator.
#
# Define as many as you like, one per line, then use them like any built-in:
# return them from update(), put them in GESTURES below, or map your own
# model's labels onto them.  Every one you define is also collected in
# CUSTOM_ACTIONS, keyed by name, so CUSTOM_ACTIONS["DIAGONAL_LEFT"] works too.
#
# Examples (uncomment, rename, or delete):
#
#   SLOW_FORWARD  = define_action("SLOW_FORWARD", vx=0.10, color=(0, 128, 0))
#   HELLO         = define_action("HELLO")          # stands still, shows HELLO

CUSTOM_ACTIONS: dict[str, Action] = {}


def define_action(
    name: str,
    vx: float = 0.0,
    vy: float = 0.0,
    wz: float = 0.0,
    color: tuple[int, int, int] = (255, 255, 0),
) -> Action:
    """Create a named custom action and record it in CUSTOM_ACTIONS."""
    key = name.strip().upper()
    if not key:
        raise ValueError("a custom action needs a name")
    if key in BUILTIN:
        raise ValueError(f"{key!r} is a built-in action — use {key} directly instead")
    if key in CUSTOM_ACTIONS:
        raise ValueError(f"custom action {key!r} is defined twice")
    action = custom_action(key, vx=vx, vy=vy, wz=wz, color=color)
    CUSTOM_ACTIONS[key] = action
    return action


# ── define your actions below this line ───────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
#  YOUR CUSTOM ACTIONS END HERE
# ══════════════════════════════════════════════════════════════════════════════


# ── Gesture table ─────────────────────────────────────────────────────────────
# The two gestures the hackathon starts with.  Everything else is up to you.
#
# Add your gestures here — custom actions included, e.g.
#     (True, True, False, False, False): DIAGONAL_LEFT,
# — or throw this table away and recognise poses some
# other way entirely — counting extended fingers is the obvious approach, not
# the only one.  Fingertip positions, the angle of the palm, the direction the
# hand is pointing and how all of those change over time are all in `obs`.
#
#                 thumb  index  middle  ring   pinky
GESTURES: dict[tuple[bool, bool, bool, bool, bool], Action] = {
    (True,  True,  True,  True,  True):  STOP,      # open palm, five fingers up
    (False, True,  False, False, False): FORWARD,   # index finger only
}

# TODO phase 1 — the gestures you owe us:
#   BACKWARD, LEFT, RIGHT, ROTATE_LEFT, ROTATE_RIGHT
#   ... You also might come up with new methods.
#
# TODO phase 1 — robustness.  Look at what the baseline actually does before
# you add to it.  It decides from one frame, with no memory of the frame
# before; it trusts `hand.extended` without ever looking at how marginal the
# call was; and every pose that is not exactly one of two entries in a lookup
# table comes out as NONE, including the poses that are nearly one of them.
# In phase 2 another team will go looking for what follows from that.  Get
# there first.


# ── OPTIONAL: bring your own model ────────────────────────────────────────────
# You do not have to use MediaPipe's landmarks as your only input.  Every
# observation also carries the raw camera image, so you can run a classifier of
# your own — on the whole frame, on a crop around the hand, on the landmarks as
# a feature vector, or on a history of any of those.
#
#     obs.frame                   BGR uint8 array, shape (obs.height, obs.width, 3)
#                                 (convert with cv2.cvtColor(..., cv2.COLOR_BGR2RGB)
#                                 if your model was trained on RGB)
#     hand_arrays(hand)           the 21 landmarks as numpy arrays, see below
#     crop_hand(obs.frame, hand)  the image patch around one hand
#
# Switch it on with USE_OWN_MODEL, then fill in OwnModel.  While it is off,
# nothing in this section runs.
#
# Things to know before you start:
#   - Speed.  update() runs inside the camera loop.  Every millisecond your
#     model takes is a millisecond of latency, and a slow model lowers the
#     frame rate.  Watch the fps readout in the preview window.
#   - The safety layer still uses MediaPipe.  The robot is stopped when
#     MediaPipe has seen no hand for 1.0 s, whatever your model thinks.
#   - Dependencies.  numpy and opencv are always there.  Anything else (torch,
#     onnxruntime, sklearn, ...) must be installed on the machine that runs
#     the robot and the judging, so agree it with the organisers early.
#   - Files.  Keep weights inside participant/ so they travel with your
#     submission, and load them relative to this file:
#         MODEL_DIR = Path(__file__).resolve().parent / "models"
#   - Pressing `r` in the preview window builds a new GestureRecognizer, so it
#     also reloads your model.

USE_OWN_MODEL = False


def hand_arrays(hand: Hand) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(px, lm, world) as numpy arrays of shape (21, 2), (21, 3), (21, 3).

    px     pixel coordinates in obs.frame
    lm     normalised image coordinates, x and y in 0..1, z relative depth
    world  metres, origin at the hand's centre, scale-invariant — usually the
           best starting point for a landmark classifier
    Index them with the constants in core/observation.py (WRIST, INDEX[3], ...).
    """
    return (
        np.asarray(hand.px, dtype=np.float32),
        np.asarray(hand.lm, dtype=np.float32),
        np.asarray(hand.world, dtype=np.float32),
    )


def crop_hand(frame: np.ndarray, hand: Hand, pad: float = 0.25) -> np.ndarray | None:
    """The square image patch around `hand`, padded by `pad` of its size.

    Returns None if the crop would be empty.  Resize it to whatever your model
    expects, e.g. cv2.resize(patch, (224, 224)).
    """
    x1, y1, x2, y2 = hand.bbox
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    half = max(x2 - x1, y2 - y1) * (1 + pad) / 2
    h, w = frame.shape[:2]
    x1, x2 = max(int(cx - half), 0), min(int(cx + half), w)
    y1, y2 = max(int(cy - half), 0), min(int(cy + half), h)
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2]


class OwnModel:
    """Your model.  Only built when USE_OWN_MODEL is True."""

    def __init__(self) -> None:
        # Load weights here, once — not in predict().
        pass

    def predict(self, obs: Observation) -> Action | None:
        """Return an Action, or None to fall back to the landmark rules below.

        Example shape of a crop classifier:

            if obs.frame is None or not obs.hands:
                return None
            patch = crop_hand(obs.frame, obs.hands[0])
            if patch is None:
                return None
            label = self.net(cv2.resize(patch, (224, 224)))   # your code
            return {"stop": STOP, "forward": FORWARD}.get(label)
            # or, if your model's labels are your custom action names:
            # return CUSTOM_ACTIONS.get(label.upper())
        """
        return None


class GestureRecognizer:
    """Turns hand observations into robot actions.

    KEEP the class name and the signature of `update`. The rest is yours.
    """

    def __init__(self) -> None:
        # Per-run state goes here. `update` is called once per frame on the same
        # instance, so anything you store survives to the next frame — which is
        # how you would remember what the last few frames looked like.
        self.last_action: Action = NONE
        self.own_model: OwnModel | None = OwnModel() if USE_OWN_MODEL else None

    def update(self, obs: Observation) -> Action:
        """Called once per camera frame. Return the action the robot should do.

        KEEP this signature. Replace the body with whatever you like.
        """
        if self.own_model is not None:
            action = self.own_model.predict(obs)
            if action is not None:
                self.last_action = action
                return action

        hand = self._pick_hand(obs)
        if hand is None:
            return NONE

        action = GESTURES.get(pattern(hand), NONE)
        self.last_action = action
        return action

    # ── your own helpers ──────────────────────────────────────────────────────

    def _pick_hand(self, obs: Observation) -> Hand | None:
        """Which hand is giving the orders?

        The largest hand that clears the confidence and size floors.  Naive on
        purpose — "largest" is a guess about intent, and `obs.hands` does not
        promise to contain only the hand you meant.
        """
        for hand in obs.hands:
            if hand.score >= MIN_SCORE and hand.scale >= MIN_SCALE:
                return hand
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  EDIT UNTIL HERE
# ══════════════════════════════════════════════════════════════════════════════
