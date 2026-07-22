# Preparing TGOV5 for ANDES upstream

## Current status

This repository is a documented and tested **upstream candidate**. It is not yet a merge-ready
patch for `CURENT/andes`. The implementation is intentionally narrower than a general TGOV5:
one aggregate shaft output and the Gumede benchmark's 90 s exact fuel delay.

## Target ANDES file map

An upstream contribution is expected to touch these areas of the ANDES repository:

| ANDES path | Required change |
|---|---|
| `andes/models/governor/tgov5.py` | Add the canonical `TGOV5Data`, `TGOV5Model`, and `TGOV5` classes |
| `andes/models/governor/__init__.py` | Export the new model classes |
| `andes/models/__init__.py` | Register `TGOV5` in the governor class list |
| `andes/io/psse-dyr.yaml` | Map the public TGOV5 DYR fields to ANDES inputs |
| `tests/` | Add import, initialization, equation, limiter, and trajectory tests |
| ANDES test cases | Add a redistributable workbook/DYR case with provenance |
| model documentation | Let ANDES generate the reference page from model metadata |

ANDES generates most model-reference documentation from `Model.doc()` and the parameter,
variable, service, discrete, and block metadata. The source docstring and every public parameter
therefore need meaningful `info`, `tex_name`, and `unit` fields.

## Blocking decisions before a pull request

### 1. Separate the standard model from research instrumentation

`PSEL` is not a public TGOV5 parameter. Move it out of the canonical upstream class. Keep the
pressure-ablation behavior in this repository as a research subclass or experimental wrapper.
`PBASE` is an ANDES adapter and should remain only if maintainers agree with the base-conversion
interface.

### 2. Resolve arbitrary `TD`

The current ANDES `Delay` block receives a scalar delay at construction. This adapter therefore
constructs 90 s and rejects other `TD` values. A general upstream model needs a maintainer-approved
solution for model rows with different delays, such as a supported vector delay, grouping by
delay, or a clearly documented upstream restriction. Do not silently replace the exact delay with
a rational approximation.

### 3. Decide the cross-compound scope

The current output combines all `K1`–`K8` stage coefficients into one mechanical-power signal.
The public model permits HP/LP cross-compound output allocation. Either implement and test the
second output using an ANDES-approved interface or obtain agreement that the first contribution
will be explicitly single-shaft only.

### 4. Add an authoritative import contract

Create a TGOV5 entry in `andes/io/psse-dyr.yaml` with the public DYR field order. Verify the
mapping with a redistributable case and round-trip assertions. Repository-only fields must not
shift or contaminate the standard DYR schema.

### 5. Establish accepted numerical evidence

The current tests establish source mapping, initialization, direction, delay behavior, and
time-step convergence. Upstream review should also include trajectory comparison against an
independent implementation or published benchmark accepted by the maintainers. Report tolerances,
time step, disturbance, base conversion, limit activity, and the exact validation domain.

### 6. Confirm contribution licensing

This repository is MIT licensed; ANDES is GPL-3.0 licensed. Before submitting, confirm that the
contributed files and any case data can be distributed under the upstream project's terms. Do not
include third-party PDFs or parameter data without redistribution permission.

## Recommended implementation sequence

1. Fork the current `CURENT/andes` default branch and create a focused `tgov5` feature branch.
2. Reduce the source to a standard-only TGOV5 class; keep research-only instrumentation here.
3. Resolve the exact-delay and cross-compound design questions with maintainers early.
4. Add model registration and PSS/E DYR mapping.
5. Add a small redistributable case and initialization/trajectory regression tests.
6. Run formatting, `flake8`, targeted tests, and `andes selftest` on the supported Python versions.
7. Generate and inspect the model reference from ANDES metadata.
8. Open a narrowly scoped pull request with the equation source, validation matrix, limitations,
   and follow-up work stated explicitly.

## Pull-request evidence checklist

- [ ] Public parameter inventory matches the cited TGOV5 source.
- [ ] No `PSEL` or other research-only field is in the canonical DYR contract.
- [ ] Turbine/system base conversion is tested.
- [ ] Initialization residuals pass for the fixture case.
- [ ] Rate limits, position limits, deadband, and anti-windup are exercised.
- [ ] Exact-delay behavior is tested for the accepted `TD` design.
- [ ] Cross-compound behavior is implemented or explicitly excluded with maintainer agreement.
- [ ] Independent trajectory comparison passes documented tolerances.
- [ ] Test data are redistributable and provenance is recorded.
- [ ] `flake8`, targeted tests, and `andes selftest` pass.
- [ ] Generated model-reference tables have complete descriptions and units.
- [ ] The PR avoids claims of proprietary-code equivalence or field validation.

## Official references for the contribution workflow

- [ANDES contributing guide](https://github.com/CURENT/andes/blob/master/CONTRIBUTING.rst)
- [ANDES model structure](https://docs.andes.app/en/latest/modeling/creating-models/model-structure.html)
- [ANDES testing models](https://docs.andes.app/en/latest/modeling/creating-models/testing-models.html)
- [ANDES TGOV1 example](https://docs.andes.app/en/latest/modeling/creating-models/example-tgov1.html)
