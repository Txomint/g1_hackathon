"""
Frame sources.  ── FROZEN FILE, DO NOT EDIT ──

Three ways to get pictures into the program, all behind the same tiny
interface:

    LaptopCamera   cv2.VideoCapture on a local webcam            (default)
    RobotCamera    the G1's own head camera, over the Unitree SDK (--robot)
    ImageFolder    a still image or a folder of them             (--image PATH)

`read()` returns (ok, frame) with frame in BGR, or (False, None) when the
source is finished or stalled.
"""
from __future__ import annotations

import os
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np

_FETCHER = Path(__file__).resolve().parent / "_video_fetcher.py"
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class FrameSource:
    name = "source"

    def read(self) -> tuple[bool, np.ndarray | None]:
        raise NotImplementedError

    def release(self) -> None:
        pass


class LaptopCamera(FrameSource):
    name = "laptop camera"

    def __init__(self, index: int = 0, width: int = 1280, height: int = 720) -> None:
        self._cap = cv2.VideoCapture(index)
        if not self._cap.isOpened():
            raise SystemExit(
                f"Could not open camera index {index}. "
                "Try a different --camera index, or close whatever else is using it."
            )
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def read(self):
        return self._cap.read()

    def release(self) -> None:
        self._cap.release()


class RobotCamera(FrameSource):
    """The G1's head camera.

    The Unitree SDK's VideoClient runs in a separate process (_video_fetcher.py)
    that streams length-prefixed JPEG over a pipe.  That isolation is inherited
    from g1_control/camera/video_bridge.py: it keeps the camera's DDS runtime
    out of the process that is driving the robot.

    Expect roughly 4-10 fps and a wide, low-mounted viewpoint — nothing like a
    laptop webcam.  Gestures tuned only against a laptop will need work here.
    """

    name = "robot camera"

    def __init__(self, iface: str, first_frame_timeout: float = 15.0) -> None:
        env = os.environ.copy()
        env.pop("RMW_IMPLEMENTATION", None)
        self._proc = subprocess.Popen(
            [sys.executable, str(_FETCHER), iface],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        self._latest: np.ndarray | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

        print(f"[camera] waiting for the robot camera on {iface} ...", flush=True)
        deadline = time.monotonic() + first_frame_timeout
        while time.monotonic() < deadline:
            with self._lock:
                if self._latest is not None:
                    print("[camera] robot camera streaming", flush=True)
                    return
            if self._proc.poll() is not None:
                break
            time.sleep(0.1)
        self.release()
        raise SystemExit(
            "No frames from the robot camera.\n"
            "  - is the Ethernet cable connected and --iface correct?\n"
            "  - is the robot powered on?\n"
            "Run with --local-camera to drive the robot from the laptop webcam instead."
        )

    def _read_loop(self) -> None:
        pipe = self._proc.stdout
        while not self._stop.is_set():
            header = self._read_exact(pipe, 4)
            if header is None:
                break
            length = struct.unpack(">I", header)[0]
            if length == 0 or length > 10_000_000:
                continue
            jpeg = self._read_exact(pipe, length)
            if jpeg is None:
                break
            frame = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                with self._lock:
                    self._latest = frame

    @staticmethod
    def _read_exact(pipe, n: int) -> bytes | None:
        buf = b""
        while len(buf) < n:
            chunk = pipe.read(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf

    def read(self):
        with self._lock:
            frame = self._latest
        if frame is None:
            return False, None
        return True, frame.copy()

    def release(self) -> None:
        self._stop.set()
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._proc.kill()


class ImageFolder(FrameSource):
    """A still image, or every image in a folder.

    The same frame is returned over and over, so the recognizer sees it as a
    held pose.  `n` / `p` in the preview window step through a folder.
    """

    name = "image"

    def __init__(self, path: str | Path) -> None:
        path = Path(path).expanduser()
        if path.is_dir():
            self.paths = sorted(
                p for p in path.iterdir() if p.suffix.lower() in _IMAGE_SUFFIXES
            )
            if not self.paths:
                raise SystemExit(f"No images found in {path}")
        elif path.is_file():
            self.paths = [path]
        else:
            raise SystemExit(f"No such file or folder: {path}")
        self._i = 0
        self._frame: np.ndarray | None = None
        self._load()

    def _load(self) -> None:
        frame = cv2.imread(str(self.current))
        if frame is None:
            raise SystemExit(f"Could not decode image: {self.current}")
        self._frame = frame

    @property
    def current(self) -> Path:
        return self.paths[self._i]

    @property
    def position(self) -> str:
        return f"{self._i + 1}/{len(self.paths)}  {self.current.name}"

    def step(self, delta: int) -> None:
        self._i = (self._i + delta) % len(self.paths)
        self._load()

    def read(self):
        return True, self._frame.copy()
