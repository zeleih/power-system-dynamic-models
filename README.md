# Power System Dynamic Models

Source-traceable dynamic models built for power-system research and model-fidelity studies.
The repository starts with a single-shaft TGOV5 reconstruction for ANDES and is structured
to accept additional governors, exciters, load models, and control models later.

## Available models

| Model | Platform | Status | Validated scope |
|---|---|---|---|
| TGOV5 (Gumede 2016 adapter) | ANDES | Research alpha | Single-shaft aggregate benchmark, exact 90 s fuel delay |

The TGOV5 implementation follows public block diagrams and equations. It is **not** official
ANDES code, proprietary PSS/E source code, a numerically identical commercial implementation,
or a field-validated plant model.

## Why this repository is named broadly

`power-system-dynamic-models` says what the collection is, remains searchable, and does not
lock the repository to TGOV5. Each future model should live in its own documented folder with
source mapping, parameter provenance, tests, and an explicit validation boundary.

## Install

```bash
python -m pip install -e .
```

The code was developed with Python 3.12 and an ANDES 1.9.3-based research fork. A clean-room
release check also passed against the unmodified public ANDES 1.10.1 package. GitHub CI is
configured for Python 3.11 and 3.12; its first remote run will start after upload.

## Register TGOV5 with ANDES

Call the registration function before loading an ANDES workbook that contains a `TGOV5` sheet:

```python
import andes
from power_system_dynamic_models.andes import register_tgov5

register_tgov5()
system = andes.load("case_with_tgov5.xlsx", setup=False)
```

The model uses turbine-base per-unit internal power and steam-flow signals. `PBASE` converts
mechanical output to the ANDES system base.

## Important model boundary

This first release is deliberately fail-closed around the published Gumede (2016) benchmark:

- `TD` must equal 90 s because the current ANDES `Delay` block is constructed with one scalar
  time-domain delay.
- `K1 + ... + K8` must equal 1.
- `KI`, `TR1`, and `Psp` must be positive.
- Initialization requires `C3 + K13*d0 = Psp` and a positive pressure-drop coefficient.
- Only a single mechanical output is supported; active cross-compound HP/LP output is outside
  this adapter's validated scope.

`PSEL` is a repository-added binary intervention selector, not a public TGOV5 parameter.
`PSEL=1` runs the pressure-coupled model. `PSEL=0` cuts the two outgoing pressure paths while
retaining the remaining states, controllers, limits, and delay for a matched causal comparison.
Use `PSEL=0` only for research ablation, not as a standard TGOV5 operating mode.

## Validation snapshot

The source workspace was re-audited on 2026-07-22:

- 22 TGOV5 source-mapping, initialization, physical-direction, exact-delay, and time-step tests passed.
- 11 pressure-selector, hierarchy-evidence, and revision-integrity tests passed.
- 5 standalone repository contract tests passed against public ANDES 1.10.1 in a clean environment.
- The packaged model matched the research source on all parameter defaults, core equations, and block inputs.
- No third-party PDFs, proprietary model code, paper drafts, or large simulation result archives are included here.

See [docs/TGOV5_AUDIT.md](docs/TGOV5_AUDIT.md) for the findings and remaining gaps.

## Sources and provenance

The implementation was reconstructed from public model descriptions and cross-checked against:

- IEEE PES-TR1, *Dynamic Models for Turbine-Governors in Power System Studies* (2013).
- PSS/E-29 public Model Data Sheets, TGOV5 block diagram and parameter inventory.
- N. S. Gumede, *Eskom-ZESA interconnected power system modelling* (2016), Table C.0.7 and Figure C.0.2.
- Public EMTP and PowerWorld TGOV5 documentation.

Only original repository code and parameter transcriptions are licensed under MIT. Third-party
documents retain their original rights and are linked or cited, not redistributed.

## Contributing another model

Every added model should provide:

1. an implementation under `src/power_system_dynamic_models/`;
2. a model card under `models/`;
3. source and parameter provenance;
4. initialization and direction checks;
5. numerical validation with a stated domain; and
6. an explicit list of unvalidated claims.

## License

MIT for the code in this repository. See [LICENSE](LICENSE).
