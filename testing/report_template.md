# Test report — <your team> testing <their team>

Copy this file to `report_<your team>.md` and fill it in. Delete the italics.

---

## 1. What we tested

*The implementation under test, and how you ran it — live camera, stills, the
suite, or all three. One paragraph.*

**Recognizer under test:** `teams/____/gestures.py`
**Ran as:** `python3.10 run.py --impl ...`

## 2. What we decided to look at, and why

*Before you touched it: what did you expect a camera-driven gesture controller
to be bad at, and what made you think so? List the conditions you chose to
probe and the reasoning behind each. This section is worth as much as the
findings — anyone can stumble into a bug, and we want to see the thinking that
went looking for one.*

| # | What we probed | Why we thought it was worth probing |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |

## 3. Findings

*One block per failure. A finding without a reproduction is not a finding.*

### F1 — <one line: what goes wrong>

| | |
|---|---|
| **Severity** | robot moved when it should not have / moved the wrong way / refused to move / crashed |
| **Reproduce** | `testing/cases/NONE/xyz.jpg`, or the exact steps |
| **Expected** | `STOP` |
| **Got** | `FORWARD` |
| **How consistent** | always / about half the time / once in twenty |

**What we think is happening:** *your reading of the cause, from their code and
from the per-finger numbers in the preview window.*

**Suggested fix:** *optional, and appreciated.*

---

### F2 — ...

## 4. Inaccuracy — cases with no clear right answer

*Situations where the robot did something, but you could not say what it
should have done. For example: two people in frame, one pointing forward and
one holding up a palm — should it walk or stop? These are not scored as
failures. They are the decisions the designers never made, and each one needs a
rule before this controller goes near a real robot.*

### A1 — <one line: the situation>

| | |
|---|---|
| **Reproduce** | `testing/ambiguous/xyz.jpg`, or the exact steps |
| **What it did** | `FORWARD` |
| **Arguable answers** | `STOP` / `FORWARD` / `NONE` |
| **How consistent** | always / about half the time / once in twenty |

**What we would pick, and why:** *which answer you think is right and the rule
behind it — e.g. "any STOP in frame wins, because stopping is always safe".*

**How their code decides today:** *if you can tell from their code — largest
hand, first hand, whichever came last.*

---

### A2 — ...

## 5. Suite results

```
paste the output of testing/run_suite.py here
```

| | |
|---|---|
| Cases | |
| Correct | |
| Moved wrongly | |
| Crashed | |

## 6. What held up

*What you tried that did not break it. A controller that survived a serious
attempt deserves to have that written down, and it tells the next team where
not to bother.*

## 7. The case folder we built

*Where it is, how many cases, and how you labelled them. Hand it over with the
report, along with `testing/ambiguous/` — the other team should be able to
rerun everything you did.*
