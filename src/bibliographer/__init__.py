"""bibliographer package
"""

import logging


mlogger = logging.getLogger(__name__)


def add_console_handler(level=logging.INFO):
    conhandler = logging.StreamHandler()
    conhandler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    mlogger.setLevel(level)
    conhandler.setLevel(level)
    mlogger.addHandler(conhandler)
