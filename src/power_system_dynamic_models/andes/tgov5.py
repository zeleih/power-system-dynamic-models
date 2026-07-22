"""Single-shaft TGOV5 boiler-turbine-governor model for ANDES.

The equations follow the public PSS/E Model Data Sheets TGOV5 block diagram,
cross-checked against IEEE PES-TR1 and the official EMTP/PowerWorld model
descriptions. Internal power and steam-flow signals use turbine-base per unit;
``PBASE`` converts the final mechanical output to the ANDES system base.

The Gumede (2016) public PowerFactory benchmark specifies a 90-s exact fuel
delay. ANDES' time-domain delay is used for that source-consistent benchmark;
the implementation must not be described as numerically identical to
proprietary PSS/E code.
"""

from __future__ import annotations

from andes.core import (
    Algeb,
    AntiWindup,
    ConstService,
    ExtAlgeb,
    ExtService,
    HardLimiter,
    Lag,
    LeadLag,
    NumParam,
    State,
)
from andes.core.block import DeadBand1, IntegratorAntiWindup
from andes.core.common import DummyValue
from andes.core.discrete import Delay
from andes.core.service import InitChecker
from andes.models.governor.tgbase import TGBase, TGBaseData


class TGOV5Data(TGBaseData):
    """Parameters for the public TGOV5 block diagram and local adapters."""

    def __init__(self):
        super().__init__()

        # Turbine-base-to-system-base conversion. A raw value of 1 p.u. is
        # converted by ANDES using the connected generator/turbine rating.
        self.PBASE = NumParam(
            default=1.0,
            power=True,
            info="One turbine-base p.u. on system base",
        )

        self.K = NumParam(
            default=20.0,
            tex_name="K",
            info="Governor gain 1/R on turbine base",
        )
        self.T1 = NumParam(default=0.1, tex_name="T_1", unit="s")
        self.T2 = NumParam(default=0.0, tex_name="T_2", unit="s")
        self.T3 = NumParam(default=0.3, tex_name="T_3", unit="s")
        self.UO = NumParam(default=0.2, tex_name="U_o", unit="p.u./s")
        self.UC = NumParam(default=-0.2, tex_name="U_c", unit="p.u./s")
        self.VMAX = NumParam(default=1.15, tex_name="V_{MAX}", unit="p.u.")
        self.VMIN = NumParam(default=0.0, tex_name="V_{MIN}", unit="p.u.")

        self.T4 = NumParam(default=0.2, tex_name="T_4", unit="s")
        self.K1 = NumParam(default=0.3, tex_name="K_1")
        self.K2 = NumParam(default=0.0, tex_name="K_2")
        self.T5 = NumParam(default=15.0, tex_name="T_5", unit="s")
        self.K3 = NumParam(default=0.3, tex_name="K_3")
        self.K4 = NumParam(default=0.0, tex_name="K_4")
        self.T6 = NumParam(default=0.3, tex_name="T_6", unit="s")
        self.K5 = NumParam(default=0.4, tex_name="K_5")
        self.K6 = NumParam(default=0.0, tex_name="K_6")
        self.T7 = NumParam(default=0.0, tex_name="T_7", unit="s")
        self.K7 = NumParam(default=0.0, tex_name="K_7")
        self.K8 = NumParam(default=0.0, tex_name="K_8")

        self.K9 = NumParam(default=0.01, tex_name="K_9")
        self.K10 = NumParam(default=0.0, tex_name="K_{10}")
        self.K11 = NumParam(default=0.0, tex_name="K_{11}")
        self.K12 = NumParam(default=0.01, tex_name="K_{12}")
        self.K13 = NumParam(default=0.0, tex_name="K_{13}")
        self.K14 = NumParam(default=0.1, tex_name="K_{14}")

        # Research-only matched intervention. PSEL=1 is the pressure-coupled
        # model. PSEL=0 retains every state, controller, limiter, delay, and
        # outer-loop path while cutting the two outgoing pressure edges.
        self.PSEL = NumParam(
            default=1.0,
            tex_name="S_P",
            info="Binary pressure-path selector for matched interventions",
        )

        self.RMAX = NumParam(default=0.004, tex_name="R_{MAX}", unit="p.u./s")
        self.RMIN = NumParam(default=-0.004, tex_name="R_{MIN}", unit="p.u./s")
        self.LMAX = NumParam(default=1.0, tex_name="L_{MAX}", unit="p.u.")
        self.LMIN = NumParam(default=-0.4, tex_name="L_{MIN}", unit="p.u.")

        self.C1 = NumParam(default=0.0001, tex_name="C_1")
        self.C2 = NumParam(default=0.1, tex_name="C_2")
        self.C3 = NumParam(default=0.0, tex_name="C_3")
        self.B = NumParam(default=20.0, tex_name="B")
        self.CB = NumParam(default=150.0, tex_name="C_B", unit="s")
        self.KI = NumParam(default=0.1, tex_name="K_I")
        self.TI = NumParam(default=12.0, tex_name="T_I", unit="s")
        self.TR = NumParam(default=12.0, tex_name="T_R", unit="s")
        self.TR1 = NumParam(default=2.0, tex_name="T_{R1}", unit="s")
        self.CMAX = NumParam(default=1.15, tex_name="C_{MAX}", unit="p.u.")
        self.CMIN = NumParam(default=0.3, tex_name="C_{MIN}", unit="p.u.")
        self.TD = NumParam(default=3.0, tex_name="T_D", unit="s")
        self.TF = NumParam(default=5.0, tex_name="T_F", unit="s")
        self.TW = NumParam(default=5.0, tex_name="T_W", unit="s")
        self.Psp = NumParam(default=0.95, tex_name="P_{SP0}", unit="p.u.")
        self.TMW = NumParam(default=5.0, tex_name="T_{MW}", unit="s")
        self.KL = NumParam(default=0.0, tex_name="K_L")
        self.KMW = NumParam(default=1.0, tex_name="K_{MW}")
        self.DPE = NumParam(default=0.1, tex_name="D_{PE}", unit="p.u.")


class TGOV5Model(TGBase):
    """Public-equation TGOV5 realization with one mechanical output."""

    # The validated public benchmark has one common TD=90 s for every unit.
    # ANDES Delay requires a scalar at construction, so reject other values.
    SOURCE_FUEL_DELAY_SECONDS = 90.0

    def __init__(self, system, config):
        super().__init__(system, config, add_sn=True)

        self.Pe0 = ExtService(
            src="Pe",
            model="SynGen",
            indexer=self.syn,
            tex_name="P_{e0}",
            info="Initial electrical power on ANDES system base",
        )
        self.Pe = ExtAlgeb(
            src="Pe",
            model="SynGen",
            indexer=self.syn,
            tex_name="P_e",
            info="Electrical power on ANDES system base",
            export=False,
        )

        self.tmn0 = ConstService(
            v_str="tm0/PBASE",
            info="Initial turbine power on turbine base",
        )
        self._sumK = ConstService(v_str="K1+K2+K3+K4+K5+K6+K7+K8")
        self._sumK_check = InitChecker(
            u=self._sumK,
            equal=1.0,
            error_out=True,
            info="K1 through K8 sum",
        )
        self._ki_check = InitChecker(
            u=self.KI,
            lower=1e-9,
            error_out=True,
            info="KI positivity",
        )
        self._tr1_check = InitChecker(
            u=self.TR1,
            lower=1e-9,
            error_out=True,
            info="TR1 positivity",
        )
        self._td_check = InitChecker(
            u=self.TD,
            equal=self.SOURCE_FUEL_DELAY_SECONDS,
            error_out=True,
            info="TD=90 s for the Gumede 2016 exact-delay benchmark",
        )
        self._psp_check = InitChecker(
            u=self.Psp,
            lower=1e-6,
            error_out=True,
            info="Psp positivity",
        )
        self.psel_binary_residual = ConstService(
            v_str="PSEL*(1-PSEL)",
            info="zero only for the allowed binary pressure selector values",
        )
        self._psel_check = InitChecker(
            u=self.psel_binary_residual,
            equal=0.0,
            error_out=True,
            info="pressure-path selector must be exactly 0 or 1",
        )

        # Initial equilibrium on turbine base.
        self.v0 = ConstService(v_str="tmn0/Psp", info="Initial valve area")
        self.po0 = ConstService(v_str="v0", info="Initial power order")
        self.pe0n = ConstService(
            v_str="Pe0/PBASE",
            info="Initial electrical power on turbine base",
        )
        self.d0 = ConstService(
            v_str="KMW*pe0n+KL*po0",
            info="Initial raw MW demand",
        )
        self.c0 = ConstService(
            v_str="tmn0-K11*d0-K10*tmn0",
            info="Initial pressure-controller fuel contribution",
        )
        self.pd0 = ConstService(
            v_str="(Psp+C1*tmn0*tmn0)/(1+K9*tmn0*tmn0)",
            info="Initial drum pressure from pressure-drop equilibrium",
        )
        self.pd_den0 = ConstService(
            v_str="1+K9*tmn0*tmn0",
            info="Initial drum-pressure denominator",
        )
        self.drop_coeff0 = ConstService(
            v_str="C1-K9*pd0",
            info="Initial flow-pressure drop coefficient",
        )
        self.drop0 = ConstService(
            v_str="pd0-Psp",
            info="Initial drum-to-throttle pressure drop",
        )
        self.psp0_error = ConstService(
            v_str="C3+K13*d0-Psp",
            info="Published pressure-setpoint equilibrium residual",
        )
        self._pd_den0_check = InitChecker(
            u=self.pd_den0,
            lower=1e-9,
            error_out=True,
            info="positive initial drum-pressure denominator",
        )
        self._drop_coeff0_check = InitChecker(
            u=self.drop_coeff0,
            lower=1e-9,
            error_out=True,
            info="positive initial flow-pressure drop coefficient",
        )
        self._drop0_check = InitChecker(
            u=self.drop0,
            lower=1e-12,
            error_out=True,
            info="positive initial drum-to-throttle pressure drop",
        )
        self._psp0_equilibrium_check = InitChecker(
            u=self.psp0_error,
            equal=0.0,
            error_out=True,
            info="C3+K13*d0=Psp source-equation initialization",
        )
        self._v0_check = InitChecker(
            u=self.v0,
            lower=self.VMIN,
            upper=self.VMAX,
            error_out=True,
            info="initial valve area",
        )
        self._po0_check = InitChecker(
            u=self.po0,
            lower=self.LMIN,
            upper=self.LMAX,
            error_out=True,
            info="initial power order",
        )
        self._c0_check = InitChecker(
            u=self.c0,
            lower=self.CMIN,
            upper=self.CMAX,
            error_out=True,
            info="initial pressure-controller output",
        )

        # Speed governor: dw < 0 for under-frequency, so -gov opens the valve.
        self.dw = Algeb(
            info="Speed deviation omega-wref",
            tex_name=r"\Delta\omega",
            v_str="0",
            e_str="ue*(omega-wref)-dw",
        )
        self.GovLL = LeadLag(
            u=self.dw,
            T1=self.T2,
            T2=self.T1,
            K=self.K,
            info="Governor K(1+sT2)/(1+sT1)",
        )

        # Pressure and steam path are a DAE loop through valve * PT.
        self.PD = State(
            info="Drum pressure",
            tex_name="P_D",
            t_const=self.CB,
            v_str="pd0",
            e_str="Heat-L4_y",
        )
        self.PT = Algeb(
            info="Throttle pressure",
            tex_name="P_T",
            v_str="Psp",
            e_str="PD-(C1-K9*PD)*L4_y*L4_y-PT",
        )

        # Demand/control coordinates. paux is a system-base perturbation.
        self.MWD = Algeb(
            info="Raw MW demand on turbine base",
            tex_name="D",
            v_str="d0",
            e_str="d0+paux/PBASE-MWD",
        )
        self.Dstar = Algeb(
            info="Frequency-biased desired power",
            tex_name="D^*",
            v_str="d0",
            e_str="MWD-B*dw-Dstar",
        )
        self.PSP = Algeb(
            info="Pressure set point",
            tex_name="P_{SP}",
            v_str="Psp",
            e_str="C3+K13*MWD-PSP",
        )
        self.ep = Algeb(
            info="Pressure error PSP-PT",
            tex_name="e_P",
            v_str="0",
            e_str="PSEL*(PSP-PT)-ep",
        )
        self.nDPE = ConstService(v_str="-DPE", info="Negative deadband bound")
        self.PressureDB = DeadBand1(
            u=self.ep,
            center=0.0,
            lower=self.nDPE,
            upper=self.DPE,
            info="Continuous Type-2 pressure deadband in PSS/E terminology",
        )

        self.Pen = Algeb(
            info="Electrical power on turbine base",
            tex_name="P_e^{tb}",
            v_str="pe0n",
            e_str="Pe/PBASE-Pen",
        )
        self.Pmeas = Lag(
            u=self.Pen,
            T=self.TMW,
            K=self.KMW,
            info="Measured electrical power on turbine base",
        )
        self.poerr = Algeb(
            info="Power-order servo error",
            tex_name="e_o",
            v_str="0",
            e_str=(
                "Dstar-(C2+K12*PSP*Po_y)*PressureDB_y"
                "-Pmeas_y-KL*Po_y-poerr"
            ),
        )
        self.poraw = Algeb(
            info="Unconstrained power-order rate",
            tex_name=r"\dot P_o^{raw}",
            v_str="0",
            e_str="K14*poerr-poraw",
        )
        self.PoRateHL = HardLimiter(
            u=self.poraw,
            lower=self.RMIN,
            upper=self.RMAX,
        )
        self.polim = Algeb(
            info="Limited power-order rate",
            tex_name=r"\dot P_o",
            v_str="0",
            e_str=(
                "poraw*PoRateHL_zi+RMIN*PoRateHL_zl"
                "+RMAX*PoRateHL_zu-polim"
            ),
        )
        self.Po = IntegratorAntiWindup(
            u=self.polim,
            T=1.0,
            K=1.0,
            y0=self.po0,
            lower=self.LMIN,
            upper=self.LMAX,
            info="Load reference / power order",
        )

        self.vraw = Algeb(
            info="Unconstrained valve rate",
            tex_name=r"\dot v^{raw}",
            v_str="0",
            e_str="(Po_y-GovLL_y-Valve_y)/T3-vraw",
        )
        self.ValveRateHL = HardLimiter(
            u=self.vraw,
            lower=self.UC,
            upper=self.UO,
        )
        self.vlim = Algeb(
            info="Limited valve rate",
            tex_name=r"\dot v",
            v_str="0",
            e_str=(
                "vraw*ValveRateHL_zi+UC*ValveRateHL_zl"
                "+UO*ValveRateHL_zu-vlim"
            ),
        )
        self.Valve = IntegratorAntiWindup(
            u=self.vlim,
            T=1.0,
            K=1.0,
            y0=self.v0,
            lower=self.VMIN,
            upper=self.VMAX,
            info="Steam valve area",
        )

        self.L4 = Lag(
            u="Valve_y*(PSEL*PT+(1-PSEL)*Psp)",
            T=self.T4,
            K=1.0,
            info="Steam chest / inlet piping with pressure-path selector",
        )
        self.L5 = Lag(
            u=self.L4.y,
            T=self.T5,
            K=1.0,
            info="First reheat stage",
        )
        self.L6 = Lag(
            u=self.L5.y,
            T=self.T6,
            K=1.0,
            info="Second turbine stage",
        )
        self.L7 = Lag(
            u=self.L6.y,
            T=self.T7,
            K=1.0,
            info="Final turbine stage",
        )
        self.Pm = Algeb(
            info="Single-shaft turbine mechanical power on turbine base",
            tex_name="P_m",
            v_str="tmn0",
            e_str=(
                "K1*L4_y+K2*L4_y+K3*L5_y+K4*L5_y"
                "+K5*L6_y+K6*L6_y+K7*L7_y+K8*L7_y-Pm"
            ),
        )

        # Exact public linear pressure-controller transfer function:
        # KI (1+s TI)(1+s TR) / [s (1+s TR1)].
        self.pcA = ConstService(v_str="TI*TR/TR1")
        self.pcC = ConstService(v_str="TI+TR-TR1-pcA")
        self.pc_eta0 = ConstService(v_str="c0/KI")
        self.PCXi = Lag(
            u=self.ep,
            T=self.TR1,
            K=1.0,
            info="Pressure-controller lag state",
        )
        self.PCEta = State(
            info="Pressure-controller integral state",
            tex_name=r"\eta",
            t_const=DummyValue(1.0),
            v_str="pc_eta0",
            e_str="ep",
        )
        self.pc_lower_eta = Algeb(
            info="Moving lower anti-windup bound for eta",
            v_str="CMIN/KI-pcA*ep-pcC*PCXi_y",
            e_str="CMIN/KI-pcA*ep-pcC*PCXi_y-pc_lower_eta",
        )
        self.pc_upper_eta = Algeb(
            info="Moving upper anti-windup bound for eta",
            v_str="CMAX/KI-pcA*ep-pcC*PCXi_y",
            e_str="CMAX/KI-pcA*ep-pcC*PCXi_y-pc_upper_eta",
        )
        self.PCAW = AntiWindup(
            u=self.PCEta,
            lower=self.pc_lower_eta,
            upper=self.pc_upper_eta,
            info="Pressure-controller anti-windup on equivalent output bounds",
        )
        self.pcraw = Algeb(
            info="Unconstrained pressure-controller output",
            tex_name="c^{raw}",
            v_str="c0",
            e_str="KI*(PCEta+pcA*ep+pcC*PCXi_y)-pcraw",
        )
        self.PCHL = HardLimiter(
            u=self.pcraw,
            lower=self.CMIN,
            upper=self.CMAX,
        )
        self.pc = Algeb(
            info="Limited pressure-controller output",
            tex_name="c",
            v_str="c0",
            e_str="pcraw*PCHL_zi+CMIN*PCHL_zl+CMAX*PCHL_zu-pc",
        )

        self.ufuel = Algeb(
            info="Fuel command",
            tex_name="u_F",
            v_str="tmn0",
            e_str="pc+K11*Dstar+K10*L4_y-ufuel",
        )
        self.Fuel = Lag(
            u=self.ufuel,
            T=self.TF,
            K=1.0,
            info="Fuel-system lag",
        )
        self.Water = Lag(
            u=self.Fuel.y,
            T=self.TW,
            K=1.0,
            info="Water-wall lag",
        )
        self.FuelDelay = Delay(
            u=self.Water.y,
            mode="time",
            delay=self.SOURCE_FUEL_DELAY_SECONDS,
            info="Exact 90-s fuel-supply delay from the Gumede benchmark",
        )
        self.Heat = Algeb(
            info="Delayed heat input",
            tex_name="h",
            v_str="tmn0",
            e_str="FuelDelay_v-Heat",
        )

        self.pout.e_str = "ue*PBASE*Pm-pout"


class TGOV5(TGOV5Data, TGOV5Model):
    """Auditable single-shaft TGOV5 implementation for ANDES.

    The original commercial model also permits cross-compound HP/LP outputs.
    This adapter intentionally supports and validates only a single shaft.
    """

    def __init__(self, system, config):
        TGOV5Data.__init__(self)
        TGOV5Model.__init__(self, system, config)

