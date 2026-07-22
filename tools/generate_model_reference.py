"""Generate the ANDES-style reStructuredText reference for TGOV5."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from andes.system import System

from power_system_dynamic_models.andes import TGOV5


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "docs" / "TGOV5_MODEL_REFERENCE.rst"


def generate(output: Path) -> None:
    """Prepare the symbolic model and write its native ANDES documentation."""
    system = System(default_config=True, no_output=True, no_undill=True)
    model = TGOV5(system, None)

    with tempfile.TemporaryDirectory(prefix="tgov5-pycode-") as pycode_path:
        model.prepare(pycode_path=pycode_path)

    # Model.doc() resolves prepared equation calls through the parent System.
    system.calls[model.class_name] = model.calls
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(model.doc(export="rest").rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the TGOV5 reference using ANDES Model.doc().",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"output path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()
    generate(args.output.resolve())


if __name__ == "__main__":
    main()
