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
    custom_action(name, vx=, vy=, wz=)  -> your own invention

NONE and STOP both leave the robot standing still, and they are not the same
thing.  STOP means you recognised the stop gesture.  NONE means you recognised
nothing.  The test suite scores them separately, so returning STOP when you are
merely confused will cost you.
"""
from __future__ import annotations

from core.actions import (  # noqa: F401  (imported for you to use)
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


# ── Gesture table ─────────────────────────────────────────────────────────────
# The two gestures the hackathon starts with.  Everything else is up to you.
#
# Add your gestures here, or throw this table away and recognise poses some
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
#   ... plus at least one of your own that is not in the list above.
#
# TODO phase 1 — robustness.  Look at what the baseline actually does before
# you add to it.  It decides from one frame, with no memory of the frame
# before; it trusts `hand.extended` without ever looking at how marginal the
# call was; and every pose that is not exactly one of two entries in a lookup
# table comes out as NONE, including the poses that are nearly one of them.
# In phase 2 another team will go looking for what follows from that.  Get
# there first.


class GestureRecognizer:
    """Turns hand observations into robot actions.

    KEEP the class name and the signature of `update`. The rest is yours.
    """

    def __init__(self) -> None:
        # Per-run state goes here. `update` is called once per frame on the same
        # instance, so anything you store survives to the next frame — which is
        # how you would remember what the last few frames looked like.
        self.last_action: Action = NONE

    def update(self, obs: Observation) -> Action:
        """Called once per camera frame. Return the action the robot should do.

        KEEP this signature. Replace the body with whatever you like.
        """
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
