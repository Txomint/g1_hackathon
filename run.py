#!/usr/bin/env python3.10
"""
Launcher.  ── FROZEN FILE, DO NOT EDIT ──

    python3.10 run.py                        no-robot mode, laptop camera  (default)
    python3.10 run.py --image shots/         no-robot mode, stills from a path
    python3.10 run.py --robot                robot mode: robot camera, robot moves
    python3.10 run.py --robot --local-camera robot mode: laptop camera, robot moves

`--help` lists everything.  No-robot mode is the default on purpose: you should
never need the robot to develop a gesture.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.camera import ImageFolder, LaptopCamera, RobotCamera   # noqa: E402
from core.engine import Engine                                   # noqa: E402
from core.robot import G1Driver, NullRobot                       # noqa: E402


def _impl_module(spec: str) -> str:
    """Accept either a module path (participant.gestures) or a file path."""
    if spec.endswith(".py") or os.sep in spec:
        path = Path(spec).expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"--impl: no such file: {path}")
        sys.path.insert(0, str(path.parent))
        return path.stem
    return spec


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Gesture control for the Unitree G1",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    mode = p.add_argument_group("mode")
    mode.add_argument(
        "--robot", action="store_true",
        help="drive the real robot. Without this flag nothing moves.",
    )
    mode.add_argument(
        "--iface", default="enp3s0",
        help="network interface wired to the G1 (robot mode only)",
    )
    mode.add_argument(
        "--local-camera", action="store_true",
        help="robot mode with the laptop webcam instead of the robot's camera",
    )
    mode.add_argument(
        "--no-standup", action="store_true",
        help="skip the stand-up sequence — the robot is already standing in FSM 801",
    )
    mode.add_argument(
        "--yes", action="store_true",
        help="do not ask for confirmation before the robot stands up",
    )

    src = p.add_argument_group("input")
    src.add_argument("--camera", type=int, default=0, help="webcam index")
    src.add_argument(
        "--image", metavar="PATH",
        help="read an image file, or every image in a folder, instead of a camera "
             "(n / p step through a folder)",
    )
    src.add_argument("--mirror", action="store_true",
                     help="flip the frame horizontally. Makes the preview feel like a "
                          "mirror, and swaps MediaPipe's left/right hand labels.")
    src.add_argument("--max-hands", type=int, default=2,
                     help="how many hands the tracker may report at once")
    src.add_argument("--detect-hz", type=float, default=20.0,
                     help="upper bound on detections per second")
    src.add_argument("--model", default=None,
                     help="path to hand_landmarker.task (default: models/)")

    out = p.add_argument_group("output")
    out.add_argument("--impl", default="participant.gestures",
                     help="the recognizer to run — a module name or a path to a .py "
                          "file. Point it at another team's file to test their work.")
    out.add_argument("--no-display", action="store_true",
                     help="no preview window (headless; only Ctrl-C stops it)")
    return p.parse_args(argv)


def build_source(args):
    if args.image:
        return ImageFolder(args.image), True          # stills → static tracking
    if args.robot and not args.local_camera:
        return RobotCamera(args.iface), False
    return LaptopCamera(args.camera), False


def confirm_robot_mode() -> None:
    print("\n  ROBOT MODE")
    print("  - the G1 must be in a squat, or already standing with --no-standup")
    print("  - clear at least 2 m around it")
    print("  - the remote controller must be on and within reach")
    print("  - motion starts DISARMED; press SPACE in the preview window to arm\n")
    if input("  Type 'go' to continue: ").strip().lower() != "go":
        raise SystemExit("aborted")


def build_robot(args):
    if not args.robot:
        return NullRobot()

    driver = G1Driver(args.iface)
    if args.no_standup:
        fsm, mode = driver.fsm()
        print(f"[robot] skipping stand-up — FSM {fsm} mode {mode}", flush=True)
        if fsm != 801:
            raise SystemExit(
                f"--no-standup given but the robot is in FSM {fsm}, not 801. "
                "Drop --no-standup, or stand it up with g1_control/rnd.py first."
            )
    else:
        driver.stand_up()
    return driver


def main() -> None:
    args = parse_args()
    if args.local_camera and not args.robot:
        raise SystemExit("--local-camera only means something together with --robot")
    if args.image and args.robot:
        raise SystemExit("--image cannot drive the robot: there is nothing live to react to")

    if args.robot and not args.yes:
        confirm_robot_mode()      # before anything touches the robot or its camera

    impl = _impl_module(args.impl)
    source, static = build_source(args)
    robot = build_robot(args)

    engine = Engine(
        source=source,
        robot=robot,
        impl=impl,
        max_hands=args.max_hands,
        detect_hz=args.detect_hz,
        mirror=args.mirror,
        display=not args.no_display,
        static=static,
        model_path=args.model,
    )
    print(f"[engine] recognizer: {impl}   mode: {robot.label}", flush=True)
    try:
        engine.run()
    except KeyboardInterrupt:
        pass
    finally:
        engine.close()

    # The Unitree SDK's cyclonedds build aborts during interpreter teardown
    # (known, harmless — see "Known issues" in the g1_control README). All
    # commands have already been sent by this point, so exit hard.
    if args.robot:
        os._exit(0)


if __name__ == "__main__":
    main()
