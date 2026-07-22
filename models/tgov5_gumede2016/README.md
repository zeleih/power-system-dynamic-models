# TGOV5 — Gumede 2016 benchmark adapter

## Model card

- **Type:** boiler–turbine–governor dynamic model
- **Runtime:** ANDES
- **Topology:** single shaft, one mechanical-power output
- **Parameter source:** Gumede (2016), Table C.0.7
- **Fuel delay:** exact 90 s time-domain delay
- **Validation level:** source-consistent synthetic/aggregate benchmark
- **Not validated:** proprietary-code equivalence, cross-compound units, plant-specific behavior

The parameter set is stored in `parameters.json`. It contains 49 public TGOV5 values and one
ANDES base-conversion adapter, `PBASE`. The separate `PSEL` switch is defined in code as a
research intervention and is intentionally not mixed into the public parameter transcription.

## Key pressure equations

```text
PT = PD - (C1 - K9*PD) * ms^2
CB * dPD/dt = Heat - ms
PSP = C3 + K13*MWD
```

For the transcribed benchmark, `C1=0.2` and `K9=0`, so increasing steam flow lowers throttle
pressure at fixed drum pressure. Initialization additionally enforces `C3 + K13*d0 = Psp`.

## Source

N. S. Gumede, *Eskom-ZESA interconnected power system modelling*, University of the
Witwatersrand, 2016. Parameter table: PDF page 86; block diagram: PDF page 83.

Public source URL:
https://wiredspace.wits.ac.za/server/api/core/bitstreams/9c43f1d9-9dca-48cd-9b10-23f375d120ef/content

