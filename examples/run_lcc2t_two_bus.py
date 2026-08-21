"""Run a minimal two-terminal LCC2T blocking and recovery example."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import andes
import numpy as np

from power_system_dynamic_models.andes import register_lcc2t


def build_case(pycode_path: Path) -> andes.System:
    """Build a minimal two-bus AC/DC verification system."""

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
    # The AC line is a topology scaffold for public ANDES 1.x connectivity
    # checks.  The LCC2T link is connected in parallel and its terminal
    # injections, DC state, blocking, and recovery are tested independently.
    system.add("GENCLS", idx="GEN2", bus=2, gen="PV2", Sn=100, Vn=230, M=6.0)
    system.add("LCC2T", idx="DC1", busr=1, busi=2, p0=0.5, pmax=1.0)
    for idx, time, value in (
        ("BLOCK", 0.10, 1.0),
        ("UNBLOCK", 0.20, 0.0),
    ):
        system.add(
            "Alter",
            param_dict={
                "idx": idx,
                "t": time,
                "model": "LCC2T",
                "dev": "DC1",
                "src": "block",
                "method": "=",
                "amount": value,
            },
        )
    return system


def main() -> None:
    logging.disable(logging.CRITICAL)
    with tempfile.TemporaryDirectory(prefix="lcc2t-example-") as tempdir:
        system = build_case(Path(tempdir) / "pycode")
        assert system.setup()
        assert system.PFlow.run() and system.PFlow.converged
        system.TDS.config.tf = 0.6
        system.TDS.config.tstep = 0.002
        system.TDS.init()
        assert system.TDS.initialized
        assert system.TDS.run()
        system.dae.ts.unpack()

        time = np.asarray(system.dae.ts.t, dtype=float)
        current = np.asarray(system.dae.ts.x)[:, system.LCC2T.Id.a[0]]
        delivered = np.asarray(system.dae.ts.y)[:, system.LCC2T.pinv.a[0]]
        run = np.asarray(system.dae.ts.y)[:, system.LCC2T.run.a[0]]
        print(f"samples={time.size} tf={time[-1]:.3f} s")
        print(f"initial inverter power={delivered[0]:.6f} p.u.")
        print(f"minimum DC current={current.min():.6e} p.u.")
        print(f"final inverter power={(run * delivered)[-1]:.6f} p.u.")


if __name__ == "__main__":
    main()
