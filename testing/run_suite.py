#!/usr/bin/env python3.10
"""
Batch tester.  ── FROZEN FILE, DO NOT EDIT ──

Runs a recognizer over a folder of labelled still images and prints a score.
This is the phase-2 workhorse: build a folder of cases, point it at another
team's file, and see what falls over.

Folder layout — the folder name is the action you expect:

    cases/
      STOP/         palm_close.jpg  palm_far.jpg  palm_dark.jpg ...
      FORWARD/      index_01.jpg ...
      ROTATE_LEFT/  ...
      NONE/         empty_room.jpg  two_people.jpg  coffee_mug.jpg ...

`NONE` is the most valuable folder you will build. It is where you put the
frames that *should not* command anything, and it is where most implementations
lose.

Usage:
    python3.10 testing/run_suite.py --cases testing/cases
    python3.10 testing/run_suite.py --cases testing/cases --impl teams/blue/gestures.py
    python3.10 testing/run_suite.py --cases testing/cases --per-image
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.actions import BUILTIN                       # noqa: E402
from core.engine import load_recognizer                # noqa: E402
from core.hand_tracker import HandTracker              # noqa: E402

_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
_MOVING = {n for n, a in BUILTIN.items() if not a.is_idle}


def _impl_module(spec: str) -> str:
    if spec.endswith(".py") or os.sep in spec:
        path = Path(spec).expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"--impl: no such file: {path}")
        sys.path.insert(0, str(path.parent))
        return path.stem
    return spec


def collect(cases_dir: Path) -> list[tuple[str, Path]]:
    if not cases_dir.is_dir():
        raise SystemExit(f"No such folder: {cases_dir}")
    items: list[tuple[str, Path]] = []
    for label_dir in sorted(p for p in cases_dir.iterdir() if p.is_dir()):
        label = label_dir.name.upper()
        for img in sorted(label_dir.rglob("*")):
            if img.suffix.lower() in _SUFFIXES:
                items.append((label, img))
    if not items:
        raise SystemExit(
            f"No labelled images under {cases_dir}.\n"
            "Create one folder per expected action, e.g. cases/STOP/, and drop "
            "images in it. Grab frames with run.py and the 's' key."
        )
    return items


def run(cases: list[tuple[str, Path]], impl: str, repeat: int, max_hands: int, verbose: bool):
    tracker = HandTracker(max_hands=max_hands, static=True)
    confusion: dict[str, Counter] = defaultdict(Counter)
    failures: list[tuple[str, str, Path]] = []

    for expected, path in cases:
        frame = cv2.imread(str(path))
        if frame is None:
            print(f"  !! could not decode {path}")
            continue

        # A fresh recognizer per image: no state carried over from the previous
        # case. The same frame is then fed `repeat` times at 20 fps so a
        # recognizer that debounces over several frames has time to settle.
        recognizer, _ = load_recognizer(impl)
        got = "NONE"
        for i in range(max(repeat, 1)):
            obs = tracker.observe(frame, t=i * 0.05, dt=0.05)
            try:
                action = recognizer.update(obs)
            except Exception as exc:     # a crash is a test result, not a stop sign
                got = f"CRASH({type(exc).__name__})"
                break
            got = "NONE" if action is None else action.name

        confusion[expected][got] += 1
        if got != expected:
            failures.append((expected, got, path))
        if verbose:
            mark = "ok  " if got == expected else "FAIL"
            print(f"  {mark} {path}: expected {expected}, got {got}")

    tracker.close()
    return confusion, failures


def report(confusion, failures, total: int) -> int:
    correct = sum(c[label] for label, c in confusion.items())

    print("\n── per label " + "─" * 58)
    print(f"  {'expected':<14}{'n':>4}{'correct':>9}   what it actually said")
    for label in sorted(confusion):
        counts = confusion[label]
        n = sum(counts.values())
        others = ", ".join(
            f"{k}x{v}" for k, v in counts.most_common() if k != label
        )
        print(f"  {label:<14}{n:>4}{counts[label]:>9}   {others or '-'}")

    # Errors that would move a humanoid when it should have held still, or move
    # it the wrong way. These are the ones worth writing up.
    dangerous = [
        (exp, got, p) for exp, got, p in failures
        if got in _MOVING and (exp in ("STOP", "NONE") or exp in _MOVING)
    ]
    crashes = [f for f in failures if f[1].startswith("CRASH")]

    print("\n── summary " + "─" * 60)
    print(f"  cases            {total}")
    print(f"  correct          {correct}  ({100.0 * correct / max(total, 1):.1f}%)")
    print(f"  wrong            {len(failures)}")
    print(f"  moved wrongly    {len(dangerous)}   <- should have held still, or went the wrong way")
    print(f"  crashed          {len(crashes)}")

    if dangerous:
        print("\n── moved when it should not have " + "─" * 38)
        for exp, got, p in dangerous[:25]:
            print(f"  {p}: expected {exp}, got {got}")
        if len(dangerous) > 25:
            print(f"  ... and {len(dangerous) - 25} more")

    return 0 if not failures else 1


def main() -> None:
    p = argparse.ArgumentParser(description="Score a recognizer against labelled stills")
    p.add_argument("--cases", default=str(Path(__file__).resolve().parent / "cases"),
                   help="folder of <ACTION>/ subfolders")
    p.add_argument("--impl", default="participant.gestures",
                   help="recognizer module name or path to a .py file")
    p.add_argument("--repeat", type=int, default=5,
                   help="how many times each still is fed in, so temporal filters settle")
    p.add_argument("--max-hands", type=int, default=2)
    p.add_argument("--per-image", action="store_true", help="print every case")
    args = p.parse_args()

    impl = _impl_module(args.impl)
    cases = collect(Path(args.cases).expanduser())
    print(f"recognizer: {impl}   cases: {len(cases)}")
    confusion, failures = run(cases, impl, args.repeat, args.max_hands, args.per_image)
    raise SystemExit(report(confusion, failures, len(cases)))


if __name__ == "__main__":
    main()
