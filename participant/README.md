# Your folder

`gestures.py` is the file you edit. Everything else in the repository is
infrastructure and is frozen — see the root `README.md`.

Two things must keep their shape:

1. the class is called `GestureRecognizer`
2. it has a method `update(self, obs) -> Action`

Everything else below the `EDIT FROM HERE` banner in `gestures.py` is yours.

Need more room? Add files next to this one and import them:

```python
# participant/gestures.py
from participant.filters import Debouncer
```

Anything under `participant/` travels with your submission. Anything outside it
does not.

Run what you have:

```bash
python3.10 run.py          # from the repository root
```

and press `r` in the preview window after every edit instead of restarting.
