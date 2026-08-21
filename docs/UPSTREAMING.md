# Preparing repository models for ANDES upstream

## Current status

This repository contains documented and tested **upstream candidates**. It is not a merge-ready
patch for `CURENT/andes`. Runtime registration is appropriate for independent research use, but an
official contribution additionally needs maintainer-approved data contracts, case fixtures,
import mappings, and validation evidence.

## Common ANDES contribution pattern

For each model, an upstream contribution normally needs:

| ANDES area | Required change |
|---|---|
| `andes/models/<category>/<model>.py` | Canonical `Data`, `Model`, and composed classes |
| category `__init__.py` | Export model classes |
| `andes/models/__init__.py` | Register the model in the category list |
| importer maps | Map a documented public input format when applicable |
| `andes/cases/` or test fixtures | Add a redistributable, provenance-locked case |
| tests | Add import, initialization, equation, limiter, event, and trajectory checks |
| generated documentation | Let ANDES generate the reference from model metadata |

ANDES generates model-reference documentation from `Model.doc()` and parameter, variable,
service, discrete, and block metadata. Public fields therefore need meaningful `info`, `tex_name`,
and `unit` values.

## TGOV5 blockers

1. Remove the repository-only `PSEL` research selector from a canonical standard class.
2. Resolve arbitrary `TD`; the current adapter constructs the Gumede benchmark's exact 90 s
   delay and rejects other values.
3. Implement or explicitly exclude cross-compound HP/LP output allocation with maintainer
   agreement.
4. Add an authoritative public DYR field mapping and redistributable fixture.
5. Add an independent trajectory comparison accepted by maintainers.

## LCC2T blockers

1. Agree on whether a new two-terminal LCC belongs under the existing `acdc` category or a new
   DC-transmission category.
2. Replace repository event parameters with the upstream project's preferred control/protection
   interface, including block, power modulation, and filter switching.
3. Define an accepted physical-base contract for DC voltage/current, line R/L, converter ratios,
   and commutation reactances.
4. Add a redistributable two-area case that exercises AC/DC active and reactive signs, VDCOL,
   blocking, non-reversing current, and ramped recovery.
5. Add an independent white-box trajectory comparison. A proprietary waveform may be secondary
   evidence but cannot be the only upstream oracle.
6. Decide whether commutation-failure supervision is explicitly outside the model or provided by
   a separate, documented protection model.

## Contribution sequence

1. Discuss the target category, scope, and input contract with ANDES maintainers.
2. Create a focused feature branch from the current official default branch.
3. Reduce the model to standard-only parameters and interfaces.
4. Add registration, importer mapping where applicable, and a small redistributable fixture.
5. Add initialization, physical-identity, limiter, event, and independent-trajectory tests.
6. Run formatting, `flake8`, targeted tests, and `andes selftest` on supported Python versions.
7. Generate and inspect model-reference tables from ANDES metadata.
8. Open a narrowly scoped pull request with sources, tolerances, limitations, and follow-up work.

## Pull-request evidence checklist

- [ ] Public parameter inventory matches cited sources.
- [ ] Repository-only interventions are excluded from the canonical input contract.
- [ ] Power/current/impedance base conversions are documented and tested.
- [ ] Initialization residuals pass for a redistributable fixture.
- [ ] Limiters, anti-windup, and event transitions are exercised.
- [ ] An independent trajectory comparison passes stated tolerances.
- [ ] Test data provenance and redistribution rights are recorded.
- [ ] `flake8`, targeted tests, and `andes selftest` pass.
- [ ] Generated model-reference tables have complete descriptions and units.
- [ ] The PR avoids proprietary-code, field-validation, and unsupported-equivalence claims.

## Licensing

This repository is MIT licensed; ANDES is GPL-3.0 licensed. Before submitting, confirm that the
contributed source and fixture data can be distributed under upstream terms. Do not include
third-party PDFs, licensed manuals, commercial-model source, or private simulation outputs.

## Official references

- [ANDES contributing guide](https://github.com/CURENT/andes/blob/master/CONTRIBUTING.rst)
- [ANDES model structure](https://docs.andes.app/en/latest/modeling/creating-models/model-structure.html)
- [ANDES testing models](https://docs.andes.app/en/latest/modeling/creating-models/testing-models.html)
- [ANDES TGOV1 example](https://docs.andes.app/en/latest/modeling/creating-models/example-tgov1.html)
