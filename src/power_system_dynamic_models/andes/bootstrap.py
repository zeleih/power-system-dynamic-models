"""Register repository-owned dynamic models with ANDES at runtime."""

from __future__ import annotations


def register_tgov5() -> None:
    """Idempotently expose :class:`TGOV5` through ANDES' governor registry."""

    import sys

    import andes.models
    import andes.models.governor

    from .tgov5 import TGOV5

    # ANDES imports generated numerical code through a process-global package
    # named ``pycode``. A notebook can retain stale generated modules after its
    # registry changes, so clear only those modules before the next load.
    for module_name in tuple(sys.modules):
        if module_name == "pycode" or module_name.startswith("pycode."):
            del sys.modules[module_name]

    setattr(andes.models.governor, "TGOV5", TGOV5)
    for module_name, class_names in andes.models.file_classes:
        if module_name == "governor":
            if "TGOV5" not in class_names:
                class_names.append("TGOV5")
            return
    raise RuntimeError("ANDES governor registry entry was not found")

