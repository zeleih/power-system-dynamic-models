"""Register repository-owned dynamic models with ANDES at runtime."""

from __future__ import annotations

import importlib


def _register_model(class_name: str, model_class: type, module_name: str) -> None:
    """Idempotently expose one external model through an ANDES registry."""

    import sys

    import andes.models

    model_module = importlib.import_module(f"andes.models.{module_name}")

    # ANDES imports generated numerical code through a process-global package
    # named ``pycode``. A notebook can retain stale generated modules after its
    # registry changes, so clear only those modules before the next load.
    for loaded_name in tuple(sys.modules):
        if loaded_name == "pycode" or loaded_name.startswith("pycode."):
            del sys.modules[loaded_name]

    setattr(model_module, class_name, model_class)
    for registered_module, class_names in andes.models.file_classes:
        if registered_module == module_name:
            if class_name not in class_names:
                class_names.append(class_name)
            return
    raise RuntimeError(f"ANDES {module_name!r} registry entry was not found")


def register_tgov5() -> None:
    """Idempotently expose :class:`TGOV5` through ANDES' governor registry."""

    from .tgov5 import TGOV5

    _register_model("TGOV5", TGOV5, "governor")


def register_lcc2t() -> None:
    """Idempotently expose :class:`LCC2T` through ANDES' AC/DC registry."""

    from .lcc2t import LCC2T

    _register_model("LCC2T", LCC2T, "acdc")
