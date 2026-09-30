"""
The robot driver.  ── FROZEN FILE, DO NOT EDIT ──

Two implementations of one interface:

    NullRobot   no-robot mode.  Accepts commands, moves nothing, remembers the
                last one so the HUD can show what would have happened.
    G1Driver    robot mode.  Stands the G1 up, enters FSM 801, and turns each
                Action into LocoClient.Move() / StopMove().

The stand-up sequence is the one from g1_control/rnd_walk.py: Damp (FSM 1) ->
StandUp (FSM 4) -> wait for mode 1 -> 0 -> Run (FSM 801).  FSM 801 is the entry
point for locomotion on this firmware, not FSM 200 — see the FSM table in the
g1_control README if you are curious why.
"""
from __future__ import annotations

import time

from .actions import STOP, Action

_RESEND_AFTER_S = 1.0   # re-send the current command at least this often


class NullRobot:
    connected = False
    label = "NO ROBOT"

    def __init__(self) -> None:
        self.last: Action = STOP

    def apply(self, action: Action) -> None:
        self.last = action

    def shutdown(self) -> None:
        self.last = STOP


class G1Driver:
    connected = True
    label = "ROBOT LIVE"

    def __init__(self, iface: str) -> None:
        from .g1_robot import G1Robot   # imported late: needs the Unitree SDK

        self._bot = G1Robot(interface=iface)
        self.last: Action = STOP
        self._sent: tuple[float, float, float] | None = None
        self._sent_t = 0.0
        self.startup_log: list[str] = []

    # ── startup ───────────────────────────────────────────────────────────────

    def stand_up(self) -> None:
        """Bring the robot from a squat to standing in run mode (FSM 801).

        Raises RuntimeError if either stage times out, so the caller can bail
        out before anything tries to move.
        """
        bot = self._bot

        def log(tag: str) -> None:
            time.sleep(0.25)
            line = f"{tag:<12} FSM {bot.fsm_id():3}  mode {bot.fsm_mode()}"
            self.startup_log.append(line)
            print(f"[robot] {line}", flush=True)

        bot.damp()
        log("DAMP")
        time.sleep(0.5)

        bot.stand_up()
        log("STAND_UP")

        # Skip the residual mode 0 that lingers for ~1 s after damp.
        time.sleep(1.0)
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline:
            time.sleep(0.5)
            if bot.fsm_id() == 4 and bot.fsm_mode() == 0:
                break
            print(f"[robot] waiting ... FSM {bot.fsm_id()} mode {bot.fsm_mode()}", flush=True)
        else:
            raise RuntimeError(
                "stand-up did not finish in 15 s — start the robot from a squat"
            )
        log("STANDING")

        bot.run()   # FSM 801
        log("RUN")
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if bot.fsm_id() == 801:
                return
            time.sleep(0.25)
        raise RuntimeError("FSM 801 not reached in 5 s — is the remote controller on?")

    # ── per-frame command ─────────────────────────────────────────────────────

    def apply(self, action: Action) -> None:
        self.last = action
        cmd = (round(action.vx, 3), round(action.vy, 3), round(action.wz, 3))
        now = time.monotonic()
        if cmd == self._sent and now - self._sent_t < _RESEND_AFTER_S:
            return
        if cmd == (0.0, 0.0, 0.0):
            self._bot.stop()
        else:
            self._bot.move(cmd[0], cmd[1], cmd[2], continuous=True)
        self._sent = cmd
        self._sent_t = now

    def fsm(self) -> tuple[int, int]:
        return self._bot.fsm_id(), self._bot.fsm_mode()

    def shutdown(self) -> None:
        """Stop moving.  The robot stays standing in FSM 801."""
        try:
            self._bot.stop()
        finally:
            self.last = STOP
            self._sent = (0.0, 0.0, 0.0)
