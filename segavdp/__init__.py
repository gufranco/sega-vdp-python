from typing import Any

from tms9918.memory import Vram

from . import background as background
from . import core as core
from . import display as display
from . import errors as errors
from . import flags as flags
from . import models as models
from . import modes as modes
from . import palette as palette
from . import sound as sound
from . import sprites as sprites
from . import timing as timing
from .core import UNSET_SEED, port
from .errors import NoStereo, UnknownModelError, UnknownRegionError
from .models import MODELS, NTSC, PAL, Model
from .version import VERSION

__version__ = VERSION


def Chip(model: str | None = None, memory: Any = None, **options: Any) -> "core.Chip":  # noqa: N802
    seed = options.get("seed", UNSET_SEED)
    built: core.Chip = models.lookup(model).build(
        Vram(seed=seed) if memory is None else memory, **options
    )
    return built


__all__ = [
    "MODELS",
    "NTSC",
    "PAL",
    "UNSET_SEED",
    "Chip",
    "Model",
    "NoStereo",
    "UnknownModelError",
    "UnknownRegionError",
    "Vram",
    "__version__",
    "port",
]
