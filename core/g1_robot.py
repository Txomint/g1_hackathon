"""
Unitree SDK LocoClient wrapper.  ── FROZEN FILE, DO NOT EDIT ──

Copied unchanged from g1_control/unitree_python.py.  The g1_control README
documents every method here, the FSM table, and the upstream SDK bugs this
wrapper works around.
"""
import json

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.g1.loco.g1_loco_api import (
    ROBOT_API_ID_LOCO_GET_FSM_ID,
    ROBOT_API_ID_LOCO_GET_FSM_MODE,
    ROBOT_API_ID_LOCO_GET_BALANCE_MODE,
    ROBOT_API_ID_LOCO_GET_SWING_HEIGHT,
    ROBOT_API_ID_LOCO_GET_STAND_HEIGHT,
    ROBOT_API_ID_LOCO_SET_SWING_HEIGHT,
)

_G1_FSM_STAND_UP = 4
_G1_FSM_RUN      = 801


class G1Robot:
    def __init__(self, interface: str, robot_ip: str = "192.168.123.161"):
        ChannelFactoryInitialize(0, interface)
        self._client = LocoClient()
        self._client.SetTimeout(10.0)
        self._client.Init()

    def _get(self, api_id: int, default=-1):
        code, data = self._client._Call(api_id, "{}")
        if code != 0 or data is None:
            return default
        try:
            return json.loads(data).get("data", default)
        except (json.JSONDecodeError, AttributeError):
            return default

    def fsm_id(self) -> int:
        return self._get(ROBOT_API_ID_LOCO_GET_FSM_ID)

    def fsm_mode(self) -> int:
        return self._get(ROBOT_API_ID_LOCO_GET_FSM_MODE)

    def get_balance_mode(self) -> int:
        return self._get(ROBOT_API_ID_LOCO_GET_BALANCE_MODE)

    def get_swing_height(self) -> float:
        return self._get(ROBOT_API_ID_LOCO_GET_SWING_HEIGHT, default=-1.0)

    def set_swing_height(self, height: float):
        code, _ = self._client._Call(ROBOT_API_ID_LOCO_SET_SWING_HEIGHT, json.dumps({"data": height}))
        return code

    def get_stand_height(self) -> float:
        return self._get(ROBOT_API_ID_LOCO_GET_STAND_HEIGHT, default=-1.0)

    def damp(self):
        return self._client.Damp()

    def stand_up(self):
        return self._client.SetFsmId(_G1_FSM_STAND_UP)

    def squat2standup(self):
        return self._client.Squat2StandUp()

    def set_stand_height(self, height: float):
        return self._client.SetStandHeight(height)

    def balance_stand(self, mode: int = 0):
        return self._client.BalanceStand(mode)

    def set_continuous_gait(self, enabled: bool):
        return self._client.SetBalanceMode(1 if enabled else 0)

    def continuous_gait(self, enabled: bool):
        return self.set_continuous_gait(enabled)

    def start(self):
        return self._client.SetFsmId(200)

    def run(self):
        return self._client.SetFsmId(_G1_FSM_RUN)

    def set_velocity(self, vx: float, vy: float, omega: float, duration: float = 1.0):
        return self._client.SetVelocity(vx, vy, omega, duration)

    def move(self, vx: float, vy: float, omega: float, continuous: bool = False):
        return self._client.Move(vx, vy, omega, continous_move=continuous)

    def stop(self):
        return self._client.StopMove()
