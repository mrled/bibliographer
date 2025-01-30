"""Utilities for command-line programs
"""

import os
import pdb
import sys
import traceback
from typing import Callable
import argparse




class AutoDescriptionArgumentParser(argparse.ArgumentParser):
    """An ArgumentParser that automatically sets the description from the help string when creating subparsers.

    When using this parser class,
    the help string shown by the parent parser is also shown by the subparser.
    In the example below, SUBCMD HELP STRING is shown by the parent parser and the subparser.
    By default, the help string is only shown by the parent parser,
    and the subparser just shows its arguments.

        > program --help
        usage: program [-h] {subcmd} ...
        positional arguments:
          {subcmd}
            subcmd  SUBCMD HELP STRING

        > program subcmd --help
        usage: program subcmd [-h] ...
        SUBCMD HELP STRING

    When recursively showing all argparse help,
    it's nice to have the help string shown by the subparser.
    """

    def add_subparsers(self, **kwargs):
        # Create a custom subparser action class
        class AutoDescriptionSubParserAction(argparse._SubParsersAction):
            def add_parser(self, name, help=None, **kwargs):
                if help and 'description' not in kwargs:
                    kwargs['description'] = help
                return super().add_parser(name, help=help, **kwargs)

        # Use the custom action class when creating subparsers
        kwargs['action'] = AutoDescriptionSubParserAction
        return super().add_subparsers(**kwargs)


def get_argparse_help_string(
    name: str, parser: argparse.ArgumentParser, wrap: int = 80
) -> str:
    """Generate a docstring for an argparse parser that shows the help for the parser and all subparsers, recursively.

    Based on an idea from <https://github.com/pdoc3/pdoc/issues/89>

    Arguments:
    * `name`: The name of the program
    * `parser`: The parser
    * `wrap`: The number of characters to wrap the help text to (0 to disable)
    """

    def get_parser_help_recursive(
        parser: argparse.ArgumentParser, cmd: str = "", root: bool = True
    ):
        docstring = ""
        if not root:
            docstring += "\n" + "_" * 72 + "\n\n"
        docstring += f"> {cmd} --help\n"
        parser.formatter_class = lambda prog: argparse.HelpFormatter(cmd, width=wrap)
        docstring += parser.format_help()

        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for subcmd, subparser in action.choices.items():
                    docstring += get_parser_help_recursive(
                        subparser, f"{cmd} {subcmd}", root=False
                    )
        return docstring

    docstring = get_parser_help_recursive(parser, name)
    return docstring


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


def exceptional_exception_handler(func: Callable[[list[str]], int], arguments: list[str]) -> int:
    """Handler for exceptional exceptions

    You see, most unhandled exceptions should terminate the program with a traceback,
    or, in debug mode, drop into pdb.pm().
    But for a few EXCEPTIONAL exceptions, we want to handle them gracefully.

    Wrap the main() function in this to handle these exceptional exceptions
    without a giant nastsy backtrace.
    """
    try:
        returncode = func(arguments)
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
