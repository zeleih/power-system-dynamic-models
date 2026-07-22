# Power System Dynamic Models

[![Tests](https://github.com/zeleih/power-system-dynamic-models/actions/workflows/test.yml/badge.svg)](https://github.com/zeleih/power-system-dynamic-models/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![ANDES](https://img.shields.io/badge/ANDES-tested%201.10.1-00599c.svg)](https://github.com/CURENT/andes)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Source-traceable dynamic models for power-system research. The first model is a
single-shaft **TGOV5 boiler-turbine-governor for ANDES**, reconstructed from public
equations and packaged with explicit validation boundaries.

> [!IMPORTANT]
> This is an independent research implementation. It is not official ANDES code,
> proprietary PSS/E source code, or a claim of commercial-model numerical parity.

## TGOV5 model overview

TGOV5 represents the coupled response of a speed governor, load controller, staged
steam turbine, boiler pressure, pressure controller, and delayed fuel/heat path.

| Capability | This release |
|---|---|
| Runtime | Tested with public ANDES 1.10.1; package range `>=1.9.3,<2` |
| Topology | Single shaft, one mechanical-power output |
| Parameter set | Gumede (2016) aggregate benchmark |
| Fuel delay | Exact 90 s time-domain delay |
| Internal base | Turbine base; `PBASE` converts output to system base |
| Validation level | Source-consistent research benchmark |

```text
 speed ─► governor ─┐
                    ▼
 demand ─► power order ─► valve ─► steam stages ─► mechanical power
            ▲                        │
            │                        ▼
 measured power ◄──────────── boiler/throttle pressure
                                     ▲
 pressure set point ─► controller ─► fuel ─► water wall ─► delay ─► heat
```

## Symbolic modeling in ANDES

The implementation follows the equation-oriented ANDES model style. Standard
transfer functions use ANDES blocks, while the pressure DAE loop and custom
controller relationships remain explicit and auditable.

```python
self.PD = State(
    info="Drum pressure",
    t_const=self.CB,
    v_str="pd0",
    e_str="Heat-L4_y",
)
self.PT = Algeb(
    info="Throttle pressure",
    v_str="Psp",
    e_str="PD-(C1-K9*PD)*L4_y*L4_y-PT",
)
self.L4 = Lag(
    u="Valve_y*(PSEL*PT+(1-PSEL)*Psp)",
    T=self.T4,
    K=1.0,
)
```

## Install and register

```bash
python -m pip install -e .
```

Register the external model before loading a case that contains a `TGOV5` sheet:

```python
import andes
from power_system_dynamic_models.andes import register_tgov5

register_tgov5()
system = andes.load("case_with_tgov5.xlsx", setup=False)
```

The tested benchmark parameters are in
[`models/tgov5_gumede2016/parameters.json`](models/tgov5_gumede2016/parameters.json).

## Documentation

- [TGOV5 modeling example](docs/TGOV5_MODEL_GUIDE.md) — ANDES-style overview, block
  diagram, equations, and implementation mapping.
- [TGOV5 generated reference](docs/TGOV5_MODEL_REFERENCE.rst) — parameters, variables,
  initialization, equations, services, discretes, and blocks generated from the model.
- [Validation audit](docs/TGOV5_AUDIT.md) — passed checks and remaining evidence gaps.
- [ANDES upstream plan](docs/UPSTREAMING.md) — source-file map, blockers, tests, and PR
  sequence for proposing the model to ANDES.

Regenerate the API-style model reference after changing model metadata or equations:

```bash
python tools/generate_model_reference.py
```

## Verification

The 2026-07-22 release audit reported:

- 22 source-mapping, initialization, physical-direction, delay, and time-step tests passed;
- 11 pressure-selector, evidence-hierarchy, and revision-integrity tests passed;
- standalone contract tests passed with unmodified public ANDES 1.10.1;
- packaged parameter defaults, core equations, and block inputs matched the audited research
  source.

GitHub Actions repeats the standalone tests on Python 3.11 and 3.12. These checks support a
source-consistent research release; they do not establish proprietary-code or field equivalence.

## Current model boundary

The adapter deliberately fails closed around the validated benchmark:

- `TD` must be 90 s because the current implementation constructs one scalar ANDES `Delay`;
- `K1 + ... + K8` must equal 1;
- `KI`, `TR1`, and `Psp` must be positive;
- initialization enforces the published pressure equilibrium and positive pressure-drop terms;
- active cross-compound HP/LP outputs are outside the implemented scope.

`PSEL` is a repository-only binary intervention selector, not a public TGOV5 parameter.
`PSEL=1` enables the pressure-coupled path. `PSEL=0` cuts the two outgoing pressure paths while
retaining the remaining states, controllers, limits, and delay for matched research ablation.

## Upstream status

This repository is an **upstream candidate**, not a merge-ready ANDES patch. Before proposing
it to `CURENT/andes`, the canonical model needs a standard-only data class, a maintainer-approved
strategy for arbitrary `TD`, explicit PSS/E DYR import mapping, an ANDES case fixture, and an
accepted validation comparison. See [docs/UPSTREAMING.md](docs/UPSTREAMING.md).

## Sources and provenance

The model was reconstructed from public descriptions and cross-checked against:

- IEEE PES-TR1, *Dynamic Models for Turbine-Governors in Power System Studies* (2013);
- PSS/E-29 public *Model Data Sheets*, TGOV5 block diagram and parameter inventory;
- N. S. Gumede, *Eskom-ZESA Interconnected Power System Modelling* (2016), Table C.0.7 and
  Figure C.0.2;
- public EMTP and PowerWorld TGOV5 descriptions.

Only original repository code and parameter transcriptions are distributed here. Third-party
documents retain their original rights and are cited rather than redistributed.

## Adding another model

The broad repository name leaves room for governors, exciters, load models, and controllers.
Each addition should include an implementation, model card, parameter provenance, initialization
checks, numerical tests, and an explicit list of unvalidated claims.

## License

MIT for this repository. A contribution to ANDES must also satisfy the upstream project's GPL-3.0
licensing and contribution requirements.
