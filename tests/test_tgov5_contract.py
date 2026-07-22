from __future__ import annotations

import json
from pathlib import Path

import pytest

from power_system_dynamic_models.andes import TGOV5, TGOV5Data, register_tgov5


ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = ROOT / "models" / "tgov5_gumede2016" / "parameters.json"
REFERENCE = ROOT / "docs" / "TGOV5_MODEL_REFERENCE.rst"


def test_parameter_bundle_is_complete_and_physically_compatible() -> None:
    payload = json.loads(PARAMETERS.read_text())
    p = payload["parameters"]

    assert len(p) == 50  # 49 public TGOV5 values plus the ANDES PBASE adapter.
    assert sum(p[f"K{i}"] for i in range(1, 9)) == pytest.approx(1.0)
    assert p["C1"] - p["K9"] * p["Psp"] > 0
    assert p["C3"] + p["K13"] * 0.5 == pytest.approx(p["Psp"])
    assert p["TD"] == pytest.approx(90.0)


def test_pressure_intervention_is_separate_and_default_on() -> None:
    data = TGOV5Data()

    assert data.PSEL.default == 1.0
    assert "PSEL" not in json.loads(PARAMETERS.read_text())["parameters"]


def test_model_metadata_is_complete_for_andes_reference_docs() -> None:
    data = TGOV5Data()
    undocumented = [
        name
        for name, parameter in data.params.items()
        if name not in {"idx", "u", "name", "syn", "Tn", "wref0"}
        and not parameter.info
    ]

    assert undocumented == []
    assert "single-shaft" in (TGOV5.__doc__ or "").lower()
    assert "PSEL" in (TGOV5.__doc__ or "")
    assert "90 s" in (TGOV5.__doc__ or "")

    reference = REFERENCE.read_text()
    for section in (
        "Parameters",
        "Variables",
        "Initialization Equations",
        "Differential Equations",
        "Algebraic Equations",
        "Services",
        "Discretes",
        "Blocks",
    ):
        assert f"{section}\n{'-' * len(section)}" in reference
    assert "Governor lag time constant" in reference


def test_symbolic_model_contract() -> None:
    from andes.system import System

    system = System(default_config=True, no_output=True, no_undill=True)
    model = TGOV5(system, None)

    assert model.SOURCE_FUEL_DELAY_SECONDS == pytest.approx(90.0)
    assert model.FuelDelay.delay == pytest.approx(90.0)
    assert model.PD.e_str == "Heat-L4_y"
    assert model.PT.e_str == "PD-(C1-K9*PD)*L4_y*L4_y-PT"
    assert model.PSP.e_str == "C3+K13*MWD-PSP"
    assert model.ep.e_str == "PSEL*(PSP-PT)-ep"
    assert model.L4.u.v == "Valve_y*(PSEL*PT+(1-PSEL)*Psp)"
    assert model.pout.e_str == "ue*PBASE*Pm-pout"


def test_pressure_controller_decomposition_matches_public_transfer_function() -> None:
    ti, tr, tr1 = 655.0, 4250.0, 4380.0
    a = ti * tr / tr1
    c = ti + tr - tr1 - a

    for s in (0.01j, 0.1j, 0.5j):
        realized = 1 / s + a + c / (1 + s * tr1)
        published = (1 + s * ti) * (1 + s * tr) / (s * (1 + s * tr1))
        assert realized == pytest.approx(published, rel=1e-12, abs=1e-12)


def test_registration_is_idempotent() -> None:
    import andes.models
    import andes.models.governor

    register_tgov5()
    register_tgov5()

    assert andes.models.governor.TGOV5 is TGOV5
    governor_classes = next(
        class_names for module_name, class_names in andes.models.file_classes
        if module_name == "governor"
    )
    assert governor_classes.count("TGOV5") == 1
