"""Utilities for command-line programs
"""

import os
import pdb
import sys
import traceback
from typing import Callable


def idb_excepthook(type_, value, tb):
    """
    Interactive debugger post-mortem hook.
    If debug mode is on, and an unhandled exception occurs, we drop into pdb.pm().
    """
    if hasattr(sys, "ps1") or not sys.stderr.isatty():
        sys.__excepthook__(type_, value, tb)
    else:
        traceback.print_exception(type_, value, tb)
        print()
        pdb.pm()


def exceptional_exception_handler(func: Callable[[list[str]], int], *arguments: list[str]) -> int:
    """Handler for exceptional exceptions

    You see, most unhandled exceptions should terminate the program with a traceback,
    or, in debug mode, drop into pdb.pm().
    But for a few EXCEPTIONAL exceptions, we want to handle them gracefully.

    Wrap the main() function in this to handle these exceptional exceptions
    without a giant nastsy backtrace.
    """
    try:
        returncode = func(*arguments)
        sys.stdout.flush()
    except BrokenPipeError:
        # The EPIPE signal is sent if you run e.g. `script.py | head`.
        # Wrapping the main function with this one exits cleanly if that happens.
        # See <https://docs.python.org/3/library/signal.html#note-on-sigpipe>
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        # Convention is 128 + whatever the return code would otherwise be
        returncode = 128 + 1
    except KeyboardInterrupt:
        # This is sent when the user hits Ctrl-C
        print()
        returncode = 128 + 2
    return returncode
