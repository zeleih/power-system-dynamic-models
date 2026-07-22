# Example: TGOV5 Boiler-Turbine Governor

This example documents a source-traceable TGOV5 implementation for ANDES using the same
organization as the official ANDES modeling examples. TGOV5 is useful for studies in which the
governor response, steam path, boiler pressure, and fuel/heat dynamics must remain coupled.

## Model Overview

The implemented TGOV5 model consists of:

- a speed governor with lead-lag response;
- a power-order controller with rate and position limits;
- a rate- and position-limited steam valve;
- four staged steam-path lags and weighted mechanical output;
- drum- and throttle-pressure dynamics;
- a pressure controller with output limiting and anti-windup;
- fuel-system and water-wall lags followed by an exact time delay; and
- turbine-base to ANDES system-base conversion at the mechanical output.

The class supports one aggregate mechanical output. The public TGOV5 formulation can represent
cross-compound HP/LP outputs, but that topology is not implemented or validated here.

## Block Diagram

```text
                                  ┌──────── measured electrical power ────────┐
                                  │                                           │
 ω - ωref ─► K(1+sT2)/(1+sT1) ─┐ │                                           ▼
                                ▼ │     rate/position limits        ┌─────────────────┐
 MW demand ─► frequency bias ─► power order ───────────────────────►│ valve actuator  │
                         ▲        ▲                                 └────────┬────────┘
                         │        │                                          │ × PT
 pressure set point ─────┘        └── pressure error/deadband                ▼
                                                                    ┌─────────────────┐
                                      Heat ─► drum pressure ─► PT ─►│ T4,T5,T6,T7     │
                                        ▲                           │ turbine stages   │
                                        │                           └────────┬────────┘
                                        │                                    ▼
 PSP-PT ─► pressure controller ─► fuel ─► fuel lag ─► water wall ─► delay    Pm
```

`PSEL` appears only in this research repository. With `PSEL=1`, throttle pressure acts on both
the steam-flow and pressure-error paths. With `PSEL=0`, those two outgoing pressure edges are
replaced for a matched causal ablation; it is not a standard TGOV5 operating mode.

## Mathematical Equations

The principal turbine and pressure equations are

$$
C_B\dot P_D = H-m_s,
$$

$$
P_T=P_D-(C_1-K_9P_D)m_s^2,
$$

$$
m_s=\frac{1}{1+sT_4}\left[v\left(S_P P_T+(1-S_P)P_{SP0}\right)\right],
$$

and

$$
P_m=(K_1+K_2)y_4+(K_3+K_4)y_5+(K_5+K_6)y_6+(K_7+K_8)y_7.
$$

Here $P_D$ is drum pressure, $P_T$ is throttle pressure, $H$ is delayed heat input,
$m_s=y_4$ is steam flow, $v$ is valve position, and $S_P$ denotes the repository-only `PSEL`
selector. The benchmark is initialized with $\sum_{i=1}^{8}K_i=1$.

The demand and power-order path is

$$
D^*=D-B\Delta\omega,
$$

$$
P_{SP}=C_3+K_{13}D,
$$

$$
e_P=S_P(P_{SP}-P_T),
$$

$$
e_o=D^*-(C_2+K_{12}P_{SP}P_o)\operatorname{DB}(e_P)
    -P_{e,meas}-K_LP_o,
$$

$$
\dot P_o=\operatorname{sat}_{R_{MIN}}^{R_{MAX}}(K_{14}e_o),
\qquad L_{MIN}\le P_o\le L_{MAX}.
$$

The pressure-controller transfer function is

$$
G_P(s)=K_I\frac{(1+sT_I)(1+sT_R)}{s(1+sT_{R1})}.
$$

It is realized exactly as an integrator, one lag, and algebraic feedthrough. With

$$
a=\frac{T_IT_R}{T_{R1}}, \qquad
q=T_I+T_R-T_{R1}-a,
$$

the realization is

$$
T_{R1}\dot\xi=e_P-\xi,\qquad \dot\eta=e_P,
$$

$$
c_{raw}=K_I(\eta+a e_P+q\xi),\qquad
c_{out}=\operatorname{sat}_{C_{MIN}}^{C_{MAX}}(c_{raw}).
$$

The fuel/heat path is

$$
u_F=c_{out}+K_{11}D^*+K_{10}m_s,
$$

$$
H(s)=e^{-sT_D}\frac{1}{1+sT_W}\frac{1}{1+sT_F}u_F(s).
$$

In the current adapter, the constructed ANDES time delay is fixed at 90 s and initialization
rejects any other `TD` value.

## Equation-Based Implementation

The pressure loop is written explicitly because it is a nonlinear DAE relationship rather than
a simple cascade of standard linear blocks:

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
self.PSP = Algeb(
    info="Pressure set point",
    v_str="Psp",
    e_str="C3+K13*MWD-PSP",
)
```

The power-order and valve rates are also explicit equations so the public rate limits and
position anti-windup behavior can be inspected independently.

**Key observations:**

- equation strings expose the modeled sign conventions;
- initial services compute the steady-state pressure and controller coordinates;
- `InitChecker` rejects unsupported or physically inconsistent parameter sets;
- limiter flags select the interior or saturated rate without hiding the active equation.

## Block-Based Implementation

Standard linear elements use ANDES blocks:

```python
self.GovLL = LeadLag(
    u=self.dw,
    T1=self.T2,
    T2=self.T1,
    K=self.K,
)
self.L4 = Lag(
    u="Valve_y*(PSEL*PT+(1-PSEL)*Psp)",
    T=self.T4,
    K=1.0,
)
self.FuelDelay = Delay(
    u=self.Water.y,
    mode="time",
    delay=self.SOURCE_FUEL_DELAY_SECONDS,
)
```

**Key observations:**

- `LeadLag` maps directly to the public governor transfer function;
- `Lag` blocks represent the steam, measurement, fuel, water-wall, and controller states;
- `IntegratorAntiWindup` enforces power-order and valve position bounds;
- `Delay` preserves the exact benchmark delay instead of substituting a low-order lag.

## Comparison of Approaches

| Model part | Equation-based | Block-based | Reason for choice |
|---|---:|---:|---|
| Nonlinear pressure DAE | Yes | No | The flow-squared coupling is explicit and auditable |
| Rate-limit selection | Yes | Discrete limiter only | Public saturation behavior remains visible |
| Pressure controller | Mixed | Mixed | Exact transfer function plus custom anti-windup bounds |
| Steam and fuel lags | No | Yes | Direct correspondence to standard first-order blocks |
| Exact fuel delay | No | Yes | Uses ANDES time-domain history handling |

## Guidelines

- Keep the canonical TGOV5 data class limited to public model parameters when preparing an
  ANDES contribution; move `PSEL` into a separate research subclass.
- Preserve turbine-base signals internally and convert only at the ANDES interface.
- Fail closed when a parameter set violates initialization identities or an unsupported topology.
- Validate rate and position limit activation in addition to small-signal behavior.
- Compare trajectories against an accepted independent reference before claiming numerical
  implementation equivalence.
- Add a PSS/E DYR mapping and an ANDES case fixture before requesting upstream review.

## Complete Source Code

The implementation is in
[`src/power_system_dynamic_models/andes/tgov5.py`](../src/power_system_dynamic_models/andes/tgov5.py).

Related files:

- [`models/tgov5_gumede2016/parameters.json`](../models/tgov5_gumede2016/parameters.json) —
  benchmark values;
- [`tests/test_tgov5_contract.py`](../tests/test_tgov5_contract.py) — standalone contracts;
- [`TGOV5_MODEL_REFERENCE.rst`](TGOV5_MODEL_REFERENCE.rst) — generated ANDES reference;
- [`UPSTREAMING.md`](UPSTREAMING.md) — ANDES integration checklist.

## See Also

- [ANDES model structure](https://docs.andes.app/en/latest/modeling/creating-models/model-structure.html)
- [ANDES TGOV1 modeling example](https://docs.andes.app/en/latest/modeling/creating-models/example-tgov1.html)
- [ANDES blocks](https://docs.andes.app/en/latest/modeling/components/blocks.html)
- [ANDES discrete components](https://docs.andes.app/en/latest/modeling/components/discrete.html)
- [Validation audit](TGOV5_AUDIT.md)
