# LCC2T — public two-bus verification card

## Model card

- **Type:** positive-sequence two-terminal line-commutated HVDC model
- **Runtime:** ANDES power flow and time-domain simulation
- **Control:** rectifier constant-power or constant-current PI control
- **DC network:** one dynamic current state with series resistance and inductance
- **Inverter:** fixed extinction-angle order
- **Protection interface:** converter block, power-order ramp recovery, and independent
  filter/capacitor status
- **Parameter level:** dimensionless 100-MVA verification values
- **Validation level:** equation, initialization, power-balance, and event-contract tests
- **Not validated:** a named physical link, valve-level commutation, harmonics, EMT behavior,
  protection hardware, or equipment stress

The values in `parameters.json` are the model defaults used by the repository's two-bus
contract tests and example. They are deliberately not labeled with a project name or physical
line rating because no kV/ohm/mH conversion has been established for them.

## Sources

The implementation was written independently from public equations and checked against the
modeling level used by:

- [PSAT 2.1.11](https://faraday1.ucd.ie/psat.html) `HVclass` for a white-box
  electromechanical LCC reference;
- the public [ANDES equation-oriented model API](https://docs.andes.app/en/v1.9.3/modeling/_generated/andes.core.model.Model.html)
  and modeling documentation; and
- published descriptions of two-terminal LCC controls, including VDCOL, constant extinction
  angle, non-reversing DC current, blocking, and recovery.

No PSAT source file, proprietary model source, or commercial-software data is redistributed.

## Use

Register `LCC2T` before loading a workbook containing an `LCC2T` sheet:

```python
from power_system_dynamic_models.andes import register_lcc2t

register_lcc2t()
```

For a complete programmatic case, see
[`examples/run_lcc2t_two_bus.py`](../../examples/run_lcc2t_two_bus.py).
