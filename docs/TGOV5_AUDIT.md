# TGOV5 audit — 2026-07-22

## Outcome

The implementation is suitable for release as an **auditable research reconstruction** of a
single-shaft TGOV5 benchmark in ANDES. It is not ready to be advertised as a universal TGOV5
drop-in or as plant-validated commercial-model parity.

## What passed

- Public parameter transcription and equation-direction checks for the Gumede 2016 set.
- Cryptographic binding of the original benchmark workbook, builder, and parameter bundle in
  the source research workspace.
- DAE initialization, pressure-drop identity, heat/steam equilibrium, and limiter interior checks.
- Positive and negative disturbance direction checks.
- Exact-delay behavior and 1/60 s versus 1/120 s time-step convergence checks.
- Fail-closed rejection of an AEMO/PowerFactory parameter set whose pressure convention gives
  `C1 - K9*Psp < 0` under the implemented PSS/E-29 equation.
- Binary pressure-path selector contract used by matched pressure-on/off experiments.

The re-audit executed 22 core/source-gate tests and 11 revision/selector tests; all 33 passed.
The extracted release then passed 5 standalone contract tests in a clean Python 3.12 environment
with the unmodified public ANDES 1.10.1 package. A semantic extraction check found no differences
in parameter names/defaults, core algebraic and differential equations, or block inputs relative
to the audited research source.

## Findings fixed in the release packaging

- The repository name is broader than the first model so later user-built models can be added
  without renaming or creating unrelated repositories.
- The README distinguishes the 49 public TGOV5 values, the ANDES `PBASE` adapter, and the
  repository-only `PSEL` intervention selector.
- The 90 s delay restriction is presented as a benchmark boundary rather than hidden behind a
  generic TGOV5 name.
- Paper sources, private audit material, third-party PDFs, large trajectory arrays, and obsolete
  parameter artifacts are excluded from the repository.

## Remaining gaps

1. **General delay support.** The class constructs one 90 s `Delay`; it rejects other `TD` values.
   A general adapter needs a supported per-row delay strategy or separate delay classes.
2. **Cross-compound output.** Only one mechanical output is implemented and validated.
3. **Commercial parity.** No numerical equivalence claim is made against proprietary PSS/E code.
4. **Field validation.** Gumede's model is an aggregate benchmark fitted to historical system
   measurements; this repository has no independent plant test or parameter-identification data.
5. **Pressure-selector semantics.** `PSEL=0` is a causal ablation, not a recognized standard-model
   mode and must not be used as one.

## Release language

Use: “source-consistent, single-shaft TGOV5 research reconstruction for ANDES, validated on the
Gumede 2016 aggregate benchmark.”

Avoid: “official TGOV5,” “identical to PSS/E,” “validated for real plants,” or “general TGOV5
implementation.”
