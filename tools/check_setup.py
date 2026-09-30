#!/usr/bin/env python3.10
"""Check that this machine can run the hackathon code. Run this first.

    python3.10 tools/check_setup.py            # no-robot mode only
    python3.10 tools/check_setup.py --robot    # also check the robot toolchain
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PASS, FAIL, WARN = "  ok  ", " FAIL ", " warn "
problems = 0


def check(label: str, fn, fatal: bool = True) -> None:
    global problems
    try:
        detail = fn() or ""
        print(f"[{PASS}] {label} {detail}")
    except Exception as exc:
        print(f"[{FAIL if fatal else WARN}] {label} — {exc}")
        if fatal:
            problems += 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--robot", action="store_true", help="also check the Unitree SDK")
    ap.add_argument("--camera", type=int, default=0)
    args = ap.parse_args()

    def python_version():
        if sys.version_info < (3, 10):
            raise RuntimeError(f"need 3.10+, found {sys.version.split()[0]}")
        return sys.version.split()[0]

    def import_cv2():
        import cv2
        return cv2.__version__

    def import_mediapipe():
        import mediapipe
        return mediapipe.__version__

    def model_present():
        p = ROOT / "models" / "hand_landmarker.task"
        if not p.is_file():
            raise RuntimeError(
                f"{p} missing — wget it from "
                "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
                "hand_landmarker/float16/latest/hand_landmarker.task"
            )
        return f"{p.stat().st_size / 1e6:.1f} MB"

    def tracker_builds():
        from core.hand_tracker import HandTracker
        HandTracker(static=True).close()
        return ""

    def recognizer_loads():
        from core.engine import load_recognizer
        rec, _ = load_recognizer("participant.gestures")
        if not callable(getattr(rec, "update", None)):
            raise RuntimeError("GestureRecognizer has no update() method")
        return "participant.gestures"

    def camera_opens():
        import cv2
        cap = cv2.VideoCapture(args.camera)
        try:
            if not cap.isOpened():
                raise RuntimeError(f"camera index {args.camera} would not open")
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("camera opened but returned no frame")
            return f"{frame.shape[1]}x{frame.shape[0]}"
        finally:
            cap.release()

    def display_available():
        import cv2
        import numpy as np
        cv2.imshow("check", np.zeros((40, 120, 3), dtype="uint8"))
        cv2.waitKey(1)
        cv2.destroyAllWindows()
        return ""

    print("── no-robot mode " + "─" * 54)
    check("python 3.10+", python_version)
    check("opencv", import_cv2)
    check("mediapipe", import_mediapipe)
    check("hand model", model_present)
    check("hand tracker builds", tracker_builds)
    check("participant.gestures loads", recognizer_loads)
    check("webcam", camera_opens, fatal=False)
    check("a window can be opened", display_available, fatal=False)

    if args.robot:
        def unitree_sdk():
            import unitree_sdk2py
            return str(Path(unitree_sdk2py.__file__).parent)

        def cyclone():
            import cyclonedds
            v = getattr(cyclonedds, "__version__", "?")
            if v != "0.10.2":
                raise RuntimeError(f"found {v}, the SDK expects exactly 0.10.2")
            return v

        print("\n── robot mode " + "─" * 57)
        check("unitree_sdk2py", unitree_sdk)
        check("cyclonedds 0.10.2", cyclone, fatal=False)

    print()
    if problems:
        print(f"{problems} problem(s) to fix before you can run.")
        raise SystemExit(1)
    print("Ready. Start with:  python3.10 run.py")


if __name__ == "__main__":
    main()
