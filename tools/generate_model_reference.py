"""Generate ANDES-style reStructuredText references for repository models."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from andes.system import System

from power_system_dynamic_models.andes import LCC2T, TGOV5


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "LCC2T": LCC2T,
    "TGOV5": TGOV5,
}


def generate(model_name: str, output: Path) -> None:
    """Prepare the symbolic model and write its native ANDES documentation."""
    system = System(default_config=True, no_output=True, no_undill=True)
    model = MODELS[model_name](system, None)

    with tempfile.TemporaryDirectory(prefix=f"{model_name.lower()}-pycode-") as pycode_path:
        model.prepare(pycode_path=pycode_path)

    # Model.doc() resolves prepared equation calls through the parent System.
    system.calls[model.class_name] = model.calls
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(model.doc(export="rest").rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a model reference using ANDES Model.doc().",
    )
    parser.add_argument(
        "--model",
        choices=sorted(MODELS),
        default="TGOV5",
        help="model to document (default: TGOV5)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="output path (default: docs/<MODEL>_MODEL_REFERENCE.rst)",
    )
    args = parser.parse_args()
    output = args.output or REPOSITORY_ROOT / "docs" / f"{args.model}_MODEL_REFERENCE.rst"
    generate(args.model, output.resolve())


if __name__ == "__main__":
    main()
