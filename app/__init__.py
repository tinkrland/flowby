"""the binding layer. a package so `python3 -m app.main` works from the repo root.

importing this puts `src/` on the path, which is the same trick `bin/flowby` plays, so the app is
a consumer of the library rather than a second copy of it.
"""

import pathlib
import sys

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
