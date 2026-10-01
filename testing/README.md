# Phase 2 — the testing phase

The brief is in the root `README.md`. This folder holds the tools.

## What is here

| | |
|---|---|
| `run_suite.py` | scores a recognizer against a folder of labelled stills |
| `cases/` | where your labelled stills go |
| `ambiguous/` | stills where you could not say what the right action was |
| `report_template.md` | what you hand in — copy it to `report_<your team>.md` |

## Running another team's recognizer

Drop their `participant/` folder somewhere in your checkout — `teams/red/` is
the convention — and point the launcher at it:

```bash
python3.10 run.py --impl teams/red/gestures.py
python3.10 run.py --impl teams/red/gestures.py --image captures/
```

Nothing is copied over your own work, and you can switch back by dropping the
flag.

## Building a case folder

One folder per expected action. The folder name **is** the label, and it has to
match an action name exactly:

```
testing/cases/
  STOP/
    palm_01.jpg
    palm_02.jpg
  FORWARD/
    index_01.jpg
  ROTATE_LEFT/
    ...
  NONE/
    ...
```

Fill it the easy way: run the launcher, press `s` whenever the frame on screen
is one you want to keep, and sort what lands in `captures/` afterwards.

```bash
python3.10 run.py                 # press s, s, s ...
mv captures/*.jpg testing/cases/STOP/
```

`NONE/` is the folder that does the most work. It is for every frame that should
*not* command anything at all — and it is where most implementations come apart,
because "recognise the six gestures" is a much easier problem than "recognise
the six gestures and nothing else".

## Scoring

```bash
python3.10 testing/run_suite.py --cases testing/cases
python3.10 testing/run_suite.py --cases testing/cases --impl teams/red/gestures.py
python3.10 testing/run_suite.py --cases testing/cases --per-image
```

Output:

```
── per label ──────────────────────────────────────────────────────────
  expected         n  correct   what it actually said
  FORWARD         12       11   NONEx1
  NONE            20       13   FORWARDx5, STOPx2
  STOP            14       14   -

── summary ────────────────────────────────────────────────────────────
  cases            46
  correct          38  (82.6%)
  wrong             8
  moved wrongly     5   <- should have held still, or went the wrong way
  crashed           0
```

**`moved wrongly` is the number that matters.** Being unable to recognise a
gesture is an annoyance; commanding a humanoid to walk when the operator did not
ask it to is the actual failure.

Each still is fed to a freshly constructed recognizer five times in a row
(`--repeat`), so a recognizer that deliberately waits a few frames before
committing gets its chance to settle. A single still cannot tell you anything
about how something behaves over *changing* frames, though — that part you have
to test live.

## Cases with no right answer

Some frames have no single expected action — two people signalling different
things, a hand halfway between two gestures, a gesture from someone in the
background. They cannot go in `cases/`, because a folder name is a claim about
the right answer. Put them in `ambiguous/` and write them up in the
**Inaccuracy** section of the report instead.

## Ground rules

- Attack the recognizer, not the harness. Editing `core/`, or feeding the suite
  a corrupt file, proves nothing about anyone's gesture logic.
- Every finding needs a reproduction: a saved frame, a case folder, or a written
  sequence someone else can repeat. "It felt unreliable" is not a finding.
