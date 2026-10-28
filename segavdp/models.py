from collections.abc import Callable, Sequence
from typing import Any, override

from segavdp.errors import UnknownModelError, UnknownRegionError

NTSC = "ntsc"

PAL = "pal"

REGIONS = (NTSC, PAL)

FIXED = "fixed"

CRAM = "cram"


class Model:
    __slots__ = (
        "aliases",
        "core",
        "extended",
        "handheld",
        "legacy",
        "masks",
        "name",
        "regions",
        "summary",
        "zoomed_across",
    )

    def __init__(
        self,
        name: str,
        summary: str,
        regions: Sequence[str],
        traits: dict[str, Any],
        core: Callable[..., Any],
        aliases: Sequence[str] = (),
    ) -> None:
        self.name = name
        self.summary = summary
        self.regions = tuple(regions)
        self.extended: bool = traits["extended"]
        self.masks: bool = traits["masks"]
        self.zoomed_across: int = traits["zoomed_across"]
        self.legacy: str = traits["legacy"]
        self.handheld: bool = traits["handheld"]
        self.core = core
        self.aliases = tuple(aliases)

    def build(self, memory: Any, **options: Any) -> Any:
        return self.core(self, memory, **options)

    def region(self, name: str | None) -> str:
        if name is None:
            return str(self.regions[0])
        wanted = str(name).strip().lower()
        if wanted in self.regions:
            return wanted
        raise UnknownRegionError(
            f"{name} is not a region the {self.name} runs in; it runs in {', '.join(self.regions)}"
        )

    @override
    def __repr__(self) -> str:
        return f"<Model {self.name}, {'/'.join(self.regions)}>"


def _build(model: Model, memory: Any, **options: Any) -> Any:
    from .core import Chip

    return Chip(model, memory, **options)


_CATALOGUE = (
    Model(
        name="315-5124",
        summary=(
            "The Mark III and first Master System VDP: mode 4 at 192 lines only, the "
            "table address bits that mask what the chip fetches, and horizontal zoom "
            "on the first four sprites of a line."
        ),
        regions=REGIONS,
        traits={
            "extended": False,
            "masks": True,
            "zoomed_across": 4,
            "legacy": FIXED,
            "handheld": False,
        },
        core=_build,
        aliases=("5124", "sms", "mark3", "markiii"),
    ),
    Model(
        name="315-5246",
        summary=(
            "The second Master System VDP: the 224 and 240 line mode 4 screens, no "
            "address masking, and horizontal zoom on all eight sprites of a line."
        ),
        regions=REGIONS,
        traits={
            "extended": True,
            "masks": False,
            "zoomed_across": 8,
            "legacy": FIXED,
            "handheld": False,
        },
        core=_build,
        aliases=("5246", "sms2"),
    ),
    Model(
        name="315-5378",
        summary=(
            "The Game Gear VDP: the second Master System part's behaviour plus a "
            "twelve bit colour RAM in Game Gear mode, legacy modes coloured from "
            "colour RAM, and 262 lines only."
        ),
        regions=(NTSC,),
        traits={
            "extended": True,
            "masks": False,
            "zoomed_across": 8,
            "legacy": CRAM,
            "handheld": True,
        },
        core=_build,
        aliases=("5378", "gg", "gamegear"),
    ),
)

MODELS = {model.name: model for model in _CATALOGUE}

_BY_ALIAS = {alias: model for model in _CATALOGUE for alias in (model.name, *model.aliases)}


def _normalise(name: str) -> str:
    return str(name).strip().lower().replace(" ", "").replace("_", "")


def lookup(name: str | None) -> Model:
    if name is None:
        raise UnknownModelError(
            "no model was named, and this package will not choose one for you."
            f" Name one of: {', '.join(sorted(MODELS))}"
        )
    found = _BY_ALIAS.get(_normalise(name))
    if found is None:
        raise UnknownModelError(
            f"{name} is not a model this package covers; it has {', '.join(sorted(MODELS))}"
        )
    return found
