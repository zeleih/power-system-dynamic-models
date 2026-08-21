# Example: LCC2T two-terminal LCC-HVDC

This guide follows the equation-oriented organization used by the official ANDES modeling
examples. `LCC2T` is a positive-sequence, fundamental-frequency model for power-flow and
electromechanical transient studies. It connects two AC buses through quasi-steady converters
and a dynamic DC-current state.

## Model overview

```text
rectifier AC bus                         inverter AC bus
       │                                       │
       ▼                                       ▼
  firing-angle PI ─► rectifier ─► Rdc/Ldc ─► inverter ◄─ gamma order
       ▲                          Id state       │
       │                                         ├─ active-power delivery
 power/current order ─► VDCOL                   └─ reactive absorption

block ─► converter availability and DC-current decay
filter ─► independent fixed shunt compensation at both terminals
```

The rectifier terminal absorbs active power from its AC bus; the inverter terminal delivers
active power to its AC bus. Both converters absorb reactive power. Optional fixed filters or
capacitors inject reactive power proportional to squared terminal voltage.

## Sign convention and converter equations

Positive current flows from rectifier to inverter. With

$$
k=0.995\frac{3\sqrt{2}}{\pi}, \qquad c=\frac{3}{\pi},
$$

the average DC voltages are

$$
V_{dr}=k m_r V_r\cos\alpha-cX_{cr}I_d,
$$

$$
V_{di}=k m_i V_i\cos\gamma-cX_{ci}I_d.
$$

The dynamic DC line is

$$
L_{dc}\dot I_d=V_{dr}-V_{di}-R_{dc}I_d.
$$

`LCC2T` enforces a non-reversing current floor. During blocking, AC converter power is removed
and the residual DC current decays with the configured `tblock` time constant.

The active-power identities are

$$
P_r=V_{dr}I_d, \qquad P_i=V_{di}I_d,
$$

so

$$
P_r-P_i=R_{dc}I_d^2.
$$

The converter power-factor angles are obtained from

$$
V_{dr}=k m_rV_r\cos\phi_r, \qquad
V_{di}=k m_iV_i\cos\phi_i,
$$

and converter reactive absorption is

$$
Q_{r,conv}=k m_rV_rI_d\sin\phi_r,
\qquad
Q_{i,conv}=k m_iV_iI_d\sin\phi_i.
$$

The AC-bus reactive injections include shunt compensation:

$$
Q_r=Q_{r,conv}-z_f q_{cr}V_r^2,
\qquad
Q_i=Q_{i,conv}-z_f q_{ci}V_i^2,
$$

where `filter` supplies the command $z_f$.

## Control structure

`control=1` selects a filtered DC-current order. `control=2` selects a rate-limited active-power
order and converts it to a current order using rectifier DC voltage. Both paths pass through the
same three-segment VDCOL ceiling and rectifier current PI controller:

$$
e_I=I_{ord}-I_d,
\qquad
\dot X_r=K_i e_I,
\qquad
\cos\alpha=\operatorname{clip}(X_r+K_pe_I).
$$

The PI integrator freezes while blocked. `pcmd`, `icmd`, `block`, and `filter` are numerical
parameters so an ANDES `Alter` event can change them during simulation.

## ANDES implementation mapping

The model follows the official `Data`/`Model` composition pattern:

```python
class LCC2TData(ModelData):
    ...


class LCC2TModel(Model):
    ...


class LCC2T(LCC2TData, LCC2TModel):
    ...
```

Key implementation choices are:

| Physical/control part | ANDES component |
|---|---|
| AC terminal coupling | `ExtAlgeb` on bus angle and voltage equations |
| DC line current | `State` with non-reversing `AntiWindup` floor |
| VDCOL | `Piecewise` plus `GainLimiter` |
| Rectifier PI | `IntegratorAntiWindup` and output `GainLimiter` |
| Power recovery | `State` with `AntiWindupRate` |
| Initialization constraints | `InitChecker` and closed-form `v_str` values |

## Install and register

```bash
python -m pip install -e .
```

```python
import andes
from power_system_dynamic_models.andes import register_lcc2t

register_lcc2t()
system = andes.load("case_with_lcc2t.xlsx", setup=False)
```

Registration is process-global and idempotent. Register the model before loading a workbook that
contains an `LCC2T` sheet.

## Scope and limitations

Use this model for system-level studies of active-power interruption, DC-current dynamics,
converter reactive demand, filtering, blocking, and ramped recovery. Do not use it to infer:

- individual valve commutation or harmonics;
- EMT-scale commutation failure;
- proprietary controller or protection implementation details;
- equipment current/voltage stress without a physical per-link base conversion; or
- sending-grid dynamics when the rectifier bus is represented by an ideal slack source.

## See also

- [LCC2T generated reference](LCC2T_MODEL_REFERENCE.rst)
- [LCC2T validation audit](LCC2T_AUDIT.md)
- [LCC2T public model card](../models/lcc2t_public_2bus/README.md)
- [ANDES 1.9.3 Model API](https://docs.andes.app/en/v1.9.3/modeling/_generated/andes.core.model.Model.html)
- [ANDES model structure](https://docs.andes.app/en/v2.0.0/modeling/creating-models/model-structure.html)
