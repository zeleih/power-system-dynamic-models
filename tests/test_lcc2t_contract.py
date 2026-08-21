from __future__ import annotations

import json
from pathlib import Path
import tempfile

import numpy as np
import pytest

from power_system_dynamic_models.andes import LCC2T, LCC2TData, register_lcc2t


ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = ROOT / "models" / "lcc2t_public_2bus" / "parameters.json"
REFERENCE = ROOT / "docs" / "LCC2T_MODEL_REFERENCE.rst"


def _build_system(pycode_path: Path, *, with_block: bool = False):
    import andes

    register_lcc2t()
    system = andes.System(
        default_config=True,
        no_output=True,
        pycode_path=str(pycode_path),
    )
    for bus in (1, 2):
        system.add("Bus", idx=bus, Vn=230, v0=1.0, a0=0.0)
    system.add(
        "Slack", idx="S1", bus=1, Vn=230, v0=1.0, a0=0.0, p0=0.0, q0=0.0
    )
    system.add("PV", idx="PV2", bus=2, Vn=230, p0=0.0, q0=0.0, v0=1.0)
    system.add(
        "Line",
        idx="L12",
        bus1=1,
        bus2=2,
        Sn=100,
        Vn1=230,
        Vn2=230,
        r=0.0,
        x=0.1,
        b=0.0,
    )
    system.add("GENCLS", idx="GEN2", bus=2, gen="PV2", Sn=100, Vn=230, M=6.0)
    system.add("LCC2T", idx="DC1", busr=1, busi=2, p0=0.5, pmax=1.0)
    if with_block:
        system.add(
            "Alter",
            param_dict={
                "idx": "BLOCK",
                "t": 0.05,
                "model": "LCC2T",
                "dev": "DC1",
                "src": "block",
                "method": "=",
                "amount": 1.0,
            },
        )
    assert system.setup()
    assert system.PFlow.run() and system.PFlow.converged
    return system


def test_public_parameter_card_matches_model_defaults() -> None:
    data = LCC2TData()
    published = json.loads(PARAMETERS.read_text(encoding="utf-8"))["parameters"]

    assert published.keys() == {
        name for name in data.params if name not in {"idx", "u", "name", "busr", "busi"}
    }
    for name, expected in published.items():
        assert getattr(data, name).default == pytest.approx(expected)


def test_model_metadata_and_andes_reference_are_complete() -> None:
    data = LCC2TData()
    assert [
        name
        for name, parameter in data.params.items()
        if name not in {"idx", "u", "name"} and not parameter.info
    ] == []

    reference = REFERENCE.read_text(encoding="utf-8")
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
    assert "DC line and smoothing inductance" in reference


def test_symbolic_acdc_interface_contract() -> None:
    from andes.system import System

    model = LCC2T(System(default_config=True, no_output=True, no_undill=True), None)
    assert model.group == "StaticACDC"
    assert model.flags.pflow and model.flags.tds
    assert model.Id.e_str.endswith("-block*(ldc/tblock)*Id)")
    assert model.Ida.e_str.endswith("*(Id-Ida)")
    assert model.ar.e_str == "u*run*pr"
    assert model.ai.e_str == "-u*run*pinv"
    assert model.vr.e_str == "u*(run*qr-filter*qcr*vr**2)"
    assert model.vi.e_str == "u*(run*qi-filter*qci*vi**2)"


def test_registration_is_idempotent() -> None:
    import andes.models.acdc

    register_lcc2t()
    register_lcc2t()

    assert andes.models.acdc.LCC2T is LCC2T
    classes = next(
        names for module_name, names in andes.models.file_classes if module_name == "acdc"
    )
    assert classes.count("LCC2T") == 1


def test_power_flow_identity_and_no_disturbance_drift() -> None:
    with tempfile.TemporaryDirectory(prefix="lcc2t-contract-") as tempdir:
        system = _build_system(Path(tempdir) / "pycode")

        current = float(system.LCC2T.Ida.v[0])
        rectifier = float(system.LCC2T.pr.v[0])
        inverter = float(system.LCC2T.pinv.v[0])
        resistance = float(system.LCC2T.rdc.v[0])
        assert rectifier - inverter == pytest.approx(resistance * current**2, abs=1e-9)

        system.TDS.config.tf = 0.05
        system.TDS.config.tstep = 0.002
        system.TDS.init()
        assert system.TDS.initialized
        assert np.max(np.abs(system.dae.f)) < 1e-8
        assert np.max(np.abs(system.dae.g)) < 1e-8
        assert system.TDS.run()
        system.dae.ts.unpack()

        dc_current = np.asarray(system.dae.ts.x)[:, system.LCC2T.Id.a[0]]
        inverter_power = np.asarray(system.dae.ts.y)[:, system.LCC2T.pinv.a[0]]
        assert np.ptp(dc_current) < 1e-8
        assert np.ptp(inverter_power) < 1e-7


def test_block_removes_ac_power_and_current_never_reverses() -> None:
    with tempfile.TemporaryDirectory(prefix="lcc2t-block-") as tempdir:
        system = _build_system(Path(tempdir) / "pycode", with_block=True)
        system.TDS.config.tf = 0.20
        system.TDS.config.tstep = 0.002
        system.TDS.init()
        assert system.TDS.run()
        system.dae.ts.unpack()

        time = np.asarray(system.dae.ts.t, dtype=float)
        current = np.asarray(system.dae.ts.x)[:, system.LCC2T.Id.a[0]]
        run = np.asarray(system.dae.ts.y)[:, system.LCC2T.run.a[0]]
        inverter = np.asarray(system.dae.ts.y)[:, system.LCC2T.pinv.a[0]]
        post = time > 0.06
        assert current.min() >= -1e-12
        assert np.max(np.abs((run * inverter)[post])) < 1e-9
        assert current[-1] < 1e-3
