"""``python -m eval.gold`` — regenerate the adapted gold from the labeled gold.

A module entry point rather than ``python -m eval.gold.adapter``: the package's ``__init__`` imports
``adapter``, so running the submodule directly emits a ``RuntimeWarning`` about double import. The
reviewer command must be quiet enough that a real warning would stand out.
"""

from __future__ import annotations

import sys

from .adapter import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
