# LCC2T release audit

## Release claim

`LCC2T` is an independently written, reduced two-terminal LCC-HVDC model for ANDES power-flow
and electromechanical transient studies. The release claim is limited to the equations and
interfaces distributed in this repository.

## Evidence hierarchy

1. **Public white-box equations:** [PSAT 2.1.11](https://faraday1.ucd.ie/psat.html)
   `HVclass` and standard average-value LCC relationships establish the model layer and physical
   signs.
2. **Official host API:** the implementation follows the released ANDES 1.x
   [`ModelData`/`Model` API](https://docs.andes.app/en/v1.9.3/modeling/_generated/andes.core.model.Model.html),
   symbolic equations, services, blocks, discretes, metadata, and runtime registration
   conventions.
3. **Independent repository tests:** power balance, steady initialization, no-disturbance drift,
   event interfaces, non-reversing DC current, and idempotent registration are exercised without
   proprietary source code.
4. **Private research validation:** authorized commercial-software output was used outside this
   public repository to check external voltage/current/power behavior. Those files and internal
   controller inferences are not redistributed and are not release dependencies.

## Public checks

The repository test suite checks:

- every published input parameter has model metadata;
- power flow satisfies $P_r-P_i=R_{dc}I_d^2$;
- initial differential and algebraic residuals are small;
- a no-disturbance trajectory does not drift;
- the block event removes AC-terminal converter power and current remains non-negative;
- `register_lcc2t()` is idempotent; and
- the public parameter card matches the model defaults.

GitHub Actions repeats the suite on Python 3.11 and 3.12 with the public ANDES package range
declared in `pyproject.toml`.

## Public ANDES compatibility adapter

The research checkout that supplied the equations runs on an ANDES 2.0 development tree. This
public package targets the released ANDES 1.x API declared by the repository. The published source
therefore makes two interface-only adaptations:

- bus index parameters omit the development-only `status_parent` keyword; and
- AC-terminal equations use the ANDES 1.x device-status parameter `u` instead of the development
  tree's effective-status service `ue`.

Converter, DC-line, control, limiter, initialization, and event equations are otherwise retained.
The in-service case has `u=1`, so the AC/DC injections used by the documented model contract are
unchanged. Compatibility is verified against the public ANDES 1.10.1 package.

## Provenance and licensing

The implementation is original MIT-licensed repository code. Public third-party descriptions are
cited rather than copied. In particular, no PSAT source file, commercial-model source, licensed
manual, or private simulation output is included.

## Explicitly unvalidated

- valve-level switching, harmonics, or EMT behavior;
- a named physical HVDC project or its kV/ohm/mH parameters;
- commutation-failure detection and protection hardware;
- absolute equipment stress and overload settings;
- numerical parity with proprietary software; and
- a full sending-end AC network when the example uses a slack equivalent.

These limitations are part of the model contract, not deferred claims of equivalence.
