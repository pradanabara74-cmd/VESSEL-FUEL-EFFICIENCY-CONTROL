import streamlit as st
import pandas as pd
import numpy as np

# ============================================================
# VESSEL FUEL EFFICIENCY & CONTROL INTELLIGENCE CENTER
# ============================================================

st.set_page_config(
    page_title="Vessel Fuel Efficiency & Control",
    page_icon="⛽",
    layout="wide",
)

# ============================================================
# STYLE
# ============================================================

st.markdown(
    """
    <style>
    .main-title {
        font-size: 34px;
        font-weight: 800;
        color: #0B3D5C;
        margin-bottom: 0px;
    }

    .sub-title {
        font-size: 16px;
        color: #5B6770;
        margin-top: 0px;
        margin-bottom: 20px;
    }

    .info-box {
        padding: 14px;
        border-radius: 10px;
        background-color: #F3F7FA;
        border-left: 5px solid #0B3D5C;
        margin-bottom: 15px;
    }

    .status-normal {
        padding: 12px;
        border-radius: 8px;
        background-color: #E8F5E9;
        font-weight: 700;
    }

    .status-warning {
        padding: 12px;
        border-radius: 8px;
        background-color: #FFF3E0;
        font-weight: 700;
    }

    .status-critical {
        padding: 12px;
        border-radius: 8px;
        background-color: #FFEBEE;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CONSTANTS
# ============================================================

HP_TO_KW = 0.745699872

VESSEL_TYPES = [
    "Tanker",
    "Cargo Vessel",
    "Tugboat",
    "Ocean Tug",
    "AHT",
    "AHTS",
]

OPERATING_MODES = [
    "Free Sailing",
    "Economical Sailing",
    "Maneuvering",
    "Towing",
    "Anchor Handling",
    "DP Operation",
    "Standby",
    "Port / Idle",
]

# ============================================================
# FUNCTIONS
# ============================================================

def hp_to_kw(hp):
    return hp * HP_TO_KW


def kw_to_hp(kw):
    return kw / HP_TO_KW


def rpm_ratio(actual_rpm, rated_rpm):
    if rated_rpm <= 0:
        return 0.0

    return actual_rpm / rated_rpm


def propeller_power(rated_kw, actual_rpm, rated_rpm, exponent=3.0):
    """
    Approximate absorbed propulsion power using propeller law.

    P2 / P1 = (N2 / N1)^exponent

    This is an engineering estimate and should be replaced
    by manufacturer/sea-trial curves when available.
    """

    ratio = rpm_ratio(actual_rpm, rated_rpm)

    return rated_kw * (ratio ** exponent)


def estimate_load_percent(
    rated_kw,
    actual_rpm,
    rated_rpm,
    exponent=3.0,
):
    if rated_kw <= 0:
        return 0.0

    estimated_kw = propeller_power(
        rated_kw,
        actual_rpm,
        rated_rpm,
        exponent,
    )

    return min((estimated_kw / rated_kw) * 100, 100)


def sfoc_correction(base_sfoc, load_percent):
    """
    Simplified part-load correction.

    This is NOT a manufacturer engine curve.

    Manufacturer SFOC curves should be used whenever available.
    """

    if load_percent >= 85:
        factor = 1.00

    elif load_percent >= 70:
        factor = 1.02

    elif load_percent >= 50:
        factor = 1.05

    elif load_percent >= 30:
        factor = 1.10

    else:
        factor = 1.18

    return base_sfoc * factor


def fuel_kg_hour(power_kw, sfoc):
    """
    power_kw x SFOC(g/kWh) / 1000
    """

    return (power_kw * sfoc) / 1000


def fuel_litre_hour(fuel_kg_h, density):
    if density <= 0:
        return 0.0

    return fuel_kg_h / density


def fuel_ton_day(fuel_kg_h, running_hours):
    return (fuel_kg_h * running_hours) / 1000


def consumption_per_nm(litre_hour, speed_knots):
    if speed_knots <= 0:
        return 0.0

    return litre_hour / speed_knots


def calculate_engine(
    rated_kw,
    rated_rpm,
    actual_rpm,
    base_sfoc,
    density,
    running_hours,
    speed_knots,
    exponent,
    engine_count,
):
    power_one = propeller_power(
        rated_kw,
        actual_rpm,
        rated_rpm,
        exponent,
    )

    load = estimate_load_percent(
        rated_kw,
        actual_rpm,
        rated_rpm,
        exponent,
    )

    corrected_sfoc = sfoc_correction(
        base_sfoc,
        load,
    )

    kg_h_one = fuel_kg_hour(
        power_one,
        corrected_sfoc,
    )

    litre_h_one = fuel_litre_hour(
        kg_h_one,
        density,
    )

    total_power = power_one * engine_count
    total_kg_h = kg_h_one * engine_count
    total_l_h = litre_h_one * engine_count

    litres_day = total_l_h * running_hours

    tons_day = fuel_ton_day(
        total_kg_h,
        running_hours,
    )

    litre_nm = consumption_per_nm(
        total_l_h,
        speed_knots,
    )

    return {
        "load": load,
        "sfoc": corrected_sfoc,
        "power_kw": total_power,
        "kg_h": total_kg_h,
        "l_h": total_l_h,
        "l_day": litres_day,
        "ton_day": tons_day,
        "l_nm": litre_nm,
    }


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">'
    '⛽ VESSEL FUEL EFFICIENCY & CONTROL INTELLIGENCE CENTER'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="sub-title">'
    'Tanker • Cargo • Tugboat • Ocean Tug • AHT • AHTS'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="info-box">
    <b>Purpose:</b> Fuel consumption monitoring,
    RPM analysis, engine-load estimation, efficiency control
    and excess-fuel detection.
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("⚙️ Vessel & Engine Configuration")

vessel_name = st.sidebar.text_input(
    "Vessel Name",
    value="VESSEL 01",
)

vessel_type = st.sidebar.selectbox(
    "Vessel Type",
    VESSEL_TYPES,
)

gt = st.sidebar.number_input(
    "Gross Tonnage (GT)",
    min_value=0.0,
    value=3000.0,
    step=100.0,
)

operation_mode = st.sidebar.selectbox(
    "Operating Mode",
    OPERATING_MODES,
)

st.sidebar.markdown("---")

st.sidebar.subheader("Main Engine")

# ============================================================
# ENGINE MASTER DATABASE
# ============================================================

ENGINE_DATABASE = {
    "MAN": [
        "MAN B&W",
        "MAN 32/40",
        "MAN 48/60",
        "MAN D2862",
        "Other / Manual Input",
    ],
    "Caterpillar": [
        "CAT 3512",
        "CAT 3516",
        "CAT C32",
        "CAT C175",
        "Other / Manual Input",
    ],
    "Cummins": [
        "Cummins KTA38",
        "Cummins KTA50",
        "Cummins QSK38",
        "Cummins QSK60",
        "Other / Manual Input",
    ],
    "Wartsila": [
        "Wartsila 20",
        "Wartsila 26",
        "Wartsila 31",
        "Wartsila 32",
        "Other / Manual Input",
    ],
    "Yanmar": [
        "Yanmar 6EY",
        "Yanmar 8EY",
        "Yanmar 6AYM",
        "Other / Manual Input",
    ],
    "Mitsubishi": [
        "Mitsubishi S12R",
        "Mitsubishi S16R",
        "Mitsubishi UEC",
        "Other / Manual Input",
    ],
    "Niigata": [
        "Niigata 6L",
        "Niigata 8L",
        "Niigata 6MG",
        "Other / Manual Input",
    ],
    "Daihatsu": [
        "Daihatsu DK",
        "Daihatsu DE",
        "Daihatsu DC",
        "Other / Manual Input",
    ],
    "Other": [
        "Other / Manual Input",
    ],
}

# ============================================================
# ENGINE SPECIFICATION AUTO-FILL DATABASE
# Default engineering reference values.
# Verify against vessel/engine manufacturer's actual data.
# ============================================================

ENGINE_SPECS = {
    "MAN B&W": {
        "rated_kw": 3000.0,
        "rated_rpm": 1200,
        "sfoc": 205.0,
    },
    "MAN 32/40": {
        "rated_kw": 3200.0,
        "rated_rpm": 750,
        "sfoc": 190.0,
    },
    "MAN 48/60": {
        "rated_kw": 6000.0,
        "rated_rpm": 500,
        "sfoc": 185.0,
    },
    "MAN D2862": {
        "rated_kw": 1450.0,
        "rated_rpm": 1800,
        "sfoc": 205.0,
    },

    "CAT 3512": {
        "rated_kw": 1500.0,
        "rated_rpm": 1800,
        "sfoc": 205.0,
    },
    "CAT 3516": {
        "rated_kw": 2000.0,
        "rated_rpm": 1800,
        "sfoc": 205.0,
    },
    "CAT C32": {
        "rated_kw": 1000.0,
        "rated_rpm": 1800,
        "sfoc": 210.0,
    },
    "CAT C175": {
        "rated_kw": 2500.0,
        "rated_rpm": 1800,
        "sfoc": 200.0,
    },

    "Cummins KTA38": {
        "rated_kw": 900.0,
        "rated_rpm": 1800,
        "sfoc": 210.0,
    },
    "Cummins KTA50": {
        "rated_kw": 1200.0,
        "rated_rpm": 1800,
        "sfoc": 205.0,
    },
    "Cummins QSK38": {
        "rated_kw": 1000.0,
        "rated_rpm": 1800,
        "sfoc": 205.0,
    },
    "Cummins QSK60": {
        "rated_kw": 1800.0,
        "rated_rpm": 1800,
        "sfoc": 200.0,
    },
}

engine_maker = st.sidebar.selectbox(
    "Engine Maker",
    list(ENGINE_DATABASE.keys()),
)

selected_engine_model = st.sidebar.selectbox(
    "Engine Model",
    ENGINE_DATABASE[engine_maker],
)

if selected_engine_model == "Other / Manual Input":
    engine_model = st.sidebar.text_input(
        "Enter Engine Model",
        value="",
        placeholder="Example: 6L28/32A",
    )
else:
    engine_model = selected_engine_model

engine_count = st.sidebar.number_input(
    "Number of Main Engines Running",
    min_value=1,
    max_value=8,
    value=2,
    step=1,
)

# ============================================================
# AUTO ENGINE SPECIFICATION / MANUAL FALLBACK
# ============================================================

engine_spec = ENGINE_SPECS.get(engine_model)

if engine_spec:
    # Automatic values from Engine Master Database
    rated_kw = float(engine_spec["rated_kw"])
    rated_hp = kw_to_hp(rated_kw)
    rated_rpm = int(engine_spec["rated_rpm"])
    base_sfoc = float(engine_spec["sfoc"])

    st.sidebar.markdown("### ⚙️ Engine Specification")
    st.sidebar.success("Engine specification loaded automatically")

    st.sidebar.metric(
        "Rated Power / Engine",
        f"{rated_kw:,.0f} kW"
    )

    st.sidebar.metric(
        "Equivalent HP / Engine",
        f"{rated_hp:,.0f} HP"
    )

    st.sidebar.metric(
        "Rated RPM",
        f"{rated_rpm:,}"
    )

    st.sidebar.metric(
        "Base SFOC",
        f"{base_sfoc:.1f} g/kWh"
    )

else:
    # Manual input for engines not yet available in ENGINE_SPECS
    st.sidebar.markdown("### ⚙️ Manual Engine Specification")

    power_input = st.sidebar.radio(
        "Rated Power Input",
        ["kW", "HP"],
        horizontal=True,
    )

    if power_input == "kW":
        rated_kw = st.sidebar.number_input(
            "Rated Power / Engine (kW)",
            min_value=1.0,
            value=1500.0,
            step=50.0,
        )
        rated_hp = kw_to_hp(rated_kw)

    else:
        rated_hp = st.sidebar.number_input(
            "Rated Power / Engine (HP)",
            min_value=1.0,
            value=2000.0,
            step=50.0,
        )
        rated_kw = hp_to_kw(rated_hp)

    rated_rpm = st.sidebar.number_input(
        "Rated RPM",
        min_value=100,
        max_value=3000,
        value=1200,
        step=50,
    )

    base_sfoc = st.sidebar.number_input(
        "Base SFOC (g/kWh)",
        min_value=100.0,
        max_value=400.0,
        value=205.0,
        step=1.0,
    )

# Actual RPM remains adjustable for operations
actual_rpm = st.sidebar.slider(
    "Actual RPM",
    min_value=100,
    max_value=int(rated_rpm),
    value=min(800, int(rated_rpm)),
    step=10,
)

fuel_density = st.sidebar.number_input(
    "Fuel Density (kg/L)",
    min_value=0.700,
    max_value=1.050,
    value=0.850,
    step=0.001,
    format="%.3f",
)

propeller_exponent = st.sidebar.number_input(
    "Propeller Curve Exponent",
    min_value=2.0,
    max_value=3.5,
    value=3.0,
    step=0.1,
)

running_hours = st.sidebar.number_input(
    "Running Hours / Day",
    min_value=0.0,
    max_value=24.0,
    value=24.0,
    step=0.5,
)

speed_knots = st.sidebar.number_input(
    "Vessel Speed (knots)",
    min_value=0.0,
    value=10.0,
    step=0.5,
)

fuel_price = st.sidebar.number_input(
    "Fuel Price / Litre",
    min_value=0.0,
    value=1.0,
    step=0.05,
)

# ============================================================
# CALCULATION
# ============================================================

result = calculate_engine(
    rated_kw,
    rated_rpm,
    actual_rpm,
    base_sfoc,
    fuel_density,
    running_hours,
    speed_knots,
    propeller_exponent,
    engine_count,
)

# ============================================================
# VESSEL INFORMATION
# ============================================================

st.subheader("🚢 Vessel & Engine Profile")

profile1, profile2, profile3, profile4 = st.columns(4)

profile1.metric(
    "Vessel",
    vessel_name,
)

profile2.metric(
    "Type",
    vessel_type,
)

profile3.metric(
    "Gross Tonnage",
    f"{gt:,.0f} GT",
)

profile4.metric(
    "Operating Mode",
    operation_mode,
)

profile5, profile6, profile7, profile8 = st.columns(4)

profile5.metric(
    "Engine",
    engine_model,
)

profile6.metric(
    "Rated Power / Engine",
    f"{rated_kw:,.0f} kW",
)

profile7.metric(
    "Equivalent HP / Engine",
    f"{rated_hp:,.0f} HP",
)

profile8.metric(
    "Rated RPM",
    f"{rated_rpm:,}",
)

# ============================================================
# KPI DASHBOARD
# ============================================================

st.subheader("📊 Fuel Efficiency Dashboard")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Actual RPM",
    f"{actual_rpm:,} RPM",
)

c2.metric(
    "Estimated Engine Load",
    f"{result['load']:.1f} %",
)

c3.metric(
    "Estimated Power",
    f"{result['power_kw']:,.0f} kW",
)

c4.metric(
    "Adjusted SFOC",
    f"{result['sfoc']:.1f} g/kWh",
)

c5, c6, c7, c8 = st.columns(4)

c5.metric(
    "Fuel Consumption",
    f"{result['l_h']:,.1f} L/h",
)

c6.metric(
    "Daily Consumption",
    f"{result['l_day']:,.0f} L/day",
)

c7.metric(
    "Daily Consumption",
    f"{result['ton_day']:.2f} t/day",
)

c8.metric(
    "Fuel / Nautical Mile",
    f"{result['l_nm']:.2f} L/NM",
)

daily_cost = result["l_day"] * fuel_price

st.metric(
    "Estimated Daily Fuel Cost",
    f"{daily_cost:,.2f}",
)

# ============================================================
# RPM ANALYSIS
# ============================================================

st.subheader("⚙️ RPM vs Fuel Consumption")

rpm_points = [
    600,
    700,
    800,
    900,
    1000,
    1100,
    1200,
]

rows = []

for rpm in rpm_points:

    if rpm > rated_rpm:
        continue

    r = calculate_engine(
        rated_kw,
        rated_rpm,
        rpm,
        base_sfoc,
        fuel_density,
        running_hours,
        speed_knots,
        propeller_exponent,
        engine_count,
    )

    rows.append(
        {
            "RPM": rpm,
            "Load (%)": round(r["load"], 1),
            "Power (kW)": round(r["power_kw"], 1),
            "SFOC (g/kWh)": round(r["sfoc"], 1),
            "Fuel (kg/h)": round(r["kg_h"], 1),
            "Fuel (L/h)": round(r["l_h"], 1),
            "Fuel (L/day)": round(r["l_day"], 0),
            "Fuel (t/day)": round(r["ton_day"], 2),
        }
    )

rpm_df = pd.DataFrame(rows)

st.dataframe(
    rpm_df,
    use_container_width=True,
    hide_index=True,
)

if not rpm_df.empty:

    st.markdown("### 📈 Solar Consumption by RPM")

    chart_df = rpm_df.set_index("RPM")[
        ["Fuel (L/h)"]
    ]

    st.line_chart(chart_df)

    st.markdown("### ⚡ Engine Power by RPM")

    power_chart = rpm_df.set_index("RPM")[
        ["Power (kW)"]
    ]

    st.line_chart(power_chart)

# ============================================================
# ACTUAL VS EXPECTED
# ============================================================

st.subheader("🎯 Actual Fuel vs Expected Fuel")

actual_fuel_l_h = st.number_input(
    "Enter Actual Fuel Consumption (L/h)",
    min_value=0.0,
    value=float(round(result["l_h"], 1)),
    step=1.0,
)

# ============================================================
# PRECISION-SAFE ACTUAL VS EXPECTED CALCULATION
# ============================================================

# Use the same precision displayed/entered by the operator.
expected_fuel = round(float(result["l_h"]), 1)
actual_fuel_l_h = round(float(actual_fuel_l_h), 1)

# Prevent tiny floating-point differences from creating
# false excess-fuel alarms.
variance = round(actual_fuel_l_h - expected_fuel, 1)

# Treat differences smaller than 0.05 L/h as zero.
if abs(variance) < 0.05:
    variance = 0.0

if expected_fuel > 0:
    variance_percent = round(
        (variance / expected_fuel) * 100,
        2
    )
else:
    variance_percent = 0.0

a1, a2, a3, a4 = st.columns(4)

a1.metric(
    "Expected",
    f"{expected_fuel:,.1f} L/h",
)

a2.metric(
    "Actual",
    f"{actual_fuel_l_h:,.1f} L/h",
)

a3.metric(
    "Variance",
    f"{variance:,.1f} L/h",
)

a4.metric(
    "Variance",
    f"{variance_percent:+.1f} %",
)

# ============================================================
# STATUS
# ============================================================

st.markdown("### 🚦 Fuel Efficiency Status")

if variance_percent <= 5:

    st.markdown(
        """
        <div class="status-normal">
        ✅ NORMAL — Actual consumption is within the
        configured estimated range.
        </div>
        """,
        unsafe_allow_html=True,
    )

elif variance_percent <= 15:

    st.markdown(
        """
        <div class="status-warning">
        ⚠️ HIGH CONSUMPTION — Review engine load,
        vessel condition, weather, speed and operating mode.
        </div>
        """,
        unsafe_allow_html=True,
    )

else:

    st.markdown(
        """
        <div class="status-critical">
        🔴 CRITICAL FUEL CONSUMPTION — Significant
        deviation from the configured expected consumption.
        Investigation is recommended.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# POTENTIAL EXCESS
# ============================================================

st.subheader("💰 Excess Fuel Intelligence")

if variance > 0.05:

    excess_day = (
        variance *
        running_hours
    )

    excess_month = excess_day * 30

    excess_cost_day = (
        excess_day *
        fuel_price
    )

    excess_cost_month = (
        excess_month *
        fuel_price
    )

else:

    excess_day = 0
    excess_month = 0
    excess_cost_day = 0
    excess_cost_month = 0

e1, e2, e3, e4 = st.columns(4)

e1.metric(
    "Excess Fuel / Day",
    f"{excess_day:,.0f} L",
)

e2.metric(
    "Excess Fuel / 30 Days",
    f"{excess_month:,.0f} L",
)

e3.metric(
    "Potential Cost / Day",
    f"{excess_cost_day:,.2f}",
)

e4.metric(
    "Potential Cost / 30 Days",
    f"{excess_cost_month:,.2f}",
)

# ============================================================
# FORMULA
# ============================================================

with st.expander("📐 Engineering Formula Used"):

    st.markdown(
        r"""
### Power conversion

**1 HP = 0.745699872 kW**

### Propeller-law estimate

\[
P_{actual}
=
P_{rated}
\left(
\frac{RPM_{actual}}
{RPM_{rated}}
\right)^n
\]

Default:

\[
n = 3
\]

### Fuel mass consumption

\[
Fuel_{kg/h}
=
\frac{
Power_{kW}
\times
SFOC_{g/kWh}
}{1000}
\]

### Fuel volume

\[
Fuel_{L/h}
=
\frac{
Fuel_{kg/h}
}{
Density_{kg/L}
}
\]

### Daily fuel

\[
Fuel_{L/day}
=
Fuel_{L/h}
\times
RunningHours
\]

### Fuel per nautical mile

\[
Fuel_{L/NM}
=
\frac{
Fuel_{L/h}
}{
Speed_{knots}
}
\]

**Important:** Propeller law and part-load SFOC correction
are estimates. Manufacturer engine performance curves,
fuel-flow-meter data and vessel sea-trial data should take
priority when available.
"""
    )

# ============================================================
# INTELLIGENCE
# ============================================================

st.subheader("🧠 Fuel Efficiency Intelligence")

recommendations = []

if variance_percent > 5:
    recommendations.append(
        "Actual fuel consumption exceeds the configured expected value."
    )

if result["load"] < 30:
    recommendations.append(
        "Engine is operating at a low estimated propulsion load."
    )

if actual_rpm > rated_rpm * 0.90:
    recommendations.append(
        "Engine is operating close to rated RPM."
    )

if speed_knots > 0:
    recommendations.append(
        f"Current estimated fuel intensity is "
        f"{result['l_nm']:.2f} L/NM."
    )

if not recommendations:
    recommendations.append(
        "No significant efficiency exception detected from current inputs."
    )

for item in recommendations:
    st.write("•", item)

# ============================================================
# DISCLAIMER
# ============================================================

st.warning(
    """
ENGINEERING NOTICE:
Calculated fuel consumption is an engineering estimate,
not a replacement for the engine manufacturer's certified
fuel-consumption/performance curve.

For operational or commercial decisions, configure the app
using the exact engine model, engine rating, manufacturer
SFOC/load curve, fuel density, sea-trial data and calibrated
fuel-flow measurements.
"""
)

st.caption(
    "Vessel Fuel Efficiency & Control Intelligence Center"
)
