# ── Python 3.10+ / tornado 6 compatibility fix ───────────────────────────────
# tornado 6.x uses asyncio's SelectorEventLoop.  On Windows + Python 3.10+,
# asyncio defaults to ProactorEventLoop which is incompatible.
# Setting WindowsSelectorEventLoopPolicy here ensures correct behaviour when
# airsim is imported (e.g. in airsim_fly.py or airsim_patrol.py).
# In main.py this policy is already set before import — this is a safety net.
import sys as _sys
import asyncio as _asyncio

if _sys.platform == "win32":
    if not isinstance(_asyncio.get_event_loop_policy(),
                       _asyncio.WindowsSelectorEventLoopPolicy):
        _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())
# ─────────────────────────────────────────────────────────────────────────────

from .client import *
from .utils import *
from .types import *

__version__ = "1.8.1"
