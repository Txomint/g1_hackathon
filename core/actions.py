"""
The robot's command vocabulary.  ── FROZEN FILE, DO NOT EDIT ──

An Action is a *named velocity command*.  The gesture recognizer in
`participant/gestures.py` returns one of these every frame; the rest of the
program turns it into either a line of text on the screen (no-robot mode) or
a real velocity command to the G1 (robot mode).

The seven built-in actions below are the official vocabulary of the hackathon
and their names are what the scoreboard checks for.  Do not rename them and
do not change their velocities.

If you invent a gesture that needs a motion nobody listed here, build it with
`custom_action()` (see the bottom of this file) — it goes through exactly the
same safety clamp as the built-ins.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ── Speed limits ──────────────────────────────────────────────────────────────
# Matched to the tested limits in g1_control/rnd_walk.py.  core/safety.py
# re-clamps every command to these numbers right before it reaches the robot,
# so raising them here does not make the robot go faster.
VX_MAX = 0.40   # m/s   forward (+) / backward (-)
VY_MAX = 0.25   # m/s   strafe left (+) / right (-)
WZ_MAX = 0.50   # rad/s turn left (+) / right (-)


@dataclass(frozen=True)
class Action:
    """One command the robot can be asked to perform.

    vx  forward  (+) / backward (-)   in m/s
    vy  left     (+) / right    (-)   in m/s   (sideways step, body stays facing forward)
    wz  turn left(+) / turn right(-)  in rad/s
    """
    name: str
    vx: float = 0.0
    vy: float = 0.0
    wz: float = 0.0
    color: tuple[int, int, int] = field(default=(255, 255, 255))  # BGR, for the HUD

    @property
    def is_idle(self) -> bool:
        return self.vx == 0.0 and self.vy == 0.0 and self.wz == 0.0

    def __str__(self) -> str:
        return self.name


# ── The official vocabulary ───────────────────────────────────────────────────
# NONE means "I could not read the operator" — it is what you return when you
# do not know.  It is not the same as STOP: STOP is a decision, NONE is the
# absence of one.  Both leave the robot standing still, but the HUD shows them
# differently and the test suite scores them differently.
NONE = Action("NONE", color=(150, 150, 150))

STOP = Action("STOP", color=(0, 0, 255))
FORWARD = Action("FORWARD", vx=+VX_MAX, color=(0, 220, 0))
BACKWARD = Action("BACKWARD", vx=-0.25, color=(0, 180, 220))
LEFT = Action("LEFT", vy=+VY_MAX, color=(255, 180, 0))
RIGHT = Action("RIGHT", vy=-VY_MAX, color=(255, 0, 180))
ROTATE_LEFT = Action("ROTATE_LEFT", wz=+WZ_MAX, color=(0, 255, 255))
ROTATE_RIGHT = Action("ROTATE_RIGHT", wz=-WZ_MAX, color=(180, 100, 255))

BUILTIN: dict[str, Action] = {
    a.name: a
    for a in (NONE, STOP, FORWARD, BACKWARD, LEFT, RIGHT, ROTATE_LEFT, ROTATE_RIGHT)
}


def custom_action(
    name: str,
    vx: float = 0.0,
    vy: float = 0.0,
    wz: float = 0.0,
    color: tuple[int, int, int] = (255, 255, 0),
) -> Action:
    """Build your own action for a gesture that the vocabulary above misses.

    Velocities are clamped to the global limits immediately, so you cannot use
    this to make the robot move faster than the built-ins.

        SHUFFLE = custom_action("DIAGONAL_LEFT", vx=0.2, vy=0.15)
    """
    if name in BUILTIN:
        raise ValueError(
            f"{name!r} is a built-in action — use actions.{name} instead of redefining it"
        )
    return Action(
        name=name.upper(),
        vx=max(-VX_MAX, min(VX_MAX, float(vx))),
        vy=max(-VY_MAX, min(VY_MAX, float(vy))),
        wz=max(-WZ_MAX, min(WZ_MAX, float(wz))),
        color=color,
    )
