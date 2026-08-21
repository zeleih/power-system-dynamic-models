"""Reduced two-terminal line-commutated HVDC model for ANDES.

This positive-sequence model is intended for electromechanical transient and
frequency-response studies.  Converter valves and individual commutations are
outside its scope.
"""

from __future__ import annotations

from andes.core import (
    Algeb,
    ConstService,
    ExtAlgeb,
    IdxParam,
    Model,
    ModelData,
    NumParam,
    Piecewise,
    State,
)
from andes.core.block import GainLimiter, IntegratorAntiWindup
from andes.core.discrete import AntiWindup, AntiWindupRate
from andes.core.service import InitChecker


class LCC2TData(ModelData):
    """Input data for a two-terminal LCC-HVDC link."""

    def __init__(self):
        super().__init__()

        self.busr = IdxParam(
            model="ACNode",
            info="rectifier-side AC bus",
            mandatory=True,
        )
        self.busi = IdxParam(
            model="ACNode",
            info="inverter-side AC bus",
            mandatory=True,
        )

        self.p0 = NumParam(
            default=0.5,
            info="initial rectifier DC power on system base",
            unit="p.u.",
            non_negative=True,
        )
        self.control = NumParam(
            default=2,
            info="rectifier control mode: 1 constant current, 2 constant power",
            vtype=int,
        )
        self.i0 = NumParam(
            default=0.5,
            info="initial DC-current order for constant-current control",
            unit="p.u.",
            non_negative=True,
        )
        self.rdc = NumParam(
            default=0.0625,
            info="DC line resistance on system base",
            unit="p.u.",
            non_zero=True,
        )
        self.ldc = NumParam(
            default=0.2,
            info="DC line and smoothing inductance",
            unit="p.u.-s",
            non_zero=True,
        )
        self.xcr = NumParam(
            default=0.1345,
            info="rectifier commutation reactance",
            unit="p.u.",
            non_negative=True,
        )
        self.xci = NumParam(
            default=0.1257,
            info="inverter commutation reactance",
            unit="p.u.",
            non_negative=True,
        )
        self.mr = NumParam(
            default=1.25,
            info="rectifier converter-transformer ratio",
            non_zero=True,
        )
        self.mi = NumParam(
            default=1.25,
            info="inverter converter-transformer ratio",
            non_zero=True,
        )

        self.alpha_min = NumParam(
            default=5.0,
            info="minimum rectifier firing angle",
            unit="degree",
        )
        self.alpha_max = NumParam(
            default=120.0,
            info="maximum rectifier firing angle",
            unit="degree",
        )
        self.gamma = NumParam(
            default=18.0,
            info="inverter extinction-angle order",
            unit="degree",
        )
        self.kp = NumParam(
            default=25.0,
            info="rectifier current-controller proportional gain",
            tex_name="K_p",
        )
        self.ki = NumParam(
            default=20.0,
            info="rectifier current-controller integral gain",
            non_negative=True,
            tex_name="K_i",
        )

        self.vdcn = NumParam(
            default=1.6,
            info="DC voltage base used by VDCOL",
            unit="p.u.",
            non_zero=True,
        )
        self.vdc_low = NumParam(
            default=0.50,
            info="VDCOL low-voltage breakpoint",
            unit="p.u.",
        )
        self.vdc_high = NumParam(
            default=0.90,
            info="VDCOL high-voltage breakpoint",
            unit="p.u.",
        )
        self.idc_low = NumParam(
            default=0.10,
            info="VDCOL current ceiling below low breakpoint",
            unit="p.u.",
        )
        self.idc_high = NumParam(
            default=2.00,
            info="VDCOL current ceiling above high breakpoint",
            unit="p.u.",
        )

        self.pcmd = NumParam(
            default=1.0,
            info="active-power order multiplier; may be changed by Alter",
        )
        self.icmd = NumParam(
            default=1.0,
            info="DC-current order multiplier; may be changed by Alter",
        )
        self.tiref = NumParam(
            default=0.02,
            info="DC-current order tracking time constant",
            unit="s",
            non_zero=True,
        )
        self.block = NumParam(
            default=0.0,
            info="converter block command: 0 normal, 1 blocked",
            unit="bool",
        )
        self.filter = NumParam(
            default=1.0,
            info="filter/capacitor status: 0 disconnected, 1 connected",
            unit="bool",
        )
        self.pmax = NumParam(
            default=1.0,
            info="maximum recovered power order",
            unit="p.u.",
        )
        self.tpref = NumParam(
            default=0.02,
            info="power-order tracking time constant",
            unit="s",
            non_zero=True,
        )
        self.rup = NumParam(
            default=0.25,
            info="maximum power-order recovery rate",
            unit="p.u./s",
            non_negative=True,
        )
        self.rdn = NumParam(
            default=5.0,
            info="positive magnitude of maximum power-order reduction rate",
            unit="p.u./s",
            non_negative=True,
        )
        self.tblock = NumParam(
            default=0.02,
            info="blocked-state DC residual-current decay time constant",
            unit="s",
            non_zero=True,
        )

        self.qcr = NumParam(
            default=0.0,
            info="rectifier fixed filter/capacitor compensation at 1 p.u. voltage",
            unit="p.u.",
        )
        self.qci = NumParam(
            default=0.0,
            info="inverter fixed filter/capacitor compensation at 1 p.u. voltage",
            unit="p.u.",
        )


class LCC2TModel(Model):
    """Quasi-steady converters, dynamic DC current and rectifier PI control."""

    def __init__(self, system, config):
        super().__init__(system, config)
        self.group = "StaticACDC"
        self.flags.update({"pflow": True, "tds": True})
        self.flags.nr_iter = True

        self.ar = ExtAlgeb(
            model="Bus",
            src="a",
            indexer=self.busr,
            info="rectifier AC-bus voltage angle",
            tex_name=r"\theta_r",
            ename="P_r",
        )
        self.vr = ExtAlgeb(
            model="Bus",
            src="v",
            indexer=self.busr,
            info="rectifier AC-bus voltage magnitude",
            tex_name="V_r",
            ename="Q_r",
        )
        self.ai = ExtAlgeb(
            model="Bus",
            src="a",
            indexer=self.busi,
            info="inverter AC-bus voltage angle",
            tex_name=r"\theta_i",
            ename="P_i",
        )
        self.vi = ExtAlgeb(
            model="Bus",
            src="v",
            indexer=self.busi,
            info="inverter AC-bus voltage magnitude",
            tex_name="V_i",
            ename="Q_i",
        )

        self.kconv = ConstService(
            v_str="0.995*3*sqrt(2)/pi",
            info="six-pulse average-voltage coefficient",
        )
        self.ccomm = ConstService(
            v_str="3/pi",
            info="commutation-drop coefficient",
        )
        self.cosa_lo = ConstService(
            v_str="cos(alpha_max*pi/180)",
            info="lower cos(alpha) limit",
        )
        self.cosa_hi = ConstService(
            v_str="cos(alpha_min*pi/180)",
            info="upper cos(alpha) limit",
        )
        self.cosg = ConstService(
            v_str="cos(gamma*pi/180)",
            info="cosine of inverter extinction-angle order",
        )
        self.rdn_neg = ConstService(
            v_str="-rdn",
            info="negative power-order ramp limit",
        )
        self.tone = ConstService(
            v_str="1",
            info="unit state time constant",
        )
        self.vdcol_slope = ConstService(
            v_str="(idc_high-idc_low)/(vdc_high-vdc_low)",
            info="VDCOL linear-segment slope",
        )
        self.uI = ConstService(
            v_str="Indicator(control < 1.5)",
            info="constant-current control selector",
        )
        self.uP = ConstService(
            v_str="Indicator(control >= 1.5)",
            info="constant-power control selector",
        )
        self._control_check = InitChecker(
            u=self.control,
            lower=0.5,
            upper=2.5,
            error_out=True,
            info="control must be 1 (current) or 2 (power)",
        )

        self._angle_span = ConstService(
            v_str="cosa_hi-cosa_lo",
            info="positive cosine-angle limit span",
        )
        self._angle_check = InitChecker(
            u=self._angle_span,
            lower=1e-9,
            error_out=True,
            info="alpha_min must be less than alpha_max",
        )
        self._vdcol_span = ConstService(
            v_str="vdc_high-vdc_low",
            info="positive VDCOL voltage span",
        )
        self._vdcol_check = InitChecker(
            u=self._vdcol_span,
            lower=1e-9,
            error_out=True,
            info="vdc_high must exceed vdc_low",
        )
        self._p_headroom = ConstService(
            v_str="pmax-p0",
            info="initial power-order headroom",
        )
        self._pmax_check = InitChecker(
            u=self._p_headroom,
            lower=0.0,
            error_out=True,
            info="pmax must not be less than p0",
        )

        self.Ida = Algeb(
            info="DC current algebraic interface",
            tex_name="I_d^a",
            v_str="p0/(kconv*mi*vi*cosg)",
            diag_eps=True,
        )
        self.Vdr = Algeb(
            info="rectifier DC voltage",
            tex_name="V_{dr}",
            v_str="p0/(Ida+1e-8)",
            e_str="kconv*mr*vr*cosa-ccomm*xcr*Ida-Vdr",
            diag_eps=True,
        )
        self.Vdi = Algeb(
            info="inverter DC voltage",
            tex_name="V_{di}",
            v_str="kconv*mi*vi*cosg-ccomm*xci*Ida",
            e_str="kconv*mi*vi*cosg-ccomm*xci*Ida-Vdi",
            diag_eps=True,
        )
        self.cosa = Algeb(
            info="cosine of rectifier firing angle",
            tex_name=r"\cos\alpha",
            v_str="cos(15*pi/180)",
            diag_eps=True,
        )
        self.phir = Algeb(
            info="rectifier fundamental power-factor angle",
            tex_name=r"\phi_r",
            v_str="0.35",
            e_str="Vdr-kconv*mr*vr*cos(phir)",
            diag_eps=True,
        )
        self.phii = Algeb(
            info="inverter fundamental power-factor angle",
            tex_name=r"\phi_i",
            v_str="0.35",
            e_str="Vdi-kconv*mi*vi*cos(phii)",
            diag_eps=True,
        )

        self.Pref = State(
            info="rate-limited active-power order",
            tex_name="P_{ref}",
            v_str="p0",
            e_str=(
                "1.0*Indicator(dae_t < 0)*(p0-Pref)"
                "+1.0*Indicator(dae_t >= 0)"
                "*((p0*pcmd*(1-block)-Pref)/tpref)"
            ),
            t_const=self.tone,
        )
        self.PrefLimiter = AntiWindupRate(
            u=self.Pref,
            lower=0.0,
            upper=self.pmax,
            rate_lower=self.rdn_neg,
            rate_upper=self.rup,
            info="power-order magnitude and recovery-rate limits",
        )
        self.Pref.discrete = self.PrefLimiter

        self.Iref = State(
            info="filtered DC-current order",
            tex_name="I_{ref}",
            v_str="i0",
            e_str=(
                "1.0*Indicator(dae_t < 0)*(i0-Iref)"
                "+1.0*Indicator(dae_t >= 0)"
                "*((i0*icmd-Iref)/tiref)"
            ),
            t_const=self.tone,
        )

        self.prefeff = Algeb(
            info="power order used in power flow or time domain",
            tex_name="P_{ref}^{eff}",
            v_str="p0",
            e_str=(
                "1.0*Indicator(dae_t < 0)*p0"
                "+1.0*Indicator(dae_t >= 0)*Pref-prefeff"
            ),
            diag_eps=True,
        )
        self.vdcnorm = Algeb(
            info="normalized inverter DC voltage for VDCOL",
            tex_name="v_{di}",
            v_str="1",
            e_str="Vdi/vdcn-vdcnorm",
            diag_eps=True,
        )
        self.VDCOL = Piecewise(
            u=self.vdcnorm,
            points=("vdc_low", "vdc_high"),
            funs=(
                "idc_low",
                "idc_low+vdcol_slope*(vdcnorm-vdc_low)",
                "idc_high",
            ),
            info="voltage-dependent DC current ceiling",
            tex_name="I_{VDCOL}",
        )
        self.IordRaw = Algeb(
            info="unlimited rectifier current order",
            tex_name="I_{ord}^{raw}",
            v_str="p0/(Vdr+1e-8)",
            e_str="uI*Iref+uP*prefeff/(Vdr+1e-8)-IordRaw",
            diag_eps=True,
        )
        self.IordLimiter = GainLimiter(
            u=self.IordRaw,
            K=1.0,
            R=1.0,
            lower=0.0,
            upper=self.VDCOL_y,
            info="non-negative current order limited by VDCOL",
        )
        self.Iord = Algeb(
            info="limited DC current order",
            tex_name="I_{ord}",
            v_str="p0/(Vdr+1e-8)",
            e_str="IordLimiter_y-Iord",
            diag_eps=True,
        )
        self.ierr = Algeb(
            info="rectifier current-control error",
            tex_name="e_I",
            v_str="0",
            e_str="Iord-Ida-ierr",
            diag_eps=True,
        )
        self.Xr = IntegratorAntiWindup(
            u="(1-block)*ierr",
            T=1.0,
            K=self.ki,
            y0=self.cosa,
            lower=self.cosa_lo,
            upper=self.cosa_hi,
            info="rectifier PI integral state",
            tex_name="X_r",
            no_warn=True,
        )
        self.Xr.y.e_str = (
            "1.0*Indicator(dae_t < 0)*(cosa-Xr_y)"
            "+1.0*Indicator(dae_t >= 0)*ki*(1-block)*ierr"
        )
        self.CosaRaw = Algeb(
            info="unlimited rectifier PI output",
            tex_name=r"\cos\alpha^{raw}",
            v_str="cosa",
            e_str=(
                "1.0*Indicator(dae_t < 0)*(cosa-CosaRaw)"
                "+1.0*Indicator(dae_t >= 0)*(Xr_y+kp*ierr-CosaRaw)"
            ),
            diag_eps=True,
        )
        self.CosaLimiter = GainLimiter(
            u=self.CosaRaw,
            K=1.0,
            R=1.0,
            lower=self.cosa_lo,
            upper=self.cosa_hi,
            info="rectifier firing-angle output limiter",
        )

        self.cosa.e_str = (
            "1.0*Indicator(dae_t < 0)"
            "*(uI*(i0-Ida)+uP*(p0-Vdr*Ida))"
            "+1.0*Indicator(dae_t >= 0)*(CosaLimiter_y-cosa)"
        )
        self.Id = State(
            info="DC line current state",
            tex_name="I_d",
            unit="p.u.",
            v_str="Ida",
            e_str=(
                "1.0*Indicator(dae_t < 0)*(Ida-Id)"
                "+1.0*Indicator(dae_t >= 0)"
                "*((1-block)*(Vdr-Vdi-rdc*Id)"
                "-block*(ldc/tblock)*Id)"
            ),
            t_const=self.ldc,
        )
        # Thyristor current cannot reverse.  The lower anti-windup bound is
        # especially important during restart: if the inverter-side open-
        # circuit voltage temporarily exceeds the maximum rectifier voltage,
        # a purely differential line equation would otherwise drive Id below
        # zero and make the converter algebraic equations non-physical.
        self.IdLimiter = AntiWindup(
            u=self.Id,
            lower=0.0,
            upper=self.idc_high,
            no_upper=True,
            no_warn=True,
            state=self.Id,
            info="non-reversing LCC DC-current floor",
        )
        self.Id.discrete = self.IdLimiter
        self.Ida.e_str = (
            "1.0*Indicator(dae_t < 0)*(Vdr-Vdi-rdc*Ida)"
            "+1.0*Indicator(dae_t >= 0)*(Id-Ida)"
        )

        self.run = Algeb(
            info="converter availability at the AC terminals",
            tex_name="z_{run}",
            v_str="1",
            e_str=(
                "1.0*Indicator(dae_t < 0)"
                "+1.0*Indicator(dae_t >= 0)*(1-block)-run"
            ),
            diag_eps=True,
        )
        self.pr = Algeb(
            info="unblocked rectifier active-power absorption",
            tex_name="P_r",
            v_str="p0",
            e_str="Vdr*Ida-pr",
            diag_eps=True,
        )
        self.pinv = Algeb(
            info="unblocked inverter active-power delivery",
            tex_name="P_i",
            v_str="p0-rdc*Ida**2",
            e_str="Vdi*Ida-pinv",
            diag_eps=True,
        )
        self.qr = Algeb(
            info="rectifier converter reactive-power absorption",
            tex_name="Q_r^{conv}",
            v_str="0.3*p0",
            e_str="kconv*mr*vr*Ida*sin(phir)-qr",
            diag_eps=True,
        )
        self.qi = Algeb(
            info="inverter converter reactive-power absorption",
            tex_name="Q_i^{conv}",
            v_str="0.4*p0",
            e_str="kconv*mi*vi*Ida*sin(phii)-qi",
            diag_eps=True,
        )

        # Closed-form normal operating-point initialization.  Re-evaluating
        # the formulas with the solved bus voltages at TDS init avoids relying
        # on proprietary load-flow state transfer and keeps every initial
        # differential equation at zero.
        self.Ida.v_str = (
            "uI*i0+uP*2*p0/(kconv*mi*vi*cosg"
            "+sqrt((kconv*mi*vi*cosg)**2"
            "+4*(rdc-ccomm*xci)*p0))"
        )
        self.Vdi.v_str = "kconv*mi*vi*cosg-ccomm*xci*Ida"
        self.Vdr.v_str = "Vdi+rdc*Ida"
        self.cosa.v_str = "(Vdr+ccomm*xcr*Ida)/(kconv*mr*vr)"
        self.phir.v_str = "acos(Vdr/(kconv*mr*vr))"
        self.phii.v_str = "acos(Vdi/(kconv*mi*vi))"
        self.Id.v_str = "Ida"
        self.Xr.y.v_str = "cosa"
        self.Pref.v_str = "p0"
        self.Iref.v_str = "i0"
        self.prefeff.v_str = "p0"
        self.vdcnorm.v_str = "Vdi/vdcn"
        self.IordRaw.v_str = "Ida"
        self.Iord.v_str = "Ida"
        self.ierr.v_str = "0"
        self.CosaRaw.v_str = "cosa"
        self.run.v_str = "1"
        self.pr.v_str = "Vdr*Ida"
        self.pinv.v_str = "Vdi*Ida"
        self.qr.v_str = "kconv*mr*vr*Ida*sin(phir)"
        self.qi.v_str = "kconv*mi*vi*Ida*sin(phii)"

        self.ar.e_str = "u*run*pr"
        self.ai.e_str = "-u*run*pinv"
        self.vr.e_str = "u*(run*qr-filter*qcr*vr**2)"
        self.vi.e_str = "u*(run*qi-filter*qci*vi**2)"


class LCC2T(LCC2TData, LCC2TModel):
    """Two-terminal LCC-HVDC model for power flow and time-domain studies."""

    def __init__(self, system, config):
        LCC2TData.__init__(self)
        LCC2TModel.__init__(self, system, config)
