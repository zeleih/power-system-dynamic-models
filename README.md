# Power System Dynamic Models

[![Tests](https://github.com/zeleih/power-system-dynamic-models/actions/workflows/test.yml/badge.svg)](https://github.com/zeleih/power-system-dynamic-models/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![ANDES](https://img.shields.io/badge/ANDES-tested%201.10.1-00599c.svg)](https://github.com/CURENT/andes)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Source-traceable, independently implemented dynamic models for power-system research. Each model
is packaged with ANDES-style symbolic source, a model card, public-source provenance, numerical
contracts, and an explicit list of claims that remain unvalidated.

> [!IMPORTANT]
> This is an independent research library. It is not official ANDES code, proprietary simulator
> source code, or a claim of commercial-model numerical parity.

## Model catalog

| Model | Category | Implemented scope | Model card | Documentation |
|---|---|---|---|---|
| **TGOV5** | Boiler–turbine–governor | Single shaft, boiler pressure, pressure controller, staged steam path, exact 90 s benchmark delay | [Gumede 2016](models/tgov5_gumede2016/README.md) | [Guide](docs/TGOV5_MODEL_GUIDE.md) · [Reference](docs/TGOV5_MODEL_REFERENCE.rst) · [Audit](docs/TGOV5_AUDIT.md) |
| **LCC2T** | Two-terminal LCC-HVDC | Average-value converters, dynamic DC current, rectifier PI, VDCOL, reactive demand, filters, block and ramped recovery | [Public two-bus card](models/lcc2t_public_2bus/README.md) | [Guide](docs/LCC2T_MODEL_GUIDE.md) · [Reference](docs/LCC2T_MODEL_REFERENCE.rst) · [Audit](docs/LCC2T_AUDIT.md) |

## Repository layout

```text
src/power_system_dynamic_models/andes/   original ANDES model implementations
models/<model_card>/                     parameter provenance and validated scope
docs/                                    modeling guides, generated references, audits
examples/                                minimal executable studies
tests/                                   standalone symbolic and numerical contracts
tools/                                   documentation and release helpers
```

The root README is a catalog. Model-specific equations, parameter assumptions, and evidence
boundaries live with each model rather than being mixed into a repository-wide claim.

## Install

```bash
python -m pip install -e .
```

The package declares `andes>=1.9.3,<2` and is tested in GitHub Actions on Python 3.11 and 3.12.

## Register external models

Register a model before loading an ANDES workbook that contains its sheet:

```python
import andes
from power_system_dynamic_models.andes import register_lcc2t, register_tgov5

register_tgov5()
register_lcc2t()
system = andes.load("case_with_external_models.xlsx", setup=False)
```

Registration is idempotent and does not modify the installed ANDES source tree.

## LCC2T quick start

`LCC2T` connects a rectifier-side AC bus and an inverter-side AC bus. From the receiving grid it
behaves as a controlled active-power injection that also consumes converter reactive power and
can receive independent shunt-filter compensation. It is not a negative load or a synchronous
generator model.

```python
system.add(
    "LCC2T",
    idx="DC1",
    busr=1,
    busi=2,
    p0=0.5,
    control=2,
    pmax=1.0,
)
system.add(
    "Alter",
    param_dict={
        "idx": "BLOCK_DC1",
        "t": 0.1,
        "model": "LCC2T",
        "dev": "DC1",
        "src": "block",
        "method": "=",
        "amount": 1.0,
    },
)
```

Run the complete two-bus example with:

```bash
python examples/run_lcc2t_two_bus.py
```

The public card is dimensionless and suitable for model verification. A study of a physical link
must establish its own AC/DC bases, converter ratios, commutation reactances, line R/L values,
control settings, filter steps, and protection sequence.

## TGOV5 quick start

TGOV5 represents a coupled governor, load controller, staged steam turbine, boiler-pressure
system, pressure controller, and delayed fuel/heat path. The published repository adapter is
restricted to the single-shaft Gumede (2016) aggregate benchmark and an exact 90 s delay.

```python
from power_system_dynamic_models.andes import register_tgov5

register_tgov5()
```

`PSEL` is a repository-only matched-intervention selector, not a public TGOV5 parameter. See the
[TGOV5 guide](docs/TGOV5_MODEL_GUIDE.md) before using it.

## Verification

```bash
python -m pip install -e '.[test]'
python -m pytest
python tools/generate_model_reference.py --model TGOV5
python tools/generate_model_reference.py --model LCC2T
```

The suite verifies metadata, registry behavior, initialization contracts, model-specific physical
identities, and time-domain behavior. Passing these tests supports the documented public model
contracts; it does not establish field validation or proprietary-code equivalence.

## Current validation boundaries

### TGOV5

- source-consistent single-shaft aggregate benchmark;
- no cross-compound HP/LP outputs;
- `TD` must be 90 s in the current adapter;
- no claim of plant-specific or proprietary PSS/E parity.

### LCC2T

- positive-sequence, fundamental-frequency, electromechanical-transient model;
- no valve switching, harmonics, EMT commutation failure, or protection hardware;
- no claim that the public two-bus parameters describe a physical HVDC project;
- no equipment-stress conclusion without per-link kV/ohm/mH calibration; and
- a slack source represents an ideal external sending grid in the minimal example.

## Sources and provenance

Models are reconstructed from public equations and descriptions, then implemented independently
using the official ANDES symbolic-model API. Public references are cited in each model card and
audit. Third-party source files, licensed manuals, proprietary model code, and private simulation
outputs are not redistributed.

The primary references currently include:

- IEEE PES-TR1 and public TGOV5 model data sheets;
- N. S. Gumede (2016), TGOV5 aggregate benchmark;
- [PSAT 2.1.11](https://faraday1.ucd.ie/psat.html) `HVclass` and standard average-value
  LCC-HVDC equations; and
- the official [ANDES 1.9.3 Model API](https://docs.andes.app/en/v1.9.3/modeling/_generated/andes.core.model.Model.html)
  and [model-structure guide](https://docs.andes.app/en/v2.0.0/modeling/creating-models/model-structure.html).

## Adding another model

Every addition should include:

1. an original implementation under `src/power_system_dynamic_models/andes/`;
2. an idempotent runtime registration function;
3. a model card and parameter-provenance record under `models/`;
4. an ANDES-style guide and generated model reference;
5. symbolic, initialization, numerical, and event tests; and
6. an explicit list of unsupported or unvalidated claims.

See [docs/UPSTREAMING.md](docs/UPSTREAMING.md) for the additional work required before proposing
a model to the official ANDES repository.

## License

MIT for this repository. A contribution to ANDES must separately satisfy the upstream project's
GPL-3.0 licensing and contribution requirements.
