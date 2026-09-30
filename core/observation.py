"""
What your recognizer sees.  ── FROZEN FILE, DO NOT EDIT ──

One `Observation` is produced per camera frame and handed to
`GestureRecognizer.update()`.  It holds zero or more `Hand` objects: none when
no hand is visible, and up to `--max-hands` when several are.

Everything here is *derived from the camera*, so everything here can be wrong.
That is the point of the testing phase.
"""
from __future__ import annotations

from dataclasses import dataclass, field

FINGERS = ("thumb", "index", "middle", "ring", "pinky")

# MediaPipe hand landmark indices, 21 per hand.  Use these to index Hand.lm /
# Hand.px instead of writing magic numbers:
#     tip_of_index = hand.px[INDEX[3]]
WRIST = 0
THUMB = (1, 2, 3, 4)      # CMC, MCP, IP,  TIP
INDEX = (5, 6, 7, 8)      # MCP, PIP, DIP, TIP
MIDDLE = (9, 10, 11, 12)
RING = (13, 14, 15, 16)
PINKY = (17, 18, 19, 20)

FINGER_LANDMARKS: dict[str, tuple[int, int, int, int]] = {
    "thumb": THUMB,
    "index": INDEX,
    "middle": MIDDLE,
    "ring": RING,
    "pinky": PINKY,
}

# Bone chains, for drawing.
CHAINS = (
    (WRIST, *THUMB),
    (WRIST, *INDEX),
    (WRIST, *MIDDLE),
    (WRIST, *RING),
    (WRIST, *PINKY),
    (INDEX[0], MIDDLE[0], RING[0], PINKY[0]),   # the knuckle line
)


@dataclass(frozen=True)
class Hand:
    """One detected hand."""

    side: str
    """"left" or "right", as MediaPipe labels it.

    This is the label for an *unmirrored* camera image.  The preview window is
    mirrored so it feels like a mirror to the operator, which means the hand
    drawn on the left of the screen is usually labelled "right".  Whether
    MediaPipe's idea of left and right matches the operator's is something you
    should check yourself rather than trust.
    """

    score: float
    """MediaPipe's own confidence in this detection, 0..1."""

    curl: dict[str, float]
    """How bent each finger is, in degrees.  0 = perfectly straight.

    Roughly 0-30 for an extended finger and 120-180 for one folded into the
    palm, but the boundary moves with hand orientation, camera distance and
    especially for the thumb.  Computed from MediaPipe's metric world
    landmarks, so it does not change when the hand moves closer or further
    away — only its reliability does.
    """

    extended: dict[str, bool]
    """`curl` thresholded at the defaults in core/hand_tracker.py.

    A convenience, not a ground truth.  If it disagrees with what you see, read
    `curl` and threshold it yourself — that is a legitimate and expected fix.
    """

    lm: list[tuple[float, float, float]]
    """21 normalised image-space landmarks, x and y in 0..1, z relative depth."""

    world: list[tuple[float, float, float]]
    """21 landmarks in metres, origin at the hand's geometric centre.

    Scale-invariant: use these for angles and shapes.  Use `lm` / `px` for
    anything about *where in the frame* the hand is.
    """

    px: list[tuple[int, int]]
    """21 landmarks in pixels, for drawing and for pixel-distance tests."""

    bbox: tuple[int, int, int, int]
    """(x1, y1, x2, y2) pixel bounding box around the 21 landmarks."""

    scale: float
    """Bounding-box diagonal as a fraction of the frame diagonal, 0..1.

    A crude proxy for how close the hand is to the camera: ~0.35 at arm's
    length from a laptop webcam, under 0.10 from across a room.
    """

    def fingers_up(self) -> list[str]:
        """Names of the fingers currently counted as extended."""
        return [f for f in FINGERS if self.extended.get(f)]

    def count_up(self) -> int:
        return sum(1 for f in FINGERS if self.extended.get(f))

    def center(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.bbox
        return (x1 + x2) // 2, (y1 + y2) // 2


@dataclass(frozen=True)
class Observation:
    """Everything known about one camera frame."""

    hands: list[Hand] = field(default_factory=list)
    """Detected hands, ordered largest-first — so `hands[0]` is usually the
    closest hand, but "usually" is doing a lot of work in that sentence.
    May be empty.  May hold more than one entry."""

    t: float = 0.0
    """Seconds since the program started.  Use differences of this, not
    wall-clock time, if you want to reason about how long a gesture has been
    held."""

    dt: float = 0.0
    """Seconds since the previous frame.  Varies: expect ~0.05 s on a laptop
    webcam and ~0.25 s or worse on the robot's camera."""

    width: int = 0
    height: int = 0

    def hand(self, side: str) -> Hand | None:
        """The detected hand on the given side, or None."""
        for h in self.hands:
            if h.side == side:
                return h
        return None

    @property
    def any_hand(self) -> Hand | None:
        """The largest detected hand, or None if the frame has no hands."""
        return self.hands[0] if self.hands else None
