"""
eod_strategy.__main__
---------------------
Allows package execution with:
    python -m eod_strategy <args>

It simply forwards to eod_continuation.main()
"""
from .eod_continuation import main

if __name__ == "__main__":
    main()
