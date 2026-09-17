import streamlit as st
import pandas as pd

# ============================================================
# VESSEL FUEL EFFICIENCY & CONTROL INTELLIGENCE CENTER
# ============================================================

st.set_page_config(
    page_title="Vessel Fuel Efficiency & Control",
    page_icon="⛽",
    layout="wide",
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

ENGINE_DATABASE = {
    "MAN": [
        "MAN B&W",
        "MAN 32/40",
        "MAN 48/60",
        "MAN D2862",
        "Other / Manual Input",
    ],
    "Caterpillar": [
        "CAT 3512B",
        "CAT 3512C",
        "CAT 3512E",
        "CAT 3516",
        "CAT C32",
        "CAT C175",
        "Other / Manual Input",
    ],
    "Cummins": [
        "Cummins KTA38",
        "Cummins KTA50",
        "Cummins QSK38",
        "Cummins QSK60-M",
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

FUEL_TYPES = {
    "MGO / DMA": 0.850,
    "MDO / DMB": 0.880,
    "VLSFO": 0.940,
    "HFO": 0.980,
    "Custom": 0.850,
}

# Reference information only.
# These are NOT automatically treated as the vessel's installed rating.
ENGINE_REFERENCE = {
    "CAT 3512E": {
        "power": "1000–1902 kW",
        "rpm": "1600–1800 RPM",
        "source": "Caterpillar published marine range",
    },
    "CAT 3512C": {
        "power": "1281–2552 bhp range",
        "rpm": "1200–1800 RPM",
        "source": "Caterpillar published marine range",
    },
    "CAT 3512B": {
        "power": "Example published rating: 1119 kW",
        "rpm": "Example published rating: 1800 RPM",
        "source": "Caterpillar marine performance sheet",
    },
    "Cummins QSK60-M": {
        "power": "Multiple ratings: approx. 1491–2014 kW",
        "rpm": "1600–1900 RPM depending on rating",
        "source": "Cummins published marine ratings",
    },
}

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
        padding: 14px;
        border-radius: 8px;
        background-color: #E8F5E9;
        font-weight: 700;
    }

    .status-warning {
        padding: 14px;
        border-radius: 8px;
        background-color: #FFF3E0;
        font-weight: 700;
    }

    .status-critical {
        padding: 14px;
        border-radius: 8px;
        background-color: #FFEBEE;
        font-weight: 700;
    }

    .status-low {
        padding: 14px;
        border-radius: 8px;
        background-color: #E3F2FD;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# ENGINEERING FUNCTIONS
# ============================================================

def hp_to_kw(hp):
    return float(hp) * HP_TO_KW


def kw_to_hp(kw):
    return float(kw) / HP_TO_KW


def safe_divide(a, b):
    if b == 0:
        return 0.0
    return a / b


def propeller_power(
    rated_kw,
    actual_rpm,
    rated_rpm,
    exponent=3.0,
):
    if rated_kw <= 0 or rated_rpm <= 0:
        return 0.0

    ratio = max(0.0, actual_rpm / rated_rpm)

    return rated_kw * (ratio ** exponent)


def estimated_load_percent(
    actual_power_kw,
    rated_kw,
):
    if rated_kw <= 0:
        return 0.0

    return min(
        max(actual_power_kw / rated_kw * 100.0, 0.0),
        100.0,
    )


def corrected_sfoc(
    base_sfoc,
    load_percent,
):
    """
    Generic part-load correction for estimation only.

    It is not a substitute for the manufacturer's
    certified SFOC/load curve.
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
    power_one_kw = propeller_power(
        rated_kw,
        actual_rpm,
        rated_rpm,
        exponent,
    )

    load_percent = estimated_load_percent(
        power_one_kw,
        rated_kw,
    )

    sfoc = corrected_sfoc(
        base_sfoc,
        load_percent,
    )

    fuel_one_kg_h = (
        power_one_kw * sfoc
    ) / 1000.0

    fuel_one_l_h = safe_divide(
        fuel_one_kg_h,
        density,
    )

    total_power_kw = power_one_kw * engine_count
    total_fuel_kg_h = fuel_one_kg_h * engine_count
    total_fuel_l_h = fuel_one_l_h * engine_count

    fuel_l_day = total_fuel_l_h * running_hours

    fuel_t_day = (
        total_fuel_kg_h * running_hours
    ) / 1000.0

    fuel_l_nm = safe_divide(
        total_fuel_l_h,
        speed_knots,
    )

    distance_day_nm = speed_knots * running_hours

    return {
        "load": load_percent,
        "sfoc": sfoc,
        "power_kw": total_power_kw,
        "power_one_kw": power_one_kw,
        "kg_h": total_fuel_kg_h,
        "l_h": total_fuel_l_h,
        "l_day": fuel_l_day,
        "ton_day": fuel_t_day,
        "l_nm": fuel_l_nm,
        "distance_day_nm": distance_day_nm,
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
    <b>Purpose:</b> Vessel fuel monitoring, RPM/load analysis,
    fuel-efficiency control, cost monitoring and excess-fuel
    detection.
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# SIDEBAR — VESSEL
# ============================================================

st.sidebar.header("⚙️ Vessel Configuration")

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

# ============================================================
# SIDEBAR — ENGINE
# ============================================================

st.sidebar.header("🔧 Main Engine")

engine_maker = st.sidebar.selectbox(
    "Engine Maker",
    list(ENGINE_DATABASE.keys()),
)

selected_engine_model = st.sidebar.selectbox(
    "Engine Model / Family",
    ENGINE_DATABASE[engine_maker],
)

if selected_engine_model == "Other / Manual Input":
    engine_model = st.sidebar.text_input(
        "Exact Engine Model",
        value="",
        placeholder="Example: 6L28/32A",
    )
else:
    engine_model = selected_engine_model

reference = ENGINE_REFERENCE.get(engine_model)

if reference:
    with st.sidebar.expander(
        "ℹ️ Manufacturer Reference Range"
    ):
        st.write("Power:", reference["power"])
        st.write("Speed:", reference["rpm"])
        st.write("Reference:", reference["source"])
        st.caption(
            "Enter the exact installed engine rating below. "
            "A model family can have multiple ratings."
        )

engine_count = st.sidebar.number_input(
    "Main Engines Running",
    min_value=1,
    max_value=8,
    value=2,
    step=1,
)

st.sidebar.markdown("### Installed Engine Rating")

power_input = st.sidebar.radio(
    "Power Input Unit",
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

actual_rpm = st.sidebar.slider(
    "Actual RPM",
    min_value=100,
    max_value=int(rated_rpm),
    value=min(800, int(rated_rpm)),
    step=10,
)

propeller_exponent = st.sidebar.number_input(
    "Propeller Curve Exponent",
    min_value=2.0,
    max_value=3.5,
    value=3.0,
    step=0.1,
)

st.sidebar.caption(
    "Default n = 3.0 represents the conventional cubic "
    "propeller-law estimate for comparison purposes."
)

st.sidebar.markdown("---")

# ============================================================
# SIDEBAR — FUEL
# ============================================================

st.sidebar.header("⛽ Fuel Configuration")

fuel_type = st.sidebar.selectbox(
    "Fuel Type",
    list(FUEL_TYPES.keys()),
)

default_density = FUEL_TYPES[fuel_type]

fuel_density = st.sidebar.number_input(
    "Fuel Density (kg/L)",
    min_value=0.700,
    max_value=1.050,
    value=float(default_density),
    step=0.001,
    format="%.3f",
)

fuel_price = st.sidebar.number_input(
    "Fuel Price / Litre",
    min_value=0.0,
    value=1.0,
    step=0.05,
)

currency = st.sidebar.selectbox(
    "Currency",
    ["USD", "IDR", "SGD", "EUR"],
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

# ============================================================
# CALCULATION
# ============================================================

result = calculate_engine(
    rated_kw=rated_kw,
    rated_rpm=rated_rpm,
    actual_rpm=actual_rpm,
    base_sfoc=base_sfoc,
    density=fuel_density,
    running_hours=running_hours,
    speed_knots=speed_knots,
    exponent=propeller_exponent,
    engine_count=engine_count,
)

daily_cost = result["l_day"] * fuel_price
monthly_cost = daily_cost * 30

# ============================================================
# PROFILE
# ============================================================

st.subheader("🚢 Vessel & Engine Profile")

p1, p2, p3, p4 = st.columns(4)

p1.metric("Vessel", vessel_name)
p2.metric("Type", vessel_type)
p3.metric("Gross Tonnage", f"{gt:,.0f} GT")
p4.metric("Operating Mode", operation_mode)

p5, p6, p7, p8 = st.columns(4)

p5.metric("Engine", engine_model or "Manual")
p6.metric(
    "Rated Power / Engine",
    f"{rated_kw:,.0f} kW",
)
p7.metric(
    "Equivalent HP / Engine",
    f"{rated_hp:,.0f} HP",
)
p8.metric(
    "Rated RPM",
    f"{rated_rpm:,}",
)

# ============================================================
# DASHBOARD
# ============================================================

st.subheader("📊 Fuel Efficiency Dashboard")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Actual RPM",
    f"{actual_rpm:,}",
)

c2.metric(
    "Estimated Load",
    f"{result['load']:.1f}%",
)

c3.metric(
    "Estimated Total Power",
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
    "Daily Fuel",
    f"{result['l_day']:,.0f} L/day",
)

c7.metric(
    "Daily Fuel Mass",
    f"{result['ton_day']:.2f} t/day",
)

c8.metric(
    "Fuel Intensity",
    (
        f"{result['l_nm']:.2f} L/NM"
        if speed_knots > 0
        else "N/A"
    ),
)

cost1, cost2, cost3 = st.columns(3)

cost1.metric(
    "Estimated Daily Fuel Cost",
    f"{currency} {daily_cost:,.2f}",
)

cost2.metric(
    "Estimated 30-Day Fuel Cost",
    f"{currency} {monthly_cost:,.2f}",
)

cost3.metric(
    "Estimated Distance / Day",
    f"{result['distance_day_nm']:,.1f} NM",
)

# ============================================================
# RPM PERFORMANCE TABLE
# ============================================================

st.subheader("⚙️ RPM vs Fuel Consumption")

standard_rpm_points = [
    600,
    700,
    800,
    900,
    1000,
    1100,
    1200,
]

rpm_points = sorted(
    set(
        [
            rpm
            for rpm in standard_rpm_points
            if rpm <= rated_rpm
        ]
        + [int(rated_rpm)]
    )
)

rows = []

for rpm in rpm_points:

    r = calculate_engine(
        rated_kw=rated_kw,
        rated_rpm=rated_rpm,
        actual_rpm=rpm,
        base_sfoc=base_sfoc,
        density=fuel_density,
        running_hours=running_hours,
        speed_knots=speed_knots,
        exponent=propeller_exponent,
        engine_count=engine_count,
    )

    rows.append(
        {
            "RPM": rpm,
            "Load (%)": round(r["load"], 1),
            "Total Power (kW)": round(r["power_kw"], 1),
            "Adjusted SFOC (g/kWh)": round(r["sfoc"], 1),
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

    st.markdown("### 📈 Fuel Consumption by RPM")

    st.line_chart(
        rpm_df.set_index("RPM")[["Fuel (L/h)"]]
    )

    st.markdown("### ⚡ Estimated Engine Power by RPM")

    st.line_chart(
        rpm_df.set_index("RPM")[["Total Power (kW)"]]
    )

# ============================================================
# ACTUAL VS EXPECTED
# ============================================================

st.subheader("🎯 Actual Fuel vs Expected Fuel")

expected_fuel = round(
    float(result["l_h"]),
    1,
)

actual_fuel_l_h = st.number_input(
    "Measured / Actual Fuel Consumption (L/h)",
    min_value=0.0,
    value=expected_fuel,
    step=1.0,
)

actual_fuel_l_h = round(
    float(actual_fuel_l_h),
    1,
)

variance = round(
    actual_fuel_l_h - expected_fuel,
    1,
)

if abs(variance) < 0.05:
    variance = 0.0

variance_percent = (
    (variance / expected_fuel) * 100
    if expected_fuel > 0
    else 0.0
)

variance_percent = round(
    variance_percent,
    2,
)

efficiency_index = (
    expected_fuel / actual_fuel_l_h * 100
    if actual_fuel_l_h > 0
    else 0.0
)

v1, v2, v3, v4, v5 = st.columns(5)

v1.metric(
    "Expected",
    f"{expected_fuel:,.1f} L/h",
)

v2.metric(
    "Actual",
    f"{actual_fuel_l_h:,.1f} L/h",
)

v3.metric(
    "Difference",
    f"{variance:+,.1f} L/h",
)

v4.metric(
    "Variance",
    f"{variance_percent:+.1f}%",
)

v5.metric(
    "Efficiency Index",
    f"{efficiency_index:.1f}%",
)

# ============================================================
# STATUS
# ============================================================

st.markdown("### 🚦 Fuel Efficiency Status")

if variance_percent < -5:

    st.markdown(
        """
        <div class="status-low">
        🔵 BELOW ESTIMATE — Actual fuel consumption is
        materially below the current engineering estimate.
        Verify measurement quality and operating conditions.
        </div>
        """,
        unsafe_allow_html=True,
    )

elif variance_percent <= 5:

    st.markdown(
        """
        <div class="status-normal">
        ✅ NORMAL — Actual fuel consumption is within
        ±5% of the current engineering estimate.
        </div>
        """,
        unsafe_allow_html=True,
    )

elif variance_percent <= 15:

    st.markdown(
        """
        <div class="status-warning">
        ⚠️ HIGH CONSUMPTION — Actual fuel consumption
        is more than 5% above the current estimate.
        Investigation is recommended.
        </div>
        """,
        unsafe_allow_html=True,
    )

else:

    st.markdown(
        """
        <div class="status-critical">
        🔴 CRITICAL DEVIATION — Actual consumption is
        more than 15% above the current estimate.
        Investigate engine load, hull/propeller condition,
        weather, current, operating mode and measurement data.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# EXCESS FUEL
# ============================================================

st.subheader("💰 Excess Fuel Intelligence")

positive_variance = max(
    variance,
    0.0,
)

excess_day = (
    positive_variance *
    running_hours
)

excess_30d = (
    excess_day *
    30
)

excess_mass_day = (
    excess_day *
    fuel_density /
    1000
)

excess_cost_day = (
    excess_day *
    fuel_price
)

excess_cost_30d = (
    excess_30d *
    fuel_price
)

e1, e2, e3, e4, e5 = st.columns(5)

e1.metric(
    "Excess / Day",
    f"{excess_day:,.0f} L",
)

e2.metric(
    "Excess / Day",
    f"{excess_mass_day:.2f} t",
)

e3.metric(
    "Excess / 30 Days",
    f"{excess_30d:,.0f} L",
)

e4.metric(
    "Potential Cost / Day",
    f"{currency} {excess_cost_day:,.2f}",
)

e5.metric(
    "Potential Cost / 30 Days",
    f"{currency} {excess_cost_30d:,.2f}",
)

# ============================================================
# ACTUAL VS EXPECTED CHART
# ============================================================

comparison_df = pd.DataFrame(
    {
        "Fuel (L/h)": [
            expected_fuel,
            actual_fuel_l_h,
        ]
    },
    index=[
        "Expected",
        "Actual",
    ],
)

st.markdown("### 📊 Expected vs Actual")

st.bar_chart(comparison_df)

# ============================================================
# INTELLIGENCE
# ============================================================

st.subheader("🧠 Fuel Efficiency Intelligence")

recommendations = []

if variance_percent > 15:
    recommendations.append(
        "Critical excess consumption detected. "
        "Verify fuel measurement first, then review engine "
        "condition, propeller/hull resistance and operating conditions."
    )

elif variance_percent > 5:
    recommendations.append(
        "Fuel consumption is above the current estimate. "
        "Review load, RPM, weather, current and vessel condition."
    )

elif variance_percent < -5:
    recommendations.append(
        "Actual consumption is below the estimate. "
        "Confirm flow-meter/tank-sounding accuracy and whether "
        "the operating condition matches the calculation."
    )

else:
    recommendations.append(
        "Actual fuel consumption is within the configured "
        "±5% monitoring band."
    )

if result["load"] < 30:
    recommendations.append(
        "Estimated propulsion load is below 30%. "
        "Long-duration low-load operation should be evaluated "
        "against the engine manufacturer's operating guidance."
    )

if result["load"] > 90:
    recommendations.append(
        "Estimated propulsion load is above 90%. "
        "Confirm that the operating condition is permitted "
        "for the installed engine rating."
    )

if actual_rpm >= rated_rpm * 0.95:
    recommendations.append(
        "Engine is operating at or above 95% of rated RPM."
    )

if speed_knots > 0:
    recommendations.append(
        f"Current estimated fuel intensity is "
        f"{result['l_nm']:.2f} L/NM."
    )

if operation_mode in [
    "Towing",
    "Anchor Handling",
    "DP Operation",
]:
    recommendations.append(
        f"{operation_mode} can produce a load relationship "
        "that differs materially from a simple cubic "
        "free-sailing propeller curve. Use measured shaft "
        "power/fuel-flow or vessel-specific performance data "
        "when available."
    )

for recommendation in recommendations:
    st.write("•", recommendation)

# ============================================================
# ENGINEERING FORMULA
# ============================================================

with st.expander("📐 Engineering Formula & Method"):

    st.markdown(
        r"""
### Power conversion

\[
1\ HP = 0.745699872\ kW
\]

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

The default is:

\[
n = 3
\]

This is a conventional propeller-demand approximation,
not a universal engine fuel curve.

### Fuel mass flow

\[
Fuel_{kg/h}
=
\frac{
Power_{kW}
\times
SFOC_{g/kWh}
}{1000}
\]

### Fuel volume flow

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

### Fuel intensity

\[
Fuel_{L/NM}
=
\frac{
Fuel_{L/h}
}{
Speed_{knots}
}
\]

### Excess fuel

\[
Excess_{L/day}
=
\max(
Actual_{L/h}-Expected_{L/h},0
)
\times RunningHours
\]
"""
    )

# ============================================================
# VALIDATION
# ============================================================

st.subheader("🛡️ Data Quality & Validation")

validation = []

if engine_model not in ENGINE_REFERENCE:
    validation.append(
        "Exact manufacturer rating has not been verified "
        "inside this application for the selected engine."
    )

if base_sfoc == 205.0:
    validation.append(
        "Base SFOC is currently at the default input value. "
        "Replace it with the exact manufacturer/sea-trial value "
        "when available."
    )

if fuel_type != "Custom":
    validation.append(
        "Fuel density is initialized from a generic fuel-type "
        "default. Enter the bunker delivery note/laboratory "
        "density for higher accuracy."
    )

if operation_mode in [
    "Towing",
    "Anchor Handling",
    "DP Operation",
]:
    validation.append(
        "Current operating mode may not follow the standard "
        "cubic propeller-demand relationship."
    )

if not validation:
    st.success(
        "No basic configuration warning detected."
    )
else:
    for item in validation:
        st.warning(item)

# ============================================================
# ENGINEERING NOTICE
# ============================================================

st.warning(
    """
ENGINEERING NOTICE

Expected fuel consumption in this application is an
engineering estimate unless the exact manufacturer
performance curve or calibrated vessel data has been entered.

RPM alone does not uniquely determine fuel consumption.

For commercial, operational or contractual decisions,
validate the calculation against the exact installed engine
rating, manufacturer performance/SFOC curve, propeller/hull
characteristics, fuel density, sea-trial data and calibrated
fuel-flow or tank measurement data.

Towing, anchor handling and DP operations can differ
substantially from a conventional free-sailing propeller curve.
"""
)

st.caption(
    "Vessel Fuel Efficiency & Control Intelligence Center"
)

# ============================================================
# TAHAP 1 — FLEET & VESSEL DATABASE
# Vessel Fuel Efficiency & Control Intelligence Center
# ============================================================

st.divider()

st.header("🚢 Fleet & Vessel Intelligence")

st.caption(
    "Central vessel database for fuel efficiency, engine performance, "
    "bunker monitoring and fleet operational intelligence."
)

# ------------------------------------------------------------
# ASL / AST FLEET DATABASE — 21 VESSELS
# ------------------------------------------------------------

FLEET_DATABASE = [
    {"Vessel": "ASL MANTRUS", "Group": "ASL", "Status": "Active"},
    {"Vessel": "ASL MULIA", "Group": "ASL", "Status": "Active"},
    {"Vessel": "ASL SENTOSA", "Group": "ASL", "Status": "Active"},
    {"Vessel": "ASL VICTORY", "Group": "ASL", "Status": "Active"},
    {"Vessel": "ASL INTAN", "Group": "ASL", "Status": "Active"},
    {"Vessel": "ASL GEMINI", "Group": "ASL", "Status": "Active"},
    {"Vessel": "ASL BEAVER", "Group": "ASL", "Status": "Active"},
    {"Vessel": "ASL CRESST", "Group": "ASL", "Status": "Active"},
    {"Vessel": "ASL CALYPSO", "Group": "ASL", "Status": "Active"},
    {"Vessel": "ASL PHOENIX", "Group": "ASL", "Status": "Active"},
    {"Vessel": "ASL MARINE 8", "Group": "ASL", "Status": "Active"},
    {"Vessel": "AST LEGEND", "Group": "AST", "Status": "Active"},
    {"Vessel": "TERAS HYDRA", "Group": "TERAS", "Status": "Active"},
    {"Vessel": "AST MAJU", "Group": "AST", "Status": "Active"},
    {"Vessel": "KARYA ABADI 8", "Group": "OTHER", "Status": "Active"},
    {"Vessel": "NUSANTARA ABADI 1", "Group": "OTHER", "Status": "Active"},
    {"Vessel": "CAPITOL T2002", "Group": "CAPITOL", "Status": "Active"},
    {"Vessel": "CAPITOL T2001", "Group": "CAPITOL", "Status": "Active"},
    {"Vessel": "TB1000-06", "Group": "TB1000", "Status": "Active"},
    {"Vessel": "TB1000-07", "Group": "TB1000", "Status": "Active"},
    {"Vessel": "WHALE 3", "Group": "WHALE", "Status": "Active"},
]

fleet_df = pd.DataFrame(FLEET_DATABASE)

# ------------------------------------------------------------
# FLEET CONTROL
# ------------------------------------------------------------

fleet_names = fleet_df["Vessel"].tolist()

selected_fleet_vessel = st.selectbox(
    "Select Vessel for Fleet Intelligence",
    fleet_names,
    key="fleet_intelligence_vessel"
)

selected_record = fleet_df[
    fleet_df["Vessel"] == selected_fleet_vessel
].iloc[0]

# Save selected vessel for later intelligence modules
st.session_state["selected_fleet_vessel"] = selected_fleet_vessel

# ------------------------------------------------------------
# FLEET KPI
# ------------------------------------------------------------

active_vessels = int(
    (fleet_df["Status"] == "Active").sum()
)

groups = int(
    fleet_df["Group"].nunique()
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Fleet",
        len(fleet_df)
    )

with col2:
    st.metric(
        "Active Vessels",
        active_vessels
    )

with col3:
    st.metric(
        "Fleet Groups",
        groups
    )

with col4:
    st.metric(
        "Selected Vessel",
        selected_fleet_vessel
    )

# ------------------------------------------------------------
# SELECTED VESSEL
# ------------------------------------------------------------

st.subheader("🛳️ Selected Vessel")

v1, v2, v3 = st.columns(3)

with v1:
    st.metric(
        "Vessel",
        selected_record["Vessel"]
    )

with v2:
    st.metric(
        "Fleet / Group",
        selected_record["Group"]
    )

with v3:
    st.metric(
        "Operational Status",
        selected_record["Status"]
    )

# ------------------------------------------------------------
# FLEET DATABASE TABLE
# ------------------------------------------------------------

st.subheader("📋 Fleet Database")

display_fleet_df = fleet_df.copy()
display_fleet_df.insert(
    0,
    "No.",
    range(1, len(display_fleet_df) + 1)
)

st.dataframe(
    display_fleet_df,
    use_container_width=True,
    hide_index=True
)

# ------------------------------------------------------------
# FLEET READINESS
# ------------------------------------------------------------

st.subheader("🧠 Fleet Intelligence Readiness")

r1, r2, r3, r4 = st.columns(4)

with r1:
    st.metric(
        "Vessels Registered",
        f"{len(fleet_df)}/21"
    )

with r2:
    st.metric(
        "Fuel Intelligence",
        "READY"
    )

with r3:
    st.metric(
        "Engine Intelligence",
        "READY"
    )

with r4:
    st.metric(
        "Fleet Monitoring",
        "ACTIVE"
    )

if len(fleet_df) == 21:
    st.success(
        "✅ TAHAP 1 ACTIVE — 21 vessels are registered in the "
        "Fleet & Vessel Intelligence database."
    )
else:
    st.warning(
        "⚠️ Fleet database does not contain the expected 21 vessels."
    )

st.info(
    "The selected vessel is stored in the application session and "
    "can be used by the next intelligence modules."
)

# ============================================================
# END TAHAP 1
# ============================================================
# ============================================================
# TAHAP 2
# VESSEL TECHNICAL PROFILE & ENGINE DATABASE
# ============================================================

st.divider()

st.header("⚙️ Vessel Technical Profile & Engine Intelligence")
st.caption(
    "Technical vessel and main-engine database connected to "
    "Fleet & Vessel Intelligence."
)

# ------------------------------------------------------------
# SELECTED VESSEL FROM TAHAP 1
# ------------------------------------------------------------

selected_vessel_t2 = st.session_state.get(
    "selected_fleet_vessel",
    fleet_df.iloc[0]["Vessel"]
)

# ------------------------------------------------------------
# TECHNICAL DATABASE
# Initial engineering database.
# Values can be replaced with verified vessel particulars.
# ------------------------------------------------------------

VESSEL_TECHNICAL_DATABASE = {
    vessel: {
        "Vessel Type": "Tugboat",
        "Gross Tonnage": 1000,
        "Engine Maker": "MAN",
        "Engine Model": "MAN B&W",
        "Number of Engines": 2,
        "Rated Power / Engine (kW)": 1500,
        "Rated RPM": 1200,
        "Fuel Type": "MGO",
        "Base SFOC (g/kWh)": 205.0,
        "Fuel Density (kg/L)": 0.850,
    }
    for vessel in fleet_df["Vessel"].tolist()
}

# ------------------------------------------------------------
# LOAD CURRENT VESSEL DATA
# ------------------------------------------------------------

technical = VESSEL_TECHNICAL_DATABASE[selected_vessel_t2]

st.subheader("🚢 Selected Vessel Technical Profile")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Vessel", selected_vessel_t2)
c2.metric("Vessel Type", technical["Vessel Type"])
c3.metric(
    "Gross Tonnage",
    f'{technical["Gross Tonnage"]:,.0f} GT'
)
c4.metric(
    "Main Engines",
    technical["Number of Engines"]
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Engine Maker", technical["Engine Maker"])
c2.metric("Engine Model", technical["Engine Model"])
c3.metric(
    "Rated Power / Engine",
    f'{technical["Rated Power / Engine (kW)"]:,.0f} kW'
)
c4.metric(
    "Rated RPM",
    f'{technical["Rated RPM"]:,.0f}'
)

# ------------------------------------------------------------
# ENGINE POWER INTELLIGENCE
# ------------------------------------------------------------

total_installed_power = (
    technical["Number of Engines"]
    * technical["Rated Power / Engine (kW)"]
)

equivalent_hp = total_installed_power / 0.745699872

st.subheader("⚡ Engine Power Intelligence")

p1, p2, p3, p4 = st.columns(4)

p1.metric(
    "Total Installed Power",
    f"{total_installed_power:,.0f} kW"
)

p2.metric(
    "Equivalent Power",
    f"{equivalent_hp:,.0f} HP"
)

p3.metric(
    "Base SFOC",
    f'{technical["Base SFOC (g/kWh)"]:.1f} g/kWh'
)

p4.metric(
    "Fuel Density",
    f'{technical["Fuel Density (kg/L)"]:.3f} kg/L'
)

# ------------------------------------------------------------
# TECHNICAL DATA EDITOR
# Allows verified vessel data to be entered later.
# ------------------------------------------------------------

st.subheader("🛠️ Technical Data Verification")

with st.expander("Edit / Verify Vessel Technical Data"):

    vessel_type_t2 = st.selectbox(
        "Vessel Type",
        [
            "Tanker",
            "Cargo Vessel",
            "Tugboat",
            "Ocean Tug",
            "AHT",
            "AHTS",
            "Other",
        ],
        index=2,
        key="t2_vessel_type",
    )

    gt_t2 = st.number_input(
        "Gross Tonnage (GT)",
        min_value=1.0,
        value=float(technical["Gross Tonnage"]),
        step=10.0,
        key="t2_gt",
    )

    engine_maker_t2 = st.text_input(
        "Engine Maker",
        value=technical["Engine Maker"],
        key="t2_engine_maker",
    )

    engine_model_t2 = st.text_input(
        "Engine Model / Family",
        value=technical["Engine Model"],
        key="t2_engine_model",
    )

    engines_t2 = st.number_input(
        "Number of Main Engines",
        min_value=1,
        max_value=8,
        value=int(technical["Number of Engines"]),
        step=1,
        key="t2_engine_count",
    )

    power_t2 = st.number_input(
        "Rated Power / Engine (kW)",
        min_value=1.0,
        value=float(
            technical["Rated Power / Engine (kW)"]
        ),
        step=50.0,
        key="t2_power",
    )

    rpm_t2 = st.number_input(
        "Rated RPM",
        min_value=1.0,
        value=float(technical["Rated RPM"]),
        step=10.0,
        key="t2_rpm",
    )

    fuel_type_t2 = st.selectbox(
        "Fuel Type",
        ["MGO", "MDO", "HFO", "VLSFO", "LNG", "Other"],
        key="t2_fuel_type",
    )

    sfoc_t2 = st.number_input(
        "Base SFOC (g/kWh)",
        min_value=100.0,
        max_value=400.0,
        value=float(technical["Base SFOC (g/kWh)"]),
        step=1.0,
        key="t2_sfoc",
    )

    density_t2 = st.number_input(
        "Fuel Density (kg/L)",
        min_value=0.500,
        max_value=1.200,
        value=float(technical["Fuel Density (kg/L)"]),
        step=0.001,
        format="%.3f",
        key="t2_density",
    )

    save_t2 = st.button(
        "💾 Save Verified Technical Profile",
        type="primary",
        use_container_width=True,
    )

# ------------------------------------------------------------
# SAVE VERIFIED PROFILE INTO SESSION
# ------------------------------------------------------------

if save_t2:

    verified_profile = {
        "Vessel": selected_vessel_t2,
        "Vessel Type": vessel_type_t2,
        "Gross Tonnage": gt_t2,
        "Engine Maker": engine_maker_t2,
        "Engine Model": engine_model_t2,
        "Number of Engines": engines_t2,
        "Rated Power / Engine (kW)": power_t2,
        "Rated RPM": rpm_t2,
        "Fuel Type": fuel_type_t2,
        "Base SFOC (g/kWh)": sfoc_t2,
        "Fuel Density (kg/L)": density_t2,
    }

    if "verified_vessel_profiles" not in st.session_state:
        st.session_state["verified_vessel_profiles"] = {}

    st.session_state["verified_vessel_profiles"][
        selected_vessel_t2
    ] = verified_profile

    st.success(
        f"✅ Technical profile for {selected_vessel_t2} "
        "has been saved and verified."
    )

# ------------------------------------------------------------
# DATA READINESS / VALIDATION
# ------------------------------------------------------------

st.subheader("🛡️ Technical Data Readiness")

required_fields = [
    "Vessel Type",
    "Gross Tonnage",
    "Engine Maker",
    "Engine Model",
    "Number of Engines",
    "Rated Power / Engine (kW)",
    "Rated RPM",
    "Fuel Type",
    "Base SFOC (g/kWh)",
    "Fuel Density (kg/L)",
]

completed_fields = sum(
    1
    for field in required_fields
    if technical.get(field) not in [None, "", 0]
)

readiness_percent = (
    completed_fields / len(required_fields)
) * 100

r1, r2, r3, r4 = st.columns(4)

r1.metric(
    "Technical Fields",
    f"{completed_fields}/{len(required_fields)}"
)

r2.metric(
    "Database Readiness",
    f"{readiness_percent:.0f}%"
)

r3.metric(
    "Engine Intelligence",
    "READY"
)

r4.metric(
    "Fuel Calculation",
    "READY"
)

st.progress(readiness_percent / 100)

# ------------------------------------------------------------
# IMPORTANT DATA QUALITY NOTICE
# ------------------------------------------------------------

st.warning(
    "⚠️ Initial technical values are engineering defaults. "
    "Before commercial or operational use, replace them with "
    "verified vessel particulars, engine nameplate data, "
    "manufacturer performance/SFOC curves, bunker density, "
    "and sea-trial or calibrated fuel-consumption data."
)

# ------------------------------------------------------------
# TAHAP 2 STATUS
# ------------------------------------------------------------

if readiness_percent == 100:

    st.success(
        "✅ TAHAP 2 ACTIVE — Vessel Technical Profile & "
        "Engine Database is operational."
    )

else:

    st.warning(
        "⚠️ TAHAP 2 requires additional technical data."
    )

st.info(
    "Technical data from TAHAP 2 is prepared for connection "
    "to the Fuel Efficiency, Bunker, Performance and "
    "Intelligence modules in the next stages."
)

# ============================================================
# END TAHAP 2
# ============================================================
