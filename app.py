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
    """ <style> .main-title { font-size: 34px; font-weight: 800; color: #0B3D5C; margin-bottom: 0px; } .sub-title { font-size: 16px; color: #5B6770; margin-bottom: 20px; } .info-box { padding: 14px; border-radius: 10px; background-color: #F3F7FA; border-left: 5px solid #0B3D5C; margin-bottom: 15px; } .status-normal { padding: 14px; border-radius: 8px; background-color: #E8F5E9; font-weight: 700; } .status-warning { padding: 14px; border-radius: 8px; background-color: #FFF3E0; font-weight: 700; } .status-critical { padding: 14px; border-radius: 8px; background-color: #FFEBEE; font-weight: 700; } .status-low { padding: 14px; border-radius: 8px; background-color: #E3F2FD; font-weight: 700; } </style> """,
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


def propeller_power( rated_kw, actual_rpm, rated_rpm, exponent=3.0, ):
    if rated_kw <= 0 or rated_rpm <= 0:
        return 0.0

    ratio = max(0.0, actual_rpm / rated_rpm)

    return rated_kw * (ratio ** exponent)


def estimated_load_percent( actual_power_kw, rated_kw, ):
    if rated_kw <= 0:
        return 0.0

    return min(
        max(actual_power_kw / rated_kw * 100.0, 0.0),
        100.0,
    )


def corrected_sfoc( base_sfoc, load_percent, ):
    """ Generic part-load correction for estimation only. It is not a substitute for the manufacturer's certified SFOC/load curve. """

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


def calculate_engine( rated_kw, rated_rpm, actual_rpm, base_sfoc, density, running_hours, speed_knots, exponent, engine_count, ):
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
    """ <div class="info-box"> <b>Purpose:</b> Vessel fuel monitoring, RPM/load analysis, fuel-efficiency control, cost monitoring and excess-fuel detection. </div> """,
    unsafe_allow_html=True,
)

# ============================================================
# SIDEBAR — VESSEL
# ============================================================

st.sidebar.header("⚙️ Vessel Configuration")

vessel_name = st.sidebar.text_input(
    "Vessel Name",
    value=st.session_state.get("selected_vessel", "ASL MANTRUS"),
    key="sidebar_vessel_name",
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
        """ <div class="status-low"> 🔵 BELOW ESTIMATE — Actual fuel consumption is materially below the current engineering estimate. Verify measurement quality and operating conditions. </div> """,
        unsafe_allow_html=True,
    )

elif variance_percent <= 5:

    st.markdown(
        """ <div class="status-normal"> ✅ NORMAL — Actual fuel consumption is within ±5% of the current engineering estimate. </div> """,
        unsafe_allow_html=True,
    )

elif variance_percent <= 15:

    st.markdown(
        """ <div class="status-warning"> ⚠️ HIGH CONSUMPTION — Actual fuel consumption is more than 5% above the current estimate. Investigation is recommended. </div> """,
        unsafe_allow_html=True,
    )

else:

    st.markdown(
        """ <div class="status-critical"> 🔴 CRITICAL DEVIATION — Actual consumption is more than 15% above the current estimate. Investigate engine load, hull/propeller condition, weather, current, operating mode and measurement data. </div> """,
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
        r""" ### Power conversion \[ 1\ HP = 0.745699872\ kW \] ### Propeller-law estimate \[ P_{actual} = P_{rated} \left( \frac{RPM_{actual}} {RPM_{rated}} \right)^n \] The default is: \[ n = 3 \] This is a conventional propeller-demand approximation, not a universal engine fuel curve. ### Fuel mass flow \[ Fuel_{kg/h} = \frac{ Power_{kW} \times SFOC_{g/kWh} }{1000} \] ### Fuel volume flow \[ Fuel_{L/h} = \frac{ Fuel_{kg/h} }{ Density_{kg/L} } \] ### Daily fuel \[ Fuel_{L/day} = Fuel_{L/h} \times RunningHours \] ### Fuel intensity \[ Fuel_{L/NM} = \frac{ Fuel_{L/h} }{ Speed_{knots} } \] ### Excess fuel \[ Excess_{L/day} = \max( Actual_{L/h}-Expected_{L/h},0 ) \times RunningHours \] """
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
    """ ENGINEERING NOTICE Expected fuel consumption in this application is an engineering estimate unless the exact manufacturer performance curve or calibrated vessel data has been entered. RPM alone does not uniquely determine fuel consumption. For commercial, operational or contractual decisions, validate the calculation against the exact installed engine rating, manufacturer performance/SFOC curve, propeller/hull characteristics, fuel density, sea-trial data and calibrated fuel-flow or tank measurement data. Towing, anchor handling and DP operations can differ substantially from a conventional free-sailing propeller curve. """
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

# ============================================================
# TAHAP 3
# FUEL CONSUMPTION & PERFORMANCE INTELLIGENCE
# ============================================================

# ------------------------------------------------------------
# TAHAP 3 - FUEL CONSUMPTION & PERFORMANCE INTELLIGENCE
# ------------------------------------------------------------

st.divider()

st.header("⛽ Fuel Consumption & Performance Intelligence")
st.caption(
    "Operational fuel-performance monitoring connected to the "
    "selected vessel and technical engine database."
)

# ------------------------------------------------------------
# SELECTED VESSEL FROM TAHAP 1
# ------------------------------------------------------------

t3_selected_vessel = st.session_state.get(
    "selected_vessel",
    st.session_state.get(
        "sidebar_vessel_name",
        globals().get("vessel_name", "ASL MANTRUS")
    )
)

st.subheader("🚢 Vessel Fuel Performance")

st.info(
    f"Fuel performance analysis for: **{t3_selected_vessel}**"
)

# ------------------------------------------------------------
# TECHNICAL DATA FROM TAHAP 2
# Safe fallback values are provided if a variable name differs.
# ------------------------------------------------------------

t3_engine_count = float(
    st.session_state.get(
        "engine_count",
        globals().get("engine_count", 2)
    )
)

t3_power_per_engine = float(
    st.session_state.get(
        "rated_power_kw",
        globals().get(
            "rated_power_kw",
            globals().get("rated_power", 1500.0)
        )
    )
)

t3_rated_rpm = float(
    st.session_state.get(
        "rated_rpm",
        globals().get("rated_rpm", 1200.0)
    )
)

t3_base_sfoc = float(
    st.session_state.get(
        "base_sfoc",
        globals().get("base_sfoc", 205.0)
    )
)

t3_fuel_density = float(
    st.session_state.get(
        "fuel_density",
        globals().get("fuel_density", 0.850)
    )
)

t3_total_power = t3_engine_count * t3_power_per_engine

# ------------------------------------------------------------
# OPERATING INPUT
# ------------------------------------------------------------

st.subheader("⚙️ Current Operating Data")

t3_c1, t3_c2, t3_c3 = st.columns(3)

with t3_c1:
    t3_actual_rpm = st.number_input(
        "Actual RPM",
        min_value=0.0,
        max_value=max(t3_rated_rpm * 1.10, 100.0),
        value=min(800.0, t3_rated_rpm),
        step=10.0,
        key="t3_actual_rpm"
    )

with t3_c2:
    t3_actual_fuel_lph = st.number_input(
        "Actual Fuel Consumption (L/h)",
        min_value=0.0,
        value=253.0,
        step=1.0,
        key="t3_actual_fuel_lph"
    )

with t3_c3:
    t3_fuel_price = st.number_input(
        "Fuel Price (USD/L)",
        min_value=0.0,
        value=1.00,
        step=0.01,
        format="%.2f",
        key="t3_fuel_price"
    )

t3_c4, t3_c5, t3_c6 = st.columns(3)

with t3_c4:
    t3_speed_kn = st.number_input(
        "Vessel Speed (knots)",
        min_value=0.0,
        value=10.0,
        step=0.1,
        key="t3_speed_kn"
    )

with t3_c5:
    t3_operating_hours = st.number_input(
        "Operating Hours / Day",
        min_value=0.0,
        max_value=24.0,
        value=24.0,
        step=1.0,
        key="t3_operating_hours"
    )

with t3_c6:
    t3_monitor_band = st.number_input(
        "Monitoring Band (%)",
        min_value=1.0,
        max_value=50.0,
        value=5.0,
        step=1.0,
        key="t3_monitor_band"
    )

# ------------------------------------------------------------
# ENGINEERING CALCULATION
# Propeller-law estimate:
# Load fraction approximately proportional to (RPM / Rated RPM)^3
# ------------------------------------------------------------

if t3_rated_rpm > 0:
    t3_rpm_ratio = t3_actual_rpm / t3_rated_rpm
else:
    t3_rpm_ratio = 0.0

t3_rpm_ratio = max(0.0, min(t3_rpm_ratio, 1.10))

t3_load_fraction = t3_rpm_ratio ** 3
t3_load_percent = t3_load_fraction * 100.0

t3_estimated_power = t3_total_power * t3_load_fraction

# Conservative low-load SFOC correction for monitoring only.
if t3_load_percent < 30:
    t3_adjusted_sfoc = t3_base_sfoc * 1.18
elif t3_load_percent < 50:
    t3_adjusted_sfoc = t3_base_sfoc * 1.10
elif t3_load_percent < 75:
    t3_adjusted_sfoc = t3_base_sfoc * 1.04
else:
    t3_adjusted_sfoc = t3_base_sfoc

# kg/h
t3_expected_fuel_kgh = (
    t3_estimated_power * t3_adjusted_sfoc / 1000.0
)

# L/h
if t3_fuel_density > 0:
    t3_expected_fuel_lph = (
        t3_expected_fuel_kgh / t3_fuel_density
    )
else:
    t3_expected_fuel_lph = 0.0

# ------------------------------------------------------------
# VARIANCE & EFFICIENCY
# ------------------------------------------------------------

t3_difference_lph = (
    t3_actual_fuel_lph - t3_expected_fuel_lph
)

if t3_expected_fuel_lph > 0:
    t3_variance_percent = (
        t3_difference_lph / t3_expected_fuel_lph
    ) * 100.0

    t3_efficiency_index = (
        t3_expected_fuel_lph / t3_actual_fuel_lph * 100.0
        if t3_actual_fuel_lph > 0
        else 0.0
    )
else:
    t3_variance_percent = 0.0
    t3_efficiency_index = 0.0

# ------------------------------------------------------------
# DAILY PERFORMANCE
# ------------------------------------------------------------

t3_actual_daily_l = (
    t3_actual_fuel_lph * t3_operating_hours
)

t3_expected_daily_l = (
    t3_expected_fuel_lph * t3_operating_hours
)

t3_excess_lph = max(
    t3_actual_fuel_lph - t3_expected_fuel_lph,
    0.0
)

t3_excess_daily_l = (
    t3_excess_lph * t3_operating_hours
)

t3_excess_30d_l = t3_excess_daily_l * 30.0

t3_excess_daily_t = (
    t3_excess_daily_l * t3_fuel_density / 1000.0
)

t3_cost_day = (
    t3_excess_daily_l * t3_fuel_price
)

t3_cost_30d = t3_cost_day * 30.0

if t3_speed_kn > 0:
    t3_fuel_intensity = (
        t3_actual_fuel_lph / t3_speed_kn
    )
else:
    t3_fuel_intensity = 0.0

# ------------------------------------------------------------
# PERFORMANCE DASHBOARD
# ------------------------------------------------------------

st.subheader("📊 Fuel Performance Dashboard")

t3_m1, t3_m2, t3_m3, t3_m4 = st.columns(4)

t3_m1.metric(
    "Engine Load",
    f"{t3_load_percent:.1f}%"
)

t3_m2.metric(
    "Estimated Power",
    f"{t3_estimated_power:,.0f} kW"
)

t3_m3.metric(
    "Expected Fuel",
    f"{t3_expected_fuel_lph:,.1f} L/h"
)

t3_m4.metric(
    "Actual Fuel",
    f"{t3_actual_fuel_lph:,.1f} L/h"
)

t3_m5, t3_m6, t3_m7, t3_m8 = st.columns(4)

t3_m5.metric(
    "Difference",
    f"{t3_difference_lph:+,.1f} L/h"
)

t3_m6.metric(
    "Variance",
    f"{t3_variance_percent:+.1f}%"
)

t3_m7.metric(
    "Efficiency Index",
    f"{t3_efficiency_index:.1f}%"
)

t3_m8.metric(
    "Fuel Intensity",
    f"{t3_fuel_intensity:.2f} L/NM"
)

# ------------------------------------------------------------
# EXPECTED VS ACTUAL
# ------------------------------------------------------------

st.subheader("🎯 Actual Fuel vs Expected Fuel")

t3_compare_df = pd.DataFrame(
    {
        "Fuel Performance": ["Expected", "Actual"],
        "Fuel Consumption (L/h)": [
            t3_expected_fuel_lph,
            t3_actual_fuel_lph
        ]
    }
)

st.bar_chart(
    t3_compare_df.set_index("Fuel Performance")
)

# ------------------------------------------------------------
# PERFORMANCE STATUS
# ------------------------------------------------------------

st.subheader("🚦 Fuel Efficiency Status")

if t3_expected_fuel_lph <= 0:
    t3_status = "INSUFFICIENT DATA"
    st.warning(
        "⚠️ Expected fuel consumption cannot be calculated "
        "with the current technical inputs."
    )

elif t3_variance_percent > t3_monitor_band:
    t3_status = "HIGH CONSUMPTION"
    st.error(
        f"🔴 HIGH CONSUMPTION — Actual fuel is "
        f"{t3_variance_percent:.1f}% above the current "
        f"engineering estimate."
    )

elif t3_variance_percent < -t3_monitor_band:
    t3_status = "BELOW ESTIMATE"
    st.info(
        f"🔵 BELOW ESTIMATE — Actual fuel is "
        f"{abs(t3_variance_percent):.1f}% below the current "
        f"engineering estimate. Verify operating conditions "
        f"and measurement accuracy."
    )

else:
    t3_status = "NORMAL"
    st.success(
        f"🟢 NORMAL — Actual fuel consumption is within "
        f"±{t3_monitor_band:.0f}% of the current "
        f"engineering estimate."
    )

# ------------------------------------------------------------
# EXCESS FUEL INTELLIGENCE
# ------------------------------------------------------------

st.subheader("💰 Excess Fuel Intelligence")

t3_e1, t3_e2, t3_e3, t3_e4 = st.columns(4)

t3_e1.metric(
    "Excess / Day",
    f"{t3_excess_daily_l:,.0f} L"
)

t3_e2.metric(
    "Excess / Day",
    f"{t3_excess_daily_t:,.2f} t"
)

t3_e3.metric(
    "Excess / 30 Days",
    f"{t3_excess_30d_l:,.0f} L"
)

t3_e4.metric(
    "Potential Cost / 30 Days",
    f"USD {t3_cost_30d:,.2f}"
)

# ------------------------------------------------------------
# INTELLIGENCE ANALYSIS
# ------------------------------------------------------------

st.subheader("🧠 Fuel Performance Intelligence")

if t3_load_percent < 30:
    st.warning(
        "⚠️ Estimated propulsion load is below 30%. "
        "Long-duration low-load operation should be checked "
        "against the engine manufacturer's operating guidance."
    )

if t3_variance_percent > t3_monitor_band:
    st.error(
        "Fuel consumption is above the configured monitoring "
        "band. Investigate operating condition, weather, "
        "current, hull/propeller condition, engine loading, "
        "fuel quality, measurement accuracy and auxiliary loads."
    )

elif abs(t3_variance_percent) <= t3_monitor_band:
    st.success(
        "Fuel consumption is currently inside the configured "
        "monitoring band."
    )

if t3_speed_kn > 0:
    st.info(
        f"Current calculated fuel intensity: "
        f"{t3_fuel_intensity:.2f} L/NM."
    )

# ------------------------------------------------------------
# OPERATIONAL RECOMMENDATIONS
# ------------------------------------------------------------

st.subheader("📋 Priority Actions")

t3_actions = []

if t3_variance_percent > t3_monitor_band:
    t3_actions.extend(
        [
            "Verify actual fuel-flow or tank measurement data.",
            "Check engine load distribution and RPM stability.",
            "Review weather, sea state, current and vessel draft.",
            "Inspect hull and propeller condition where relevant.",
            "Compare performance against verified sea-trial or "
            "manufacturer performance data."
        ]
    )

if t3_load_percent < 30:
    t3_actions.append(
        "Review prolonged low-load operation against engine "
        "manufacturer recommendations."
    )

if t3_fuel_density == 0.850:
    t3_actions.append(
        "Replace the default fuel density with the latest "
        "BDN or laboratory-tested density."
    )

if not t3_actions:
    t3_actions.append(
        "Continue monitoring fuel consumption and record "
        "operational data consistently for trend analysis."
    )

for t3_i, t3_action in enumerate(t3_actions, start=1):
    st.write(f"{t3_i}. {t3_action}")

# ------------------------------------------------------------
# DATA QUALITY & ENGINEERING NOTICE
# ------------------------------------------------------------

st.subheader("🛡️ Data Quality & Validation")

st.warning(
    "Expected fuel consumption is an engineering estimate. "
    "For operational, contractual or commercial decisions, "
    "validate the calculation against the exact installed "
    "engine rating, manufacturer performance/SFOC curves, "
    "propeller and hull characteristics, verified fuel density, "
    "sea-trial data and calibrated fuel-flow or tank measurements."
)

# ------------------------------------------------------------
# SAVE TAHAP 3 RESULTS FOR NEXT MODULES
# ------------------------------------------------------------

st.session_state["t3_fuel_status"] = t3_status
st.session_state["t3_expected_fuel_lph"] = t3_expected_fuel_lph
st.session_state["t3_variance_percent"] = t3_variance_percent
st.session_state["t3_efficiency_index"] = t3_efficiency_index
st.session_state["t3_excess_daily_l"] = t3_excess_daily_l
st.session_state["t3_cost_30d"] = t3_cost_30d
st.session_state["t3_fuel_intensity"] = t3_fuel_intensity

st.success(
    "✅ TAHAP 3 ACTIVE — Fuel Consumption & Performance "
    "Intelligence is operational."
)

st.info(
    "Fuel-performance results from TAHAP 3 are stored in the "
    "application session and prepared for the next intelligence "
    "modules."
)

# ============================================================
# END TAHAP 3
# ============================================================

# ============================================================
# TAHAP 4 — BUNKER & FUEL INVENTORY INTELLIGENCE
# ============================================================

st.divider()

st.header("⛽ Bunker & Fuel Inventory Intelligence")

st.caption(
    "Bunker inventory, fuel ROB, consumption endurance and "
    "fuel-supply intelligence connected to Fleet, Technical "
    "and Fuel Performance modules."
)

# ------------------------------------------------------------
# SELECTED VESSEL FROM PREVIOUS MODULES
# ------------------------------------------------------------

t4_selected_vessel = st.session_state.get(
    "selected_vessel",
    st.session_state.get(
        "sidebar_vessel_name",
        globals().get("vessel_name", "ASL MANTRUS")
    )
)

st.subheader("🚢 Vessel Bunker Status")

st.info(
    f"Bunker & fuel inventory analysis for: **{t4_selected_vessel}**"
)

# ------------------------------------------------------------
# BUNKER OPERATIONAL DATA
# ------------------------------------------------------------

st.subheader("⚙️ Bunker Operational Data")

t4_col1, t4_col2, t4_col3 = st.columns(3)

with t4_col1:
    t4_tank_capacity_l = st.number_input(
        "Fuel Tank Capacity (L)",
        min_value=1.0,
        value=100000.0,
        step=1000.0,
        key="t4_tank_capacity_l"
    )

    t4_rob_l = st.number_input(
        "Current ROB (L)",
        min_value=0.0,
        value=50000.0,
        step=500.0,
        key="t4_rob_l"
    )

with t4_col2:
    t4_daily_consumption_l = st.number_input(
        "Daily Fuel Consumption (L/day)",
        min_value=0.0,
        value=float(
            st.session_state.get(
                "t3_expected_fuel_lph", 250.0
            )
        ) * 24.0,
        step=100.0,
        key="t4_daily_consumption_l"
    )

    t4_reserve_percent = st.number_input(
        "Minimum Reserve (%)",
        min_value=0.0,
        max_value=100.0,
        value=20.0,
        step=1.0,
        key="t4_reserve_percent"
    )

with t4_col3:
    t4_bunker_price = st.number_input(
        "Fuel Price (USD/L)",
        min_value=0.0,
        value=1.0,
        step=0.01,
        key="t4_bunker_price"
    )

    t4_planned_bunker_l = st.number_input(
        "Planned Bunker Quantity (L)",
        min_value=0.0,
        value=0.0,
        step=1000.0,
        key="t4_planned_bunker_l"
    )

# ------------------------------------------------------------
# BUNKER INVENTORY CALCULATIONS
# ------------------------------------------------------------

# Protect calculations from invalid/zero inputs
t4_safe_capacity_l = max(float(t4_tank_capacity_l), 1.0)
t4_safe_daily_consumption_l = max(float(t4_daily_consumption_l), 0.0)

# Current ROB percentage
t4_rob_percent = (
    float(t4_rob_l) / t4_safe_capacity_l
) * 100.0

# Minimum reserve quantity
t4_reserve_l = (
    t4_safe_capacity_l * float(t4_reserve_percent) / 100.0
)

# Fuel available above reserve
t4_usable_fuel_l = max(
    float(t4_rob_l) - t4_reserve_l,
    0.0
)

# Endurance calculations
if t4_safe_daily_consumption_l > 0:
    t4_endurance_days_total = (
        float(t4_rob_l) / t4_safe_daily_consumption_l
    )

    t4_endurance_days_usable = (
        t4_usable_fuel_l / t4_safe_daily_consumption_l
    )
else:
    t4_endurance_days_total = 0.0
    t4_endurance_days_usable = 0.0

# ROB after planned bunker
t4_projected_rob_l = min(
    float(t4_rob_l) + float(t4_planned_bunker_l),
    t4_safe_capacity_l
)

t4_projected_rob_percent = (
    t4_projected_rob_l / t4_safe_capacity_l
) * 100.0

# Available tank space
t4_available_space_l = max(
    t4_safe_capacity_l - float(t4_rob_l),
    0.0
)

# Planned bunker quantity that can physically fit
t4_accepted_bunker_l = min(
    float(t4_planned_bunker_l),
    t4_available_space_l
)

# Estimated bunker cost
t4_planned_bunker_cost = (
    t4_accepted_bunker_l * float(t4_bunker_price)
)

# Days until minimum reserve is reached
if t4_safe_daily_consumption_l > 0:
    t4_days_to_reserve = (
        max(float(t4_rob_l) - t4_reserve_l, 0.0)
        / t4_safe_daily_consumption_l
    )
else:
    t4_days_to_reserve = 0.0

# ------------------------------------------------------------
# BUNKER INVENTORY DASHBOARD
# ------------------------------------------------------------

st.subheader("📊 Bunker Inventory Dashboard")

t4_m1, t4_m2, t4_m3, t4_m4 = st.columns(4)

with t4_m1:
    st.metric(
        "Current ROB",
        f"{t4_rob_l:,.0f} L"
    )

with t4_m2:
    st.metric(
        "Tank Utilization",
        f"{t4_rob_percent:.1f}%"
    )

with t4_m3:
    st.metric(
        "Minimum Reserve",
        f"{t4_reserve_l:,.0f} L"
    )

with t4_m4:
    st.metric(
        "Usable Fuel",
        f"{t4_usable_fuel_l:,.0f} L"
    )


t4_m5, t4_m6, t4_m7, t4_m8 = st.columns(4)

with t4_m5:
    st.metric(
        "Daily Consumption",
        f"{t4_daily_consumption_l:,.0f} L/day"
    )

with t4_m6:
    st.metric(
        "Total Endurance",
        f"{t4_endurance_days_total:.1f} days"
    )

with t4_m7:
    st.metric(
        "Endurance Above Reserve",
        f"{t4_endurance_days_usable:.1f} days"
    )

with t4_m8:
    st.metric(
        "Days to Reserve",
        f"{t4_days_to_reserve:.1f} days"
    )


# ------------------------------------------------------------
# AUTOMATIC BUNKER STATUS
# ------------------------------------------------------------

st.subheader("🚦 Bunker Status")

if float(t4_rob_l) <= 0:
    t4_bunker_status = "EMPTY"

    st.error(
        "🔴 EMPTY — No usable bunker quantity is currently recorded."
    )

elif float(t4_rob_l) <= t4_reserve_l:
    t4_bunker_status = "CRITICAL"

    st.error(
        "🔴 CRITICAL — Current ROB is at or below the configured "
        "minimum reserve level."
    )

elif t4_days_to_reserve <= 1.0:
    t4_bunker_status = "CRITICAL"

    st.error(
        "🔴 CRITICAL — Estimated fuel remaining above reserve "
        "is approximately one day or less."
    )

elif t4_days_to_reserve <= 3.0:
    t4_bunker_status = "LOW"

    st.warning(
        "🟠 LOW — Fuel reserve threshold may be reached within "
        "approximately three days."
    )

elif t4_rob_percent <= 40.0:
    t4_bunker_status = "MONITOR"

    st.warning(
        "🟡 MONITOR — Current ROB is below 40% of configured "
        "tank capacity."
    )

else:
    t4_bunker_status = "NORMAL"

    st.success(
        "🟢 NORMAL — Current bunker inventory is above the "
        "configured minimum reserve."
    )

# ------------------------------------------------------------
# PROJECTED BUNKER & COST INTELLIGENCE
# ------------------------------------------------------------

st.subheader("⛽ Projected Bunker & Cost Intelligence")

t4_p1, t4_p2, t4_p3, t4_p4 = st.columns(4)

with t4_p1:
    st.metric(
        "Available Tank Space",
        f"{t4_available_space_l:,.0f} L"
    )

with t4_p2:
    st.metric(
        "Planned Bunker",
        f"{t4_planned_bunker_l:,.0f} L"
    )

with t4_p3:
    st.metric(
        "Accepted Bunker",
        f"{t4_accepted_bunker_l:,.0f} L"
    )

with t4_p4:
    st.metric(
        "Estimated Bunker Cost",
        f"USD {t4_planned_bunker_cost:,.2f}"
    )


t4_p5, t4_p6 = st.columns(2)

with t4_p5:
    st.metric(
        "Projected ROB",
        f"{t4_projected_rob_l:,.0f} L"
    )

with t4_p6:
    st.metric(
        "Projected Tank Utilization",
        f"{t4_projected_rob_percent:.1f}%"
    )


# ------------------------------------------------------------
# BUNKER PLANNING VALIDATION
# ------------------------------------------------------------

st.subheader("🛡️ Bunker Planning Validation")

if float(t4_planned_bunker_l) > t4_available_space_l:
    st.error(
        "🔴 OVER-CAPACITY WARNING — Planned bunker quantity exceeds "
        "the currently available tank capacity."
    )

    st.info(
        f"Maximum bunker quantity that can currently be accepted: "
        f"{t4_available_space_l:,.0f} L."
    )

elif float(t4_planned_bunker_l) > 0:
    st.success(
        "🟢 Planned bunker quantity is within the currently "
        "available tank capacity."
    )

else:
    st.info(
        "ℹ️ No additional bunker quantity is currently planned."
    )

# ------------------------------------------------------------
# BUNKER INTELLIGENCE
# ------------------------------------------------------------

st.subheader("🧠 Bunker Intelligence")

t4_intelligence = []

if t4_bunker_status == "EMPTY":
    t4_intelligence.append(
        "No usable bunker quantity is currently recorded."
    )

elif t4_bunker_status == "CRITICAL":
    t4_intelligence.append(
        "Fuel inventory has reached a critical operating condition."
    )

elif t4_bunker_status == "LOW":
    t4_intelligence.append(
        "Fuel reserve threshold may be reached within approximately three days."
    )

elif t4_bunker_status == "MONITOR":
    t4_intelligence.append(
        "Fuel inventory should be monitored closely because ROB is below 40%."
    )

else:
    t4_intelligence.append(
        "Current bunker inventory is within the normal operating range."
    )


if float(t4_planned_bunker_l) > t4_available_space_l:
    t4_intelligence.append(
        "Planned bunker quantity exceeds available tank space."
    )

elif float(t4_planned_bunker_l) > 0:
    t4_intelligence.append(
        "Planned bunker quantity can be accommodated within available tank capacity."
    )


if t4_safe_daily_consumption_l > 0:
    t4_intelligence.append(
        f"Estimated time until minimum reserve is reached: "
        f"{t4_days_to_reserve:.1f} days."
    )


for t4_item in t4_intelligence:
    st.write(f"• {t4_item}")


# ------------------------------------------------------------
# PRIORITY ACTIONS
# ------------------------------------------------------------

st.subheader("📋 Priority Actions")

t4_priority_actions = []

if t4_bunker_status == "EMPTY":
    t4_priority_actions.append(
        "Verify ROB immediately and arrange fuel supply before operation."
    )

elif t4_bunker_status == "CRITICAL":
    t4_priority_actions.append(
        "Review voyage requirements and arrange bunker supply immediately."
    )

elif t4_bunker_status == "LOW":
    t4_priority_actions.append(
        "Prepare bunker replenishment plan and confirm the next suitable bunker location."
    )

elif t4_bunker_status == "MONITOR":
    t4_priority_actions.append(
        "Monitor daily fuel consumption and ROB trend."
    )

else:
    t4_priority_actions.append(
        "Continue routine ROB and daily fuel-consumption monitoring."
    )


if float(t4_planned_bunker_l) > t4_available_space_l:
    t4_priority_actions.append(
        f"Reduce planned bunker quantity to no more than "
        f"{t4_available_space_l:,.0f} L based on current available tank space."
    )


if st.session_state.get("t3_fuel_status") in ["HIGH", "CRITICAL"]:
    t4_priority_actions.append(
        "Review the elevated fuel-consumption condition identified in TAHAP 3 "
        "before finalizing the bunker plan."
    )


for t4_number, t4_action in enumerate(t4_priority_actions, start=1):
    st.write(f"{t4_number}. {t4_action}")

# ------------------------------------------------------------
# DATA QUALITY & VALIDATION
# ------------------------------------------------------------

st.subheader("🛡️ Data Quality & Validation")

t4_data_quality_notes = []

if float(t4_tank_capacity_l) <= 0:
    t4_data_quality_notes.append(
        "Fuel tank capacity must be verified."
    )

if float(t4_rob_l) > float(t4_tank_capacity_l):
    t4_data_quality_notes.append(
        "Current ROB exceeds configured tank capacity. Verify tank and ROB data."
    )

if float(t4_daily_consumption_l) <= 0:
    t4_data_quality_notes.append(
        "Daily fuel consumption must be greater than zero for endurance calculations."
    )

if float(t4_reserve_percent) <= 0:
    t4_data_quality_notes.append(
        "Minimum reserve percentage should be reviewed."
    )

if not t4_data_quality_notes:
    st.success(
        "🟢 Bunker operational inputs passed the basic validation checks."
    )
else:
    for t4_note in t4_data_quality_notes:
        st.warning(f"🟠 {t4_note}")

st.info(
    "Bunker endurance and projected ROB are operational planning estimates. "
    "Before bunker procurement or voyage decisions, verify actual tank soundings, "
    "tank calibration tables, fuel density, daily consumption, safety reserve, "
    "voyage requirements and applicable company procedures."
)


# ------------------------------------------------------------
# SAVE TAHAP 4 RESULTS FOR NEXT MODULES
# ------------------------------------------------------------

# Save TAHAP 4 calculated results using separate output keys.
# Do not overwrite keys already owned by Streamlit input widgets.

st.session_state["t4_result_bunker_status"] = t4_bunker_status
st.session_state["t4_result_rob_l"] = float(t4_rob_l)
st.session_state["t4_result_rob_percent"] = t4_rob_percent
st.session_state["t4_result_daily_consumption_l"] = float(t4_daily_consumption_l)
st.session_state["t4_result_reserve_l"] = t4_reserve_l
st.session_state["t4_result_usable_fuel_l"] = t4_usable_fuel_l
st.session_state["t4_result_endurance_days_total"] = t4_endurance_days_total
st.session_state["t4_result_endurance_days_usable"] = t4_endurance_days_usable
st.session_state["t4_result_days_to_reserve"] = t4_days_to_reserve
st.session_state["t4_result_projected_rob_l"] = t4_projected_rob_l
st.session_state["t4_result_projected_rob_percent"] = t4_projected_rob_percent
st.session_state["t4_result_planned_bunker_cost"] = t4_planned_bunker_cost
st.session_state["t4_result_priority_actions"] = t4_priority_actions

st.success(
    "✅ TAHAP 4 ACTIVE — Bunker & Fuel Inventory Intelligence is operational."
)

st.info(
    "Bunker and fuel-inventory results from TAHAP 4 are stored in the "
    "application session and prepared for the next intelligence modules."
)


# ============================================================
# END TAHAP 4
# ============================================================

# ============================================================
# TAHAP 5 — VOYAGE FUEL PLANNING & ENDURANCE INTELLIGENCE
# ============================================================

st.divider()
st.header("🧭 Voyage Fuel Planning & Endurance Intelligence")
st.caption(
    "Voyage fuel requirement, sailing endurance, reserve protection and "
    "bunker sufficiency analysis connected to TAHAP 1–4."
)

t5_selected_vessel = st.session_state.get(
    "selected_fleet_vessel",
    st.session_state.get("sidebar_vessel_name", globals().get("vessel_name", "ASL MANTRUS"))
)

st.subheader("🚢 Voyage Planning Vessel")
st.info(f"Voyage fuel planning for: **{t5_selected_vessel}**")

# Inputs use unique keys so they cannot collide with earlier Streamlit widgets.
st.subheader("⚙️ Voyage Planning Data")
t5_c1, t5_c2, t5_c3 = st.columns(3)

with t5_c1:
    t5_distance_nm = st.number_input(
        "Planned Voyage Distance (NM)", min_value=0.0, value=500.0,
        step=10.0, key="t5_distance_nm"
    )
    t5_speed_kn = st.number_input(
        "Planned Average Speed (knots)", min_value=0.1, value=10.0,
        step=0.1, key="t5_speed_kn"
    )

with t5_c2:
    t5_daily_consumption_l = st.number_input(
        "Planning Fuel Consumption (L/day)", min_value=0.0,
        value=float(st.session_state.get("t4_result_daily_consumption_l", 6000.0)),
        step=100.0, key="t5_daily_consumption_l"
    )
    t5_weather_margin_pct = st.number_input(
        "Weather / Operational Margin (%)", min_value=0.0, max_value=100.0,
        value=10.0, step=1.0, key="t5_weather_margin_pct"
    )

with t5_c3:
    t5_port_allowance_l = st.number_input(
        "Port / Maneuvering Allowance (L)", min_value=0.0, value=2000.0,
        step=100.0, key="t5_port_allowance_l"
    )
    t5_extra_days = st.number_input(
        "Contingency / Standby (days)", min_value=0.0, value=1.0,
        step=0.5, key="t5_extra_days"
    )

# Bring forward verified TAHAP 4 results.
t5_current_rob_l = float(st.session_state.get("t4_result_rob_l", 0.0))
t5_reserve_l = float(st.session_state.get("t4_result_reserve_l", 0.0))
t5_projected_rob_l = float(st.session_state.get("t4_result_projected_rob_l", t5_current_rob_l))
t5_bunker_status_from_t4 = st.session_state.get("t4_result_bunker_status", "UNKNOWN")

# Core calculations.
t5_sailing_hours = (float(t5_distance_nm) / float(t5_speed_kn)) if t5_speed_kn > 0 else 0.0
t5_sailing_days = t5_sailing_hours / 24.0
t5_base_voyage_fuel_l = t5_sailing_days * float(t5_daily_consumption_l)
t5_weather_margin_l = t5_base_voyage_fuel_l * float(t5_weather_margin_pct) / 100.0
t5_standby_fuel_l = float(t5_extra_days) * float(t5_daily_consumption_l)
t5_operational_requirement_l = (
    t5_base_voyage_fuel_l + t5_weather_margin_l +
    float(t5_port_allowance_l) + t5_standby_fuel_l
)
t5_total_required_l = t5_operational_requirement_l + t5_reserve_l
t5_surplus_deficit_l = t5_projected_rob_l - t5_total_required_l
t5_arrival_rob_l = t5_projected_rob_l - t5_operational_requirement_l

if t5_daily_consumption_l > 0:
    t5_available_endurance_days = max(t5_projected_rob_l - t5_reserve_l, 0.0) / t5_daily_consumption_l
else:
    t5_available_endurance_days = 0.0

if t5_total_required_l <= 0:
    t5_status = "DATA REQUIRED"
elif t5_surplus_deficit_l < 0:
    t5_status = "CRITICAL — INSUFFICIENT FUEL"
elif t5_arrival_rob_l < (t5_reserve_l * 1.10):
    t5_status = "WARNING — LOW ARRIVAL MARGIN"
else:
    t5_status = "SUFFICIENT"

st.subheader("📊 Voyage Fuel Planning Dashboard")
t5_m1, t5_m2, t5_m3, t5_m4 = st.columns(4)
t5_m1.metric("Sailing Time", f"{t5_sailing_days:.2f} days")
t5_m2.metric("Operational Fuel", f"{t5_operational_requirement_l:,.0f} L")
t5_m3.metric("Required incl. Reserve", f"{t5_total_required_l:,.0f} L")
t5_m4.metric("Projected ROB Before Voyage", f"{t5_projected_rob_l:,.0f} L")

t5_m5, t5_m6, t5_m7, t5_m8 = st.columns(4)
t5_m5.metric("Arrival ROB", f"{t5_arrival_rob_l:,.0f} L")
t5_m6.metric("Safety Reserve", f"{t5_reserve_l:,.0f} L")
t5_m7.metric("Fuel Surplus / Deficit", f"{t5_surplus_deficit_l:+,.0f} L")
t5_m8.metric("Usable Endurance", f"{t5_available_endurance_days:.2f} days")

st.subheader("🚦 Voyage Fuel Status")
if t5_status == "SUFFICIENT":
    st.success("🟢 SUFFICIENT — Projected fuel covers the voyage plan and configured reserve.")
elif t5_status.startswith("WARNING"):
    st.warning("🟠 WARNING — Fuel is calculated as sufficient, but arrival margin is close to the configured reserve.")
elif t5_status.startswith("CRITICAL"):
    st.error(
        f"🔴 CRITICAL — Estimated fuel shortfall is {abs(t5_surplus_deficit_l):,.0f} L. "
        "Review voyage assumptions and bunker requirement before departure."
    )
else:
    st.warning("🟠 Complete the voyage and consumption inputs before relying on this calculation.")

st.subheader("🧠 Voyage Intelligence")
t5_findings = []
if t5_distance_nm <= 0:
    t5_findings.append("Planned voyage distance has not been entered.")
if t5_daily_consumption_l <= 0:
    t5_findings.append("Planning fuel consumption is missing or zero.")
if t5_weather_margin_pct < 5:
    t5_findings.append("Weather / operational margin is below 5%; verify against company voyage-planning requirements.")
if t5_surplus_deficit_l < 0:
    t5_findings.append(f"Additional fuel requirement is approximately {abs(t5_surplus_deficit_l):,.0f} L under the current assumptions.")
if t5_arrival_rob_l < t5_reserve_l:
    t5_findings.append("Estimated arrival ROB falls below the configured minimum reserve.")
if t5_bunker_status_from_t4 in ["LOW", "CRITICAL"]:
    t5_findings.append("TAHAP 4 indicates an elevated bunker-inventory condition; reconcile bunker status before voyage approval.")
if not t5_findings:
    t5_findings.append("No basic voyage-fuel exception is detected under the current planning assumptions.")
for item in t5_findings:
    st.write("•", item)

st.subheader("📋 Priority Actions")
t5_priority_actions = []
if t5_surplus_deficit_l < 0:
    t5_priority_actions.append("Plan additional bunker before departure and verify available tank capacity.")
if t5_arrival_rob_l < t5_reserve_l:
    t5_priority_actions.append("Do not rely on the current voyage fuel plan until the minimum arrival reserve is restored.")
if t5_weather_margin_pct < 5:
    t5_priority_actions.append("Review weather and operational contingency allowance against company procedures.")
t5_priority_actions.append("Verify route distance, expected speed, weather/current, consumption rate and port/maneuvering allowance before final voyage approval.")
for i, action in enumerate(t5_priority_actions, start=1):
    st.write(f"{i}. {action}")

st.subheader("🛡️ Data Quality & Validation")
t5_validation = []
if t5_projected_rob_l <= 0:
    t5_validation.append("Projected ROB from TAHAP 4 is zero or unavailable.")
if t5_daily_consumption_l <= 0:
    t5_validation.append("Daily fuel consumption must be greater than zero.")
if t5_speed_kn <= 0:
    t5_validation.append("Planned speed must be greater than zero.")
if not t5_validation:
    st.success("🟢 Voyage planning inputs passed the basic validation checks.")
else:
    for note in t5_validation:
        st.warning(f"🟠 {note}")

st.info(
    "Voyage fuel figures are planning estimates. Before operational approval, verify the actual route, "
    "weather/current, vessel condition, loading/towing condition, measured ROB, tank calibration, "
    "fuel density, expected machinery consumption, statutory/company reserves and Master/company requirements."
)

# Save TAHAP 5 outputs for downstream intelligence modules.
st.session_state["t5_result_status"] = t5_status
st.session_state["t5_result_sailing_days"] = t5_sailing_days
st.session_state["t5_result_operational_fuel_l"] = t5_operational_requirement_l
st.session_state["t5_result_total_required_l"] = t5_total_required_l
st.session_state["t5_result_arrival_rob_l"] = t5_arrival_rob_l
st.session_state["t5_result_surplus_deficit_l"] = t5_surplus_deficit_l
st.session_state["t5_result_priority_actions"] = t5_priority_actions

st.success("✅ TAHAP 5 ACTIVE — Voyage Fuel Planning & Endurance Intelligence is operational.")
st.info("TAHAP 5 results are stored in the application session and ready for the next intelligence modules.")

# ============================================================
# END TAHAP 5
# ============================================================

# ================================================================
# TAHAP 6 - FUEL EFFICIENCY PERFORMANCE & DEVIATION INTELLIGENCE
# ================================================================

st.divider()
st.header("📊 Fuel Efficiency Performance & Deviation Intelligence")
st.caption(
    "Actual-versus-baseline fuel performance, excess-fuel detection, "
    "cost impact, deviation intelligence and operational actions."
)

# ------------------------------------------------
# VESSEL CONTEXT
# ------------------------------------------------

t6_selected_vessel = st.session_state.get(
    "selected_fleet_vessel",
    st.session_state.get(
        "sidebar_vessel_name",
        globals().get("vessel_name", "ASL MANTRUS")
    )
)

st.subheader("🚢 Performance Analysis Vessel")
st.info(f"Fuel-efficiency analysis for: **{t6_selected_vessel}**")


# ------------------------------------------------
# INPUT DATA
# ------------------------------------------------

st.subheader("📝 Fuel Performance Data")

t6_c1, t6_c2, t6_c3 = st.columns(3)

with t6_c1:
    t6_actual_daily_fuel = st.number_input(
        "Actual Daily Fuel Consumption (L/day)",
        min_value=0.0,
        value=5000.0,
        step=100.0,
        key="t6_actual_daily_fuel"
    )

    t6_baseline_daily_fuel = st.number_input(
        "Baseline / Target Fuel Consumption (L/day)",
        min_value=0.0,
        value=4800.0,
        step=100.0,
        key="t6_baseline_daily_fuel"
    )


with t6_c2:
    t6_operating_hours = st.number_input(
        "Operating Hours / Day",
        min_value=0.0,
        max_value=24.0,
        value=24.0,
        step=0.5,
        key="t6_operating_hours"
    )

    t6_fuel_price = st.number_input(
        "Fuel Price (USD/L)",
        min_value=0.0,
        value=0.85,
        step=0.01,
        key="t6_fuel_price"
    )


with t6_c3:
    t6_analysis_days = st.number_input(
        "Analysis Period (Days)",
        min_value=1,
        value=30,
        step=1,
        key="t6_analysis_days"
    )

    t6_tolerance_percent = st.number_input(
        "Allowed Deviation (%)",
        min_value=0.0,
        value=5.0,
        step=0.5,
        key="t6_tolerance_percent"
    )


# ------------------------------------------------
# CALCULATIONS
# ------------------------------------------------

t6_actual_daily_fuel = float(t6_actual_daily_fuel)
t6_baseline_daily_fuel = float(t6_baseline_daily_fuel)
t6_operating_hours = float(t6_operating_hours)
t6_fuel_price = float(t6_fuel_price)
t6_analysis_days = int(t6_analysis_days)
t6_tolerance_percent = float(t6_tolerance_percent)

t6_fuel_deviation_l = (
    t6_actual_daily_fuel - t6_baseline_daily_fuel
)

if t6_baseline_daily_fuel > 0:
    t6_deviation_percent = (
        t6_fuel_deviation_l / t6_baseline_daily_fuel
    ) * 100.0
else:
    t6_deviation_percent = 0.0

t6_actual_period_fuel = (
    t6_actual_daily_fuel * t6_analysis_days
)

t6_baseline_period_fuel = (
    t6_baseline_daily_fuel * t6_analysis_days
)

t6_excess_daily_fuel = max(
    t6_actual_daily_fuel - t6_baseline_daily_fuel,
    0.0
)

t6_excess_period_fuel = (
    t6_excess_daily_fuel * t6_analysis_days
)

t6_excess_daily_cost = (
    t6_excess_daily_fuel * t6_fuel_price
)

t6_excess_period_cost = (
    t6_excess_period_fuel * t6_fuel_price
)

if t6_operating_hours > 0:
    t6_actual_hourly_fuel = (
        t6_actual_daily_fuel / t6_operating_hours
    )

    t6_baseline_hourly_fuel = (
        t6_baseline_daily_fuel / t6_operating_hours
    )
else:
    t6_actual_hourly_fuel = 0.0
    t6_baseline_hourly_fuel = 0.0


# ------------------------------------------------
# PERFORMANCE STATUS
# ------------------------------------------------

if t6_baseline_daily_fuel <= 0:
    t6_status = "DATA REQUIRED"

elif t6_deviation_percent <= 0:
    t6_status = "EFFICIENT"

elif t6_deviation_percent <= t6_tolerance_percent:
    t6_status = "NORMAL"

elif t6_deviation_percent <= 10:
    t6_status = "MONITOR"

elif t6_deviation_percent <= 20:
    t6_status = "HIGH"

else:
    t6_status = "CRITICAL"


# ------------------------------------------------
# KPI DASHBOARD
# ------------------------------------------------

st.subheader("📊 Fuel Efficiency KPI")

t6_k1, t6_k2, t6_k3, t6_k4 = st.columns(4)

t6_k1.metric(
    "Actual Consumption",
    f"{t6_actual_daily_fuel:,.0f} L/day"
)

t6_k2.metric(
    "Baseline",
    f"{t6_baseline_daily_fuel:,.0f} L/day"
)

t6_k3.metric(
    "Fuel Deviation",
    f"{t6_deviation_percent:+.1f}%"
)

t6_k4.metric(
    "Performance Status",
    t6_status
)


t6_k5, t6_k6, t6_k7, t6_k8 = st.columns(4)

t6_k5.metric(
    "Excess Fuel",
    f"{t6_excess_daily_fuel:,.0f} L/day"
)

t6_k6.metric(
    "Excess Fuel / Period",
    f"{t6_excess_period_fuel:,.0f} L"
)

t6_k7.metric(
    "Daily Cost Impact",
    f"USD {t6_excess_daily_cost:,.2f}"
)

t6_k8.metric(
    "Period Cost Impact",
    f"USD {t6_excess_period_cost:,.2f}"
)


# ------------------------------------------------
# PERIOD PERFORMANCE
# ------------------------------------------------

st.subheader("📈 Analysis Period Performance")

t6_p1, t6_p2, t6_p3, t6_p4 = st.columns(4)

t6_p1.metric(
    "Analysis Period",
    f"{t6_analysis_days} days"
)

t6_p2.metric(
    "Actual Period Fuel",
    f"{t6_actual_period_fuel:,.0f} L"
)

t6_p3.metric(
    "Baseline Period Fuel",
    f"{t6_baseline_period_fuel:,.0f} L"
)

t6_p4.metric(
    "Operating Hours",
    f"{t6_operating_hours:.1f} h/day"
)


# ------------------------------------------------
# HOURLY PERFORMANCE
# ------------------------------------------------

st.subheader("⏱️ Hourly Fuel Performance")

t6_h1, t6_h2, t6_h3 = st.columns(3)

t6_h1.metric(
    "Actual Hourly Fuel",
    f"{t6_actual_hourly_fuel:,.1f} L/h"
)

t6_h2.metric(
    "Baseline Hourly Fuel",
    f"{t6_baseline_hourly_fuel:,.1f} L/h"
)

t6_h3.metric(
    "Allowed Deviation",
    f"{t6_tolerance_percent:.1f}%"
)


# ------------------------------------------------
# PERFORMANCE INTELLIGENCE
# ------------------------------------------------

st.subheader("🧠 Fuel Performance Intelligence")

t6_intelligence = []

if t6_status == "DATA REQUIRED":
    t6_intelligence.append(
        "A valid baseline fuel-consumption value is required "
        "before fuel-efficiency deviation can be assessed."
    )

elif t6_status == "EFFICIENT":
    t6_intelligence.append(
        "Actual fuel consumption is at or below the selected baseline."
    )

elif t6_status == "NORMAL":
    t6_intelligence.append(
        "Actual fuel consumption is above baseline but remains "
        "within the selected operational tolerance."
    )

elif t6_status == "MONITOR":
    t6_intelligence.append(
        "Fuel consumption is moderately above baseline and should "
        "be monitored for persistent deterioration."
    )

elif t6_status == "HIGH":
    t6_intelligence.append(
        "Fuel consumption shows a significant adverse deviation "
        "from the selected baseline."
    )

elif t6_status == "CRITICAL":
    t6_intelligence.append(
        "Fuel consumption shows a major adverse deviation from "
        "the selected baseline and requires prompt investigation."
    )

if t6_excess_period_fuel > 0:
    t6_intelligence.append(
        f"Estimated excess consumption over {t6_analysis_days} days "
        f"is {t6_excess_period_fuel:,.0f} L."
    )

if t6_excess_period_cost > 0:
    t6_intelligence.append(
        f"Estimated excess-fuel cost impact for the selected period "
        f"is USD {t6_excess_period_cost:,.2f}."
    )

for t6_note in t6_intelligence:
    st.write(f"• {t6_note}")


# ------------------------------------------------
# POTENTIAL CAUSES
# ------------------------------------------------

st.subheader("🔎 Potential Causes / Investigation Areas")

t6_causes = []

if t6_deviation_percent > t6_tolerance_percent:

    t6_causes.extend([
        "Main-engine RPM/load may be outside the economical operating range.",
        "Hull or propeller fouling may be increasing hydrodynamic resistance.",
        "Weather, wind, waves or current may be increasing propulsion demand.",
        "Vessel draft, trim or loading condition may be affecting efficiency.",
        "Auxiliary machinery demand may be higher than the established baseline.",
        "Fuel measurement, tank sounding or calibration data may require verification.",
        "Engine condition, combustion quality or maintenance condition may require review."
    ])

else:
    t6_causes.append(
        "No significant adverse fuel-consumption deviation is indicated "
        "by the selected baseline and tolerance."
    )

for t6_cause in t6_causes:
    st.write(f"• {t6_cause}")


# ------------------------------------------------
# PRIORITY ACTIONS
# ------------------------------------------------

st.subheader("📋 Priority Actions")

t6_priority_actions = []

if t6_status == "DATA REQUIRED":

    t6_priority_actions.append(
        "Enter and verify the vessel's approved baseline or target fuel consumption."
    )

elif t6_status == "EFFICIENT":

    t6_priority_actions.append(
        "Maintain the current operating profile and continue routine fuel monitoring."
    )

elif t6_status == "NORMAL":

    t6_priority_actions.append(
        "Continue monitoring actual consumption against the approved baseline."
    )

elif t6_status == "MONITOR":

    t6_priority_actions.extend([
        "Review RPM, engine load, vessel speed and operating mode.",
        "Compare weather/current and voyage conditions with the baseline condition.",
        "Confirm daily tank soundings and fuel-consumption records."
    ])

elif t6_status == "HIGH":

    t6_priority_actions.extend([
        "Investigate the source of the adverse fuel-consumption deviation.",
        "Review engine performance, RPM/load and machinery operating condition.",
        "Review hull, propeller, draft, trim, weather and voyage conditions.",
        "Verify fuel measurements and baseline assumptions.",
        "Escalate persistent deviation for superintendent review."
    ])

elif t6_status == "CRITICAL":

    t6_priority_actions.extend([
        "Initiate prompt technical and operational investigation.",
        "Verify fuel measurements, tank soundings and calculation inputs.",
        "Review main-engine performance and machinery condition.",
        "Review hull/propeller condition and vessel operating profile.",
        "Assess the operational and financial impact of continued excess consumption.",
        "Escalate significant persistent deviation to responsible management."
    ])

for t6_index, t6_action in enumerate(
    t6_priority_actions,
    start=1
):
    st.write(f"{t6_index}. {t6_action}")


# ------------------------------------------------
# DATA QUALITY & VALIDATION
# ------------------------------------------------

st.subheader("🛡️ Data Quality & Validation")

t6_validation = []

if t6_actual_daily_fuel <= 0:
    t6_validation.append(
        "Actual daily fuel consumption is zero or unavailable."
    )

if t6_baseline_daily_fuel <= 0:
    t6_validation.append(
        "Baseline fuel consumption must be greater than zero."
    )

if t6_operating_hours <= 0:
    t6_validation.append(
        "Operating hours must be greater than zero."
    )

if t6_operating_hours > 24:
    t6_validation.append(
        "Operating hours cannot exceed 24 hours per day."
    )

if t6_fuel_price <= 0:
    t6_validation.append(
        "Fuel price is zero or unavailable; cost-impact calculations "
        "should not be used for commercial decisions."
    )

if not t6_validation:
    st.success(
        "🟢 Fuel performance inputs passed the basic validation checks."
    )
else:
    for t6_warning in t6_validation:
        st.warning(f"🟠 {t6_warning}")


# ------------------------------------------------
# OPERATIONAL CAUTION
# ------------------------------------------------

st.info(
    "Fuel-efficiency results are operational decision-support estimates. "
    "Before technical, commercial or management action, verify actual fuel "
    "measurements, tank soundings, calibration tables, fuel density, engine "
    "performance, RPM/load, vessel speed, draft/trim, hull and propeller "
    "condition, weather/current, operating mode and the approved vessel baseline."
)


# ------------------------------------------------
# SAVE TAHAP 6 RESULTS FOR NEXT MODULES
# ------------------------------------------------

st.session_state["t6_result_vessel"] = t6_selected_vessel
st.session_state["t6_result_status"] = t6_status

st.session_state["t6_result_actual_daily_fuel"] = (
    t6_actual_daily_fuel
)

st.session_state["t6_result_baseline_daily_fuel"] = (
    t6_baseline_daily_fuel
)

st.session_state["t6_result_deviation_l"] = (
    t6_fuel_deviation_l
)

st.session_state["t6_result_deviation_percent"] = (
    t6_deviation_percent
)

st.session_state["t6_result_excess_daily_fuel"] = (
    t6_excess_daily_fuel
)

st.session_state["t6_result_excess_period_fuel"] = (
    t6_excess_period_fuel
)

st.session_state["t6_result_excess_daily_cost"] = (
    t6_excess_daily_cost
)

st.session_state["t6_result_excess_period_cost"] = (
    t6_excess_period_cost
)

st.session_state["t6_result_priority_actions"] = (
    t6_priority_actions
)

st.session_state["t6_result_intelligence"] = (
    t6_intelligence
)


st.success(
    "✅ TAHAP 6 ACTIVE — Fuel Efficiency Performance & "
    "Deviation Intelligence is operational."
)

st.info(
    "TAHAP 6 results are stored in the application session "
    "and prepared for the next intelligence modules."
)


# ================================================================
# END TAHAP 6
# ================================================================

# ================================================================
# TAHAP 7 - FUEL COST & FINANCIAL IMPACT INTELLIGENCE
# ================================================================

st.divider()
st.header("💰 Fuel Cost & Financial Impact Intelligence")
st.caption(
    "Fuel-cost monitoring, baseline comparison, excess-cost detection, "
    "financial exposure and potential fuel-saving intelligence."
)

# ------------------------------------------------
# VESSEL CONTEXT
# ------------------------------------------------

t7_selected_vessel = st.session_state.get(
    "selected_fleet_vessel",
    st.session_state.get(
        "sidebar_vessel_name",
        globals().get("vessel_name", "ASL MANTRUS")
    )
)

st.subheader("🚢 Financial Analysis Vessel")
st.info(f"Fuel-cost analysis for: **{t7_selected_vessel}**")


# ------------------------------------------------
# IMPORT RESULTS FROM TAHAP 6
# ------------------------------------------------

t7_actual_daily_fuel = float(
    st.session_state.get(
        "t6_result_actual_daily_fuel",
        0.0
    )
)

t7_baseline_daily_fuel = float(
    st.session_state.get(
        "t6_result_baseline_daily_fuel",
        0.0
    )
)

t7_deviation_percent = float(
    st.session_state.get(
        "t6_result_deviation_percent",
        0.0
    )
)

t7_t6_status = st.session_state.get(
    "t6_result_status",
    "DATA REQUIRED"
)


# ------------------------------------------------
# FINANCIAL INPUTS
# ------------------------------------------------

st.subheader("📝 Financial Planning Inputs")

t7_c1, t7_c2, t7_c3 = st.columns(3)

with t7_c1:
    t7_fuel_price = st.number_input(
        "Fuel Price (USD/L)",
        min_value=0.0,
        value=0.85,
        step=0.01,
        key="t7_fuel_price"
    )

    t7_analysis_days = st.number_input(
        "Financial Analysis Period (Days)",
        min_value=1,
        value=30,
        step=1,
        key="t7_analysis_days"
    )


with t7_c2:
    t7_budget_daily_fuel = st.number_input(
        "Budget Fuel Consumption (L/day)",
        min_value=0.0,
        value=float(t7_baseline_daily_fuel),
        step=100.0,
        key="t7_budget_daily_fuel"
    )

    t7_budget_fuel_price = st.number_input(
        "Budget Fuel Price (USD/L)",
        min_value=0.0,
        value=0.80,
        step=0.01,
        key="t7_budget_fuel_price"
    )


with t7_c3:
    t7_saving_target_percent = st.number_input(
        "Fuel Saving Target (%)",
        min_value=0.0,
        max_value=100.0,
        value=5.0,
        step=0.5,
        key="t7_saving_target_percent"
    )

    t7_currency_note = st.text_input(
        "Financial Reference",
        value="USD",
        key="t7_currency_note"
    )


# ------------------------------------------------
# NORMALIZE VALUES
# ------------------------------------------------

t7_fuel_price = float(t7_fuel_price)
t7_analysis_days = int(t7_analysis_days)
t7_budget_daily_fuel = float(t7_budget_daily_fuel)
t7_budget_fuel_price = float(t7_budget_fuel_price)
t7_saving_target_percent = float(t7_saving_target_percent)


# ------------------------------------------------
# COST CALCULATIONS
# ------------------------------------------------

t7_actual_daily_cost = (
    t7_actual_daily_fuel * t7_fuel_price
)

t7_actual_period_cost = (
    t7_actual_daily_cost * t7_analysis_days
)

t7_baseline_daily_cost = (
    t7_baseline_daily_fuel * t7_fuel_price
)

t7_baseline_period_cost = (
    t7_baseline_daily_cost * t7_analysis_days
)

t7_budget_daily_cost = (
    t7_budget_daily_fuel * t7_budget_fuel_price
)

t7_budget_period_cost = (
    t7_budget_daily_cost * t7_analysis_days
)

t7_cost_variance_daily = (
    t7_actual_daily_cost - t7_baseline_daily_cost
)

t7_cost_variance_period = (
    t7_actual_period_cost - t7_baseline_period_cost
)

if t7_baseline_daily_cost > 0:
    t7_cost_variance_percent = (
        t7_cost_variance_daily /
        t7_baseline_daily_cost
    ) * 100.0
else:
    t7_cost_variance_percent = 0.0


# ------------------------------------------------
# EXCESS FUEL / COST
# ------------------------------------------------

t7_excess_daily_fuel = max(
    t7_actual_daily_fuel - t7_baseline_daily_fuel,
    0.0
)

t7_excess_period_fuel = (
    t7_excess_daily_fuel * t7_analysis_days
)

t7_excess_daily_cost = (
    t7_excess_daily_fuel * t7_fuel_price
)

t7_excess_period_cost = (
    t7_excess_period_fuel * t7_fuel_price
)


# ------------------------------------------------
# SAVING OPPORTUNITY
# ------------------------------------------------

t7_target_daily_fuel = (
    t7_actual_daily_fuel *
    (1.0 - t7_saving_target_percent / 100.0)
)

t7_target_daily_saving_l = max(
    t7_actual_daily_fuel - t7_target_daily_fuel,
    0.0
)

t7_target_period_saving_l = (
    t7_target_daily_saving_l *
    t7_analysis_days
)

t7_target_daily_saving_cost = (
    t7_target_daily_saving_l *
    t7_fuel_price
)

t7_target_period_saving_cost = (
    t7_target_period_saving_l *
    t7_fuel_price
)


# ------------------------------------------------
# FINANCIAL STATUS
# ------------------------------------------------

if t7_actual_daily_fuel <= 0 or t7_baseline_daily_fuel <= 0:
    t7_status = "DATA REQUIRED"

elif t7_cost_variance_percent <= 0:
    t7_status = "ON / BELOW BASELINE"

elif t7_cost_variance_percent <= 5:
    t7_status = "NORMAL"

elif t7_cost_variance_percent <= 10:
    t7_status = "MONITOR"

elif t7_cost_variance_percent <= 20:
    t7_status = "HIGH COST"

else:
    t7_status = "CRITICAL COST"


# ------------------------------------------------
# FINANCIAL KPI
# ------------------------------------------------

st.subheader("💵 Fuel Cost KPI")

t7_k1, t7_k2, t7_k3, t7_k4 = st.columns(4)

t7_k1.metric(
    "Actual Daily Fuel Cost",
    f"USD {t7_actual_daily_cost:,.2f}"
)

t7_k2.metric(
    "Baseline Daily Cost",
    f"USD {t7_baseline_daily_cost:,.2f}"
)

t7_k3.metric(
    "Daily Cost Variance",
    f"USD {t7_cost_variance_daily:,.2f}"
)

t7_k4.metric(
    "Financial Status",
    t7_status
)


t7_k5, t7_k6, t7_k7, t7_k8 = st.columns(4)

t7_k5.metric(
    "Actual Period Cost",
    f"USD {t7_actual_period_cost:,.2f}"
)

t7_k6.metric(
    "Baseline Period Cost",
    f"USD {t7_baseline_period_cost:,.2f}"
)

t7_k7.metric(
    "Period Cost Variance",
    f"USD {t7_cost_variance_period:,.2f}"
)

t7_k8.metric(
    "Cost Deviation",
    f"{t7_cost_variance_percent:+.1f}%"
)


# ------------------------------------------------
# BUDGET PERFORMANCE
# ------------------------------------------------

st.subheader("📊 Budget Performance")

t7_b1, t7_b2, t7_b3 = st.columns(3)

t7_budget_variance = (
    t7_actual_period_cost -
    t7_budget_period_cost
)

t7_b1.metric(
    "Budget Period Cost",
    f"USD {t7_budget_period_cost:,.2f}"
)

t7_b2.metric(
    "Actual Period Cost",
    f"USD {t7_actual_period_cost:,.2f}"
)

t7_b3.metric(
    "Actual vs Budget",
    f"USD {t7_budget_variance:,.2f}"
)


# ------------------------------------------------
# EXCESS FUEL FINANCIAL EXPOSURE
# ------------------------------------------------

st.subheader("⚠️ Excess Fuel Financial Exposure")

t7_e1, t7_e2, t7_e3, t7_e4 = st.columns(4)

t7_e1.metric(
    "Excess Fuel / Day",
    f"{t7_excess_daily_fuel:,.0f} L"
)

t7_e2.metric(
    "Excess Fuel / Period",
    f"{t7_excess_period_fuel:,.0f} L"
)

t7_e3.metric(
    "Excess Cost / Day",
    f"USD {t7_excess_daily_cost:,.2f}"
)

t7_e4.metric(
    "Excess Cost / Period",
    f"USD {t7_excess_period_cost:,.2f}"
)


# ------------------------------------------------
# SAVING OPPORTUNITY
# ------------------------------------------------

st.subheader("💡 Potential Fuel Saving")

t7_s1, t7_s2, t7_s3, t7_s4 = st.columns(4)

t7_s1.metric(
    "Saving Target",
    f"{t7_saving_target_percent:.1f}%"
)

t7_s2.metric(
    "Target Consumption",
    f"{t7_target_daily_fuel:,.0f} L/day"
)

t7_s3.metric(
    "Potential Fuel Saving",
    f"{t7_target_period_saving_l:,.0f} L"
)

t7_s4.metric(
    "Potential Cost Saving",
    f"USD {t7_target_period_saving_cost:,.2f}"
)


# ------------------------------------------------
# FINANCIAL INTELLIGENCE
# ------------------------------------------------

st.subheader("🧠 Financial Intelligence")

t7_intelligence = []

if t7_status == "DATA REQUIRED":

    t7_intelligence.append(
        "TAHAP 6 actual and baseline fuel data are required "
        "before financial performance can be assessed."
    )

elif t7_status == "ON / BELOW BASELINE":

    t7_intelligence.append(
        "Actual fuel cost is at or below the selected baseline."
    )

elif t7_status == "NORMAL":

    t7_intelligence.append(
        "Fuel cost is slightly above baseline but remains "
        "within the normal monitoring range."
    )

elif t7_status == "MONITOR":

    t7_intelligence.append(
        "Fuel-cost deviation requires closer operational monitoring."
    )

elif t7_status == "HIGH COST":

    t7_intelligence.append(
        "Fuel-cost performance shows a significant adverse deviation."
    )

elif t7_status == "CRITICAL COST":

    t7_intelligence.append(
        "Fuel-cost exposure shows a major adverse deviation "
        "requiring prompt operational and commercial review."
    )


if t7_excess_period_cost > 0:
    t7_intelligence.append(
        f"Estimated excess fuel expenditure over "
        f"{t7_analysis_days} days is "
        f"USD {t7_excess_period_cost:,.2f}."
    )


if t7_budget_variance > 0:
    t7_intelligence.append(
        f"Projected fuel expenditure is "
        f"USD {t7_budget_variance:,.2f} above the selected budget."
    )

elif t7_budget_variance < 0:
    t7_intelligence.append(
        f"Projected fuel expenditure is "
        f"USD {abs(t7_budget_variance):,.2f} below the selected budget."
    )


if t7_target_period_saving_cost > 0:
    t7_intelligence.append(
        f"A {t7_saving_target_percent:.1f}% consumption reduction "
        f"would represent approximately "
        f"USD {t7_target_period_saving_cost:,.2f} "
        f"over the selected period, subject to operational feasibility."
    )


for t7_note in t7_intelligence:
    st.write(f"• {t7_note}")


# ------------------------------------------------
# PRIORITY ACTIONS
# ------------------------------------------------

st.subheader("📋 Priority Actions")

t7_priority_actions = []

if t7_status == "DATA REQUIRED":

    t7_priority_actions.append(
        "Verify actual and baseline fuel-consumption data from TAHAP 6."
    )

elif t7_status == "ON / BELOW BASELINE":

    t7_priority_actions.append(
        "Maintain the current operating profile and continue "
        "fuel-cost monitoring."
    )

elif t7_status == "NORMAL":

    t7_priority_actions.append(
        "Continue monitoring fuel consumption and cost "
        "against the approved baseline and budget."
    )

elif t7_status == "MONITOR":

    t7_priority_actions.extend([
        "Review the source of fuel-consumption deviation.",
        "Compare actual fuel price with budget assumptions.",
        "Review voyage, speed, RPM/load and operating conditions.",
        "Track whether the adverse cost variance persists."
    ])

elif t7_status == "HIGH COST":

    t7_priority_actions.extend([
        "Investigate the operational cause of excess fuel consumption.",
        "Review engine efficiency and vessel operating profile.",
        "Review bunker price and procurement assumptions.",
        "Quantify avoidable excess-fuel expenditure.",
        "Escalate persistent adverse variance for management review."
    ])

elif t7_status == "CRITICAL COST":

    t7_priority_actions.extend([
        "Initiate prompt operational and commercial investigation.",
        "Verify fuel-consumption measurements and financial inputs.",
        "Review engine, vessel, voyage and environmental conditions.",
        "Assess immediate opportunities to reduce avoidable fuel use.",
        "Review bunker procurement and fuel-price exposure.",
        "Escalate significant financial exposure to responsible management."
    ])


for t7_index, t7_action in enumerate(
    t7_priority_actions,
    start=1
):
    st.write(f"{t7_index}. {t7_action}")


# ------------------------------------------------
# DATA QUALITY & VALIDATION
# ------------------------------------------------

st.subheader("🛡️ Data Quality & Validation")

t7_validation = []

if t7_actual_daily_fuel <= 0:
    t7_validation.append(
        "Actual daily fuel consumption from TAHAP 6 "
        "is zero or unavailable."
    )

if t7_baseline_daily_fuel <= 0:
    t7_validation.append(
        "Baseline daily fuel consumption from TAHAP 6 "
        "is zero or unavailable."
    )

if t7_fuel_price <= 0:
    t7_validation.append(
        "Actual fuel price must be greater than zero "
        "for reliable cost calculations."
    )

if t7_budget_fuel_price <= 0:
    t7_validation.append(
        "Budget fuel price must be greater than zero "
        "for budget comparison."
    )

if t7_analysis_days <= 0:
    t7_validation.append(
        "Financial analysis period must be greater than zero."
    )


if not t7_validation:

    st.success(
        "🟢 Fuel financial inputs passed the basic validation checks."
    )

else:

    for t7_warning in t7_validation:
        st.warning(f"🟠 {t7_warning}")


# ------------------------------------------------
# FINANCIAL CAUTION
# ------------------------------------------------

st.info(
    "Fuel-cost and saving figures are planning estimates. "
    "Before commercial approval, budgeting, bunker procurement or "
    "management action, verify actual bunker invoices, contracted prices, "
    "fuel density, measured consumption, tank soundings, currency basis, "
    "taxes, port charges, voyage requirements and applicable company procedures."
)


# ------------------------------------------------
# SAVE TAHAP 7 RESULTS
# ------------------------------------------------

st.session_state["t7_result_vessel"] = t7_selected_vessel
st.session_state["t7_result_status"] = t7_status

st.session_state["t7_result_actual_daily_cost"] = (
    t7_actual_daily_cost
)

st.session_state["t7_result_baseline_daily_cost"] = (
    t7_baseline_daily_cost
)

st.session_state["t7_result_actual_period_cost"] = (
    t7_actual_period_cost
)

st.session_state["t7_result_baseline_period_cost"] = (
    t7_baseline_period_cost
)

st.session_state["t7_result_cost_variance_daily"] = (
    t7_cost_variance_daily
)

st.session_state["t7_result_cost_variance_period"] = (
    t7_cost_variance_period
)

st.session_state["t7_result_cost_variance_percent"] = (
    t7_cost_variance_percent
)

st.session_state["t7_result_excess_period_cost"] = (
    t7_excess_period_cost
)

st.session_state["t7_result_budget_variance"] = (
    t7_budget_variance
)

st.session_state["t7_result_potential_saving_cost"] = (
    t7_target_period_saving_cost
)

st.session_state["t7_result_priority_actions"] = (
    t7_priority_actions
)

st.session_state["t7_result_intelligence"] = (
    t7_intelligence
)


st.success(
    "✅ TAHAP 7 ACTIVE — Fuel Cost & Financial Impact "
    "Intelligence is operational."
)

st.info(
    "TAHAP 7 results are stored in the application session "
    "and prepared for the next intelligence modules."
)


# ================================================================
# END TAHAP 7
# ================================================================

# ================================================================
# TAHAP 8 - FUEL RISK, ALERT & MANAGEMENT DECISION INTELLIGENCE
# ================================================================

st.divider()
st.header("🚨 Fuel Risk, Alert & Management Decision Intelligence")
st.caption(
    "Integrated fuel-risk assessment, management alerts, operational "
    "decision support and priority-action intelligence using results "
    "from the previous intelligence modules."
)

# ---------------------------------------------------------------
# VESSEL CONTEXT
# ---------------------------------------------------------------

t8_selected_vessel = st.session_state.get(
    "selected_fleet_vessel",
    st.session_state.get(
        "sidebar_vessel_name",
        globals().get("vessel_name", "ASL MANTRUS")
    )
)

st.subheader("🚢 Management Review Vessel")
st.info(f"Integrated fuel-risk assessment for: **{t8_selected_vessel}**")


# ---------------------------------------------------------------
# COLLECT RESULTS FROM PREVIOUS MODULES
# ---------------------------------------------------------------

t8_bunker_status = st.session_state.get(
    "t4_result_bunker_status",
    "UNKNOWN"
)

t8_rob_l = float(
    st.session_state.get(
        "t4_result_rob_l",
        0.0
    ) or 0.0
)

t8_rob_percent = float(
    st.session_state.get(
        "t4_result_rob_percent",
        0.0
    ) or 0.0
)

t8_daily_consumption_l = float(
    st.session_state.get(
        "t4_result_daily_consumption_l",
        0.0
    ) or 0.0
)

t8_days_to_reserve = float(
    st.session_state.get(
        "t4_result_days_to_reserve",
        0.0
    ) or 0.0
)

t8_projected_rob_l = float(
    st.session_state.get(
        "t4_result_projected_rob_l",
        0.0
    ) or 0.0
)

t8_projected_rob_percent = float(
    st.session_state.get(
        "t4_result_projected_rob_percent",
        0.0
    ) or 0.0
)

t8_voyage_status = st.session_state.get(
    "t5_result_status",
    "UNKNOWN"
)

t8_arrival_rob_l = float(
    st.session_state.get(
        "t5_result_arrival_rob_l",
        0.0
    ) or 0.0
)

t8_surplus_deficit_l = float(
    st.session_state.get(
        "t5_result_surplus_deficit_l",
        0.0
    ) or 0.0
)

t8_performance_status = st.session_state.get(
    "t6_result_status",
    "UNKNOWN"
)

t8_excess_period_fuel = float(
    st.session_state.get(
        "t6_result_excess_period_fuel",
        0.0
    ) or 0.0
)

t8_excess_daily_cost = float(
    st.session_state.get(
        "t6_result_excess_daily_cost",
        0.0
    ) or 0.0
)

t8_excess_period_cost = float(
    st.session_state.get(
        "t6_result_excess_period_cost",
        0.0
    ) or 0.0
)


# ---------------------------------------------------------------
# OPTIONAL TAHAP 7 FINANCIAL RESULTS
# ---------------------------------------------------------------

def t8_first_number(keys, default=0.0):
    for key in keys:
        value = st.session_state.get(key, None)

        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass

    return float(default)


t8_financial_variance = t8_first_number(
    [
        "t7_result_cost_variance",
        "t7_result_financial_variance",
        "t7_result_cost_impact",
        "t7_result_excess_cost",
    ],
    0.0
)

t8_projected_cost = t8_first_number(
    [
        "t7_result_projected_cost",
        "t7_result_total_cost",
        "t7_result_period_cost",
    ],
    0.0
)

t8_saving_opportunity = t8_first_number(
    [
        "t7_result_saving_opportunity",
        "t7_result_potential_saving",
        "t7_result_savings",
    ],
    0.0
)


# ---------------------------------------------------------------
# MANAGEMENT RISK SETTINGS
# ---------------------------------------------------------------

st.subheader("⚙️ Management Risk Thresholds")

t8_c1, t8_c2, t8_c3 = st.columns(3)

with t8_c1:
    t8_min_rob_percent = st.number_input(
        "Minimum ROB Threshold (%)",
        min_value=0.0,
        max_value=100.0,
        value=20.0,
        step=1.0,
        key="t8_min_rob_percent"
    )

with t8_c2:
    t8_min_endurance_days = st.number_input(
        "Minimum Endurance Warning (days)",
        min_value=0.0,
        value=3.0,
        step=0.5,
        key="t8_min_endurance_days"
    )

with t8_c3:
    t8_cost_alert_threshold = st.number_input(
        "Cost Alert Threshold",
        min_value=0.0,
        value=1000.0,
        step=100.0,
        key="t8_cost_alert_threshold"
    )


# ---------------------------------------------------------------
# INTEGRATED RISK SCORING
# ---------------------------------------------------------------

t8_risk_score = 0
t8_risk_factors = []
t8_management_alerts = []
t8_priority_actions = []


# Bunker / ROB risk
if t8_rob_percent <= 0:
    t8_risk_score += 25
    t8_risk_factors.append(
        "Current ROB percentage is zero or unavailable."
    )

elif t8_rob_percent < t8_min_rob_percent:
    t8_risk_score += 25
    t8_risk_factors.append(
        "Current ROB is below the management minimum threshold."
    )

elif t8_rob_percent < (t8_min_rob_percent + 10):
    t8_risk_score += 10
    t8_risk_factors.append(
        "Current ROB is approaching the management minimum threshold."
    )


# Bunker status risk
if str(t8_bunker_status).upper() in ["EMPTY", "CRITICAL"]:
    t8_risk_score += 25
    t8_risk_factors.append(
        f"Bunker inventory status is {t8_bunker_status}."
    )

elif str(t8_bunker_status).upper() in ["LOW", "MONITOR"]:
    t8_risk_score += 10
    t8_risk_factors.append(
        f"Bunker inventory requires attention: {t8_bunker_status}."
    )


# Endurance risk
if (
    t8_days_to_reserve > 0
    and t8_days_to_reserve <= t8_min_endurance_days
):
    t8_risk_score += 20
    t8_risk_factors.append(
        "Fuel reserve threshold may be reached within the "
        "management warning period."
    )


# Voyage fuel sufficiency risk
if t8_surplus_deficit_l < 0:
    t8_risk_score += 25
    t8_risk_factors.append(
        "Voyage fuel planning indicates a fuel deficit."
    )

if t8_arrival_rob_l < 0:
    t8_risk_score += 25
    t8_risk_factors.append(
        "Projected arrival ROB is below zero."
    )


# Performance deviation risk
if t8_excess_period_fuel > 0:
    t8_risk_score += 10
    t8_risk_factors.append(
        "Excess fuel consumption has been detected for the "
        "analysis period."
    )


# Cost risk
t8_combined_cost_impact = max(
    t8_excess_period_cost,
    t8_financial_variance,
    0.0
)

if t8_combined_cost_impact >= t8_cost_alert_threshold:
    t8_risk_score += 15
    t8_risk_factors.append(
        "Fuel-related cost impact exceeds the management alert threshold."
    )


# Cap score at 100
t8_risk_score = min(t8_risk_score, 100)


# ---------------------------------------------------------------
# RISK CLASSIFICATION
# ---------------------------------------------------------------

if t8_risk_score >= 70:
    t8_risk_level = "CRITICAL"

elif t8_risk_score >= 45:
    t8_risk_level = "HIGH"

elif t8_risk_score >= 20:
    t8_risk_level = "MEDIUM"

else:
    t8_risk_level = "LOW"


# ---------------------------------------------------------------
# MANAGEMENT ALERT GENERATION
# ---------------------------------------------------------------

if t8_risk_level == "CRITICAL":
    t8_management_alerts.append(
        "Immediate management review is required."
    )
    t8_priority_actions.append(
        "Verify actual ROB by tank sounding and confirm available "
        "usable fuel immediately."
    )
    t8_priority_actions.append(
        "Review voyage requirement, reserve requirement and bunker "
        "availability before continuing the planned operation."
    )

elif t8_risk_level == "HIGH":
    t8_management_alerts.append(
        "Fuel risk requires prompt superintendent and operational review."
    )
    t8_priority_actions.append(
        "Verify fuel inventory, consumption trend and voyage requirement."
    )

elif t8_risk_level == "MEDIUM":
    t8_management_alerts.append(
        "Fuel condition requires increased monitoring."
    )
    t8_priority_actions.append(
        "Monitor ROB, consumption, endurance and financial deviation "
        "against approved limits."
    )

else:
    t8_management_alerts.append(
        "No major integrated fuel-risk condition is currently indicated."
    )
    t8_priority_actions.append(
        "Continue routine fuel, performance and cost monitoring."
    )


if t8_surplus_deficit_l < 0:
    t8_priority_actions.append(
        "Review voyage fuel plan and arrange additional bunker if "
        "required before voyage approval."
    )

if t8_excess_period_fuel > 0:
    t8_priority_actions.append(
        "Investigate excess consumption against RPM/load, speed, "
        "weather/current, draft/trim, hull and propeller condition."
    )

if t8_combined_cost_impact >= t8_cost_alert_threshold:
    t8_priority_actions.append(
        "Review the financial impact of excess consumption and verify "
        "fuel price, invoices and approved operating budget."
    )


# Remove duplicate actions while preserving order
t8_priority_actions = list(dict.fromkeys(t8_priority_actions))
t8_management_alerts = list(dict.fromkeys(t8_management_alerts))


# ---------------------------------------------------------------
# INTEGRATED MANAGEMENT DASHBOARD
# ---------------------------------------------------------------

st.subheader("📊 Integrated Fuel Risk Dashboard")

t8_m1, t8_m2, t8_m3, t8_m4 = st.columns(4)

t8_m1.metric(
    "Integrated Risk Score",
    f"{t8_risk_score}/100"
)

t8_m2.metric(
    "Risk Level",
    t8_risk_level
)

t8_m3.metric(
    "Current ROB",
    f"{t8_rob_percent:,.1f}%"
)

t8_m4.metric(
    "Days to Reserve",
    f"{t8_days_to_reserve:,.1f}"
)


t8_m5, t8_m6, t8_m7, t8_m8 = st.columns(4)

t8_m5.metric(
    "Projected ROB",
    f"{t8_projected_rob_percent:,.1f}%"
)

t8_m6.metric(
    "Voyage Surplus / Deficit",
    f"{t8_surplus_deficit_l:,.1f} L"
)

t8_m7.metric(
    "Excess Period Fuel",
    f"{t8_excess_period_fuel:,.1f} L"
)

t8_m8.metric(
    "Cost Impact",
    f"{t8_combined_cost_impact:,.2f}"
)


# ---------------------------------------------------------------
# RISK STATUS DISPLAY
# ---------------------------------------------------------------

st.subheader("🚦 Integrated Risk Status")

if t8_risk_level == "CRITICAL":
    st.error(
        "🔴 CRITICAL — Immediate management and operational review required."
    )

elif t8_risk_level == "HIGH":
    st.error(
        "🟠 HIGH — Significant fuel risk requires prompt management review."
    )

elif t8_risk_level == "MEDIUM":
    st.warning(
        "🟡 MEDIUM — Increased monitoring and corrective review recommended."
    )

else:
    st.success(
        "🟢 LOW — No major integrated fuel-risk condition currently indicated."
    )


# ---------------------------------------------------------------
# RISK FACTORS
# ---------------------------------------------------------------

st.subheader("🔎 Detected Risk Factors")

if t8_risk_factors:
    for t8_index, t8_factor in enumerate(t8_risk_factors, start=1):
        st.write(f"{t8_index}. {t8_factor}")

else:
    st.success(
        "No significant integrated fuel-risk factors were detected "
        "from the available module results."
    )


# ---------------------------------------------------------------
# MANAGEMENT ALERTS
# ---------------------------------------------------------------

st.subheader("🚨 Management Alerts")

for t8_index, t8_alert in enumerate(t8_management_alerts, start=1):
    st.write(f"{t8_index}. {t8_alert}")


# ---------------------------------------------------------------
# PRIORITY ACTIONS
# ---------------------------------------------------------------

st.subheader("📋 Priority Actions")

for t8_index, t8_action in enumerate(t8_priority_actions, start=1):
    st.write(f"{t8_index}. {t8_action}")


# ---------------------------------------------------------------
# DATA QUALITY & VALIDATION
# ---------------------------------------------------------------

st.subheader("🛡️ Data Quality & Validation")

t8_validation = []

if t8_daily_consumption_l <= 0:
    t8_validation.append(
        "Daily fuel consumption is zero or unavailable."
    )

if t8_rob_l < 0:
    t8_validation.append(
        "Current ROB cannot be negative."
    )

if t8_rob_percent < 0:
    t8_validation.append(
        "Current ROB percentage cannot be negative."
    )

if not t8_validation:
    st.success(
        "🟢 Integrated fuel-risk inputs passed the basic validation checks."
    )

else:
    for t8_note in t8_validation:
        st.warning(f"🟠 {t8_note}")


st.info(
    "Integrated fuel-risk results are operational decision-support "
    "estimates. Before safety-critical, commercial or voyage decisions, "
    "verify actual tank soundings, calibration tables, fuel density, "
    "measured ROB, machinery consumption, voyage requirements, weather "
    "and current, statutory/company reserves, bunker availability, "
    "supplier information and applicable company procedures."
)


# ---------------------------------------------------------------
# SAVE TAHAP 8 RESULTS FOR NEXT MODULES
# ---------------------------------------------------------------

st.session_state["t8_result_vessel"] = t8_selected_vessel
st.session_state["t8_result_risk_score"] = t8_risk_score
st.session_state["t8_result_risk_level"] = t8_risk_level
st.session_state["t8_result_risk_factors"] = t8_risk_factors
st.session_state["t8_result_management_alerts"] = t8_management_alerts
st.session_state["t8_result_priority_actions"] = t8_priority_actions
st.session_state["t8_result_rob_percent"] = t8_rob_percent
st.session_state["t8_result_days_to_reserve"] = t8_days_to_reserve
st.session_state["t8_result_surplus_deficit_l"] = t8_surplus_deficit_l
st.session_state["t8_result_excess_period_fuel"] = t8_excess_period_fuel
st.session_state["t8_result_cost_impact"] = t8_combined_cost_impact
st.session_state["t8_result_projected_cost"] = t8_projected_cost
st.session_state["t8_result_saving_opportunity"] = t8_saving_opportunity


st.success(
    "✅ TAHAP 8 ACTIVE — Fuel Risk, Alert & Management Decision "
    "Intelligence is operational."
)

st.info(
    "TAHAP 8 results are stored in the application session "
    "and prepared for the next intelligence modules."
)


# ================================================================
# END TAHAP 8
# ================================================================

# ================================================================
# TAHAP 9 - FUEL OPTIMIZATION & OPERATING STRATEGY INTELLIGENCE
# ================================================================

st.divider()
st.header("⚙️ Fuel Optimization & Operating Strategy Intelligence")
st.caption(
    "Integrated operating-strategy recommendations using fuel inventory, "
    "voyage planning, performance deviation, financial impact and risk results."
)

# ------------------------------------------------
# VESSEL CONTEXT
# ------------------------------------------------

t9_selected_vessel = st.session_state.get(
    "selected_fleet_vessel",
    st.session_state.get(
        "sidebar_vessel_name",
        globals().get("vessel_name", "ASL MANTRUS")
    )
)

st.subheader("🚢 Optimization Vessel")
st.info(f"Fuel optimization analysis for: **{t9_selected_vessel}**")


# ------------------------------------------------
# COLLECT RESULTS FROM PREVIOUS MODULES
# ------------------------------------------------

t9_rob_l = float(
    st.session_state.get(
        "t4_result_rob_l",
        0.0
    ) or 0.0
)

t9_rob_percent = float(
    st.session_state.get(
        "t4_result_rob_percent",
        0.0
    ) or 0.0
)

t9_daily_consumption_l = float(
    st.session_state.get(
        "t4_result_daily_consumption_l",
        0.0
    ) or 0.0
)

t9_days_to_reserve = float(
    st.session_state.get(
        "t8_result_days_to_reserve",
        st.session_state.get(
            "t4_result_days_to_reserve",
            0.0
        )
    ) or 0.0
)

t9_sailing_days = float(
    st.session_state.get(
        "t5_result_sailing_days",
        0.0
    ) or 0.0
)

t9_total_required_l = float(
    st.session_state.get(
        "t5_result_total_required_l",
        0.0
    ) or 0.0
)

t9_arrival_rob_l = float(
    st.session_state.get(
        "t5_result_arrival_rob_l",
        0.0
    ) or 0.0
)

t9_surplus_deficit_l = float(
    st.session_state.get(
        "t8_result_surplus_deficit_l",
        st.session_state.get(
            "t5_result_surplus_deficit_l",
            0.0
        )
    ) or 0.0
)

t9_excess_period_fuel = float(
    st.session_state.get(
        "t8_result_excess_period_fuel",
        st.session_state.get(
            "t6_result_excess_period_fuel",
            0.0
        )
    ) or 0.0
)

t9_cost_impact = float(
    st.session_state.get(
        "t8_result_cost_impact",
        0.0
    ) or 0.0
)

t9_projected_cost = float(
    st.session_state.get(
        "t8_result_projected_cost",
        0.0
    ) or 0.0
)

t9_saving_opportunity = float(
    st.session_state.get(
        "t8_result_saving_opportunity",
        0.0
    ) or 0.0
)


# ------------------------------------------------
# OPTIMIZATION INPUTS
# ------------------------------------------------

st.subheader("🎯 Optimization Targets")

t9_c1, t9_c2, t9_c3 = st.columns(3)

with t9_c1:
    t9_reduction_target_pct = st.number_input(
        "Fuel Reduction Target (%)",
        min_value=0.0,
        max_value=30.0,
        value=5.0,
        step=0.5,
        key="t9_reduction_target_pct"
    )

with t9_c2:
    t9_speed_reduction_pct = st.number_input(
        "Potential Speed Reduction (%)",
        min_value=0.0,
        max_value=30.0,
        value=5.0,
        step=0.5,
        key="t9_speed_reduction_pct"
    )

with t9_c3:
    t9_analysis_days = st.number_input(
        "Optimization Period (days)",
        min_value=1.0,
        max_value=365.0,
        value=30.0,
        step=1.0,
        key="t9_analysis_days"
    )


# ------------------------------------------------
# OPTIMIZATION CALCULATIONS
# ------------------------------------------------

t9_reduction_fraction = t9_reduction_target_pct / 100.0

t9_target_daily_consumption_l = (
    t9_daily_consumption_l * (1.0 - t9_reduction_fraction)
)

t9_daily_fuel_saving_l = max(
    t9_daily_consumption_l - t9_target_daily_consumption_l,
    0.0
)

t9_period_fuel_saving_l = (
    t9_daily_fuel_saving_l * t9_analysis_days
)

if t9_target_daily_consumption_l > 0:
    t9_optimized_endurance_days = (
        t9_rob_l / t9_target_daily_consumption_l
    )
else:
    t9_optimized_endurance_days = 0.0

if t9_daily_consumption_l > 0:
    t9_current_endurance_days = (
        t9_rob_l / t9_daily_consumption_l
    )
else:
    t9_current_endurance_days = 0.0

t9_endurance_gain_days = max(
    t9_optimized_endurance_days - t9_current_endurance_days,
    0.0
)

if t9_analysis_days > 0:
    t9_average_daily_cost_impact = (
        t9_cost_impact / t9_analysis_days
    )
else:
    t9_average_daily_cost_impact = 0.0

if t9_daily_consumption_l > 0:
    t9_estimated_saving_value = (
        t9_cost_impact
        * (
            t9_daily_fuel_saving_l
            / t9_daily_consumption_l
        )
    )
else:
    t9_estimated_saving_value = 0.0

t9_estimated_saving_value = max(
    t9_estimated_saving_value,
    t9_saving_opportunity,
    0.0
)


# ------------------------------------------------
# OPTIMIZATION STATUS
# ------------------------------------------------

if t9_rob_l <= 0:
    t9_status = "DATA REQUIRED"

elif t9_surplus_deficit_l < 0:
    t9_status = "FUEL SECURITY PRIORITY"

elif t9_rob_percent > 0 and t9_rob_percent <= 20:
    t9_status = "RESERVE PROTECTION"

elif t9_excess_period_fuel > 0:
    t9_status = "EFFICIENCY RECOVERY"

else:
    t9_status = "OPTIMIZED MONITORING"


# ------------------------------------------------
# KPI DASHBOARD
# ------------------------------------------------

st.subheader("📊 Optimization Dashboard")

t9_k1, t9_k2, t9_k3, t9_k4 = st.columns(4)

t9_k1.metric(
    "Current Daily Fuel",
    f"{t9_daily_consumption_l:,.1f} L/day"
)

t9_k2.metric(
    "Target Daily Fuel",
    f"{t9_target_daily_consumption_l:,.1f} L/day"
)

t9_k3.metric(
    "Potential Daily Saving",
    f"{t9_daily_fuel_saving_l:,.1f} L/day"
)

t9_k4.metric(
    "Optimization Status",
    t9_status
)

t9_k5, t9_k6, t9_k7, t9_k8 = st.columns(4)

t9_k5.metric(
    "Period Fuel Saving",
    f"{t9_period_fuel_saving_l:,.1f} L"
)

t9_k6.metric(
    "Current Endurance",
    f"{t9_current_endurance_days:,.1f} days"
)

t9_k7.metric(
    "Optimized Endurance",
    f"{t9_optimized_endurance_days:,.1f} days"
)

t9_k8.metric(
    "Endurance Gain",
    f"{t9_endurance_gain_days:,.1f} days"
)


# ------------------------------------------------
# OPERATING STRATEGY INTELLIGENCE
# ------------------------------------------------

st.subheader("🧠 Operating Strategy Intelligence")

t9_intelligence = []

if t9_rob_l <= 0:
    t9_intelligence.append(
        "Reliable ROB data is required before fuel optimization can be approved."
    )

if t9_surplus_deficit_l < 0:
    t9_intelligence.append(
        "Fuel sufficiency has priority over efficiency optimization because "
        "the integrated voyage assessment indicates a fuel deficit."
    )

if t9_excess_period_fuel > 0:
    t9_intelligence.append(
        "Excess consumption has been detected. Investigate RPM/load, vessel "
        "speed, weather/current, draft/trim, hull and propeller condition."
    )

if t9_reduction_target_pct > 0:
    t9_intelligence.append(
        f"A {t9_reduction_target_pct:.1f}% fuel-reduction target would reduce "
        f"estimated daily consumption by approximately "
        f"{t9_daily_fuel_saving_l:,.1f} L/day."
    )

if t9_endurance_gain_days > 0:
    t9_intelligence.append(
        f"The optimization target could increase theoretical fuel endurance "
        f"by approximately {t9_endurance_gain_days:,.1f} days."
    )

if t9_speed_reduction_pct > 0:
    t9_intelligence.append(
        f"A potential speed adjustment of up to "
        f"{t9_speed_reduction_pct:.1f}% may be evaluated where voyage, "
        f"charter, weather, maneuvering and safety requirements permit."
    )

if not t9_intelligence:
    t9_intelligence.append(
        "Continue monitoring fuel performance against the approved operating baseline."
    )

for t9_item in t9_intelligence:
    st.write(f"• {t9_item}")


# ------------------------------------------------
# RECOMMENDED OPERATING STRATEGY
# ------------------------------------------------

st.subheader("🧭 Recommended Operating Strategy")

t9_priority_actions = []

if t9_rob_l <= 0:
    t9_priority_actions.append(
        "Verify actual ROB by tank sounding and approved calibration tables."
    )

if t9_surplus_deficit_l < 0:
    t9_priority_actions.append(
        "Review bunker requirement and reserve protection before voyage approval."
    )

if t9_excess_period_fuel > 0:
    t9_priority_actions.append(
        "Investigate the root cause of excess consumption before increasing "
        "the optimization target."
    )

if t9_speed_reduction_pct > 0:
    t9_priority_actions.append(
        "Evaluate economical speed only where safe navigation, schedule, "
        "charter and operational requirements permit."
    )

t9_priority_actions.append(
    "Compare actual daily consumption with the approved baseline and "
    "optimization target."
)

t9_priority_actions.append(
    "Verify engine RPM/load, vessel speed, draft/trim, weather/current and "
    "hull/propeller condition before implementing operational changes."
)

for t9_index, t9_action in enumerate(t9_priority_actions, start=1):
    st.write(f"{t9_index}. {t9_action}")


# ------------------------------------------------
# MANAGEMENT SUMMARY
# ------------------------------------------------

st.subheader("📋 Management Optimization Summary")

t9_summary = pd.DataFrame(
    {
        "Parameter": [
            "Vessel",
            "Optimization Status",
            "Current Daily Consumption",
            "Target Daily Consumption",
            "Daily Fuel Saving",
            "Period Fuel Saving",
            "Current Endurance",
            "Optimized Endurance",
            "Endurance Gain",
            "Existing Saving Opportunity",
        ],
        "Result": [
            t9_selected_vessel,
            t9_status,
            f"{t9_daily_consumption_l:,.1f} L/day",
            f"{t9_target_daily_consumption_l:,.1f} L/day",
            f"{t9_daily_fuel_saving_l:,.1f} L/day",
            f"{t9_period_fuel_saving_l:,.1f} L",
            f"{t9_current_endurance_days:,.1f} days",
            f"{t9_optimized_endurance_days:,.1f} days",
            f"{t9_endurance_gain_days:,.1f} days",
            f"{t9_saving_opportunity:,.2f}",
        ],
    }
)

st.dataframe(
    t9_summary,
    use_container_width=True,
    hide_index=True
)


# ------------------------------------------------
# DATA QUALITY & VALIDATION
# ------------------------------------------------

st.subheader("🛡️ Data Quality & Validation")

t9_validation = []

if t9_rob_l <= 0:
    t9_validation.append(
        "ROB from the previous fuel-inventory module is zero or unavailable."
    )

if t9_daily_consumption_l <= 0:
    t9_validation.append(
        "Daily fuel consumption is zero or unavailable."
    )

if t9_analysis_days <= 0:
    t9_validation.append(
        "Optimization period must be greater than zero."
    )

if not t9_validation:
    st.success(
        "🟢 Fuel optimization inputs passed the basic validation checks."
    )
else:
    for t9_note in t9_validation:
        st.warning(f"🟠 {t9_note}")


st.info(
    "Fuel-optimization results are decision-support estimates. Before changing "
    "vessel speed, RPM/load, voyage plan or bunker strategy, verify actual "
    "fuel measurements, machinery limitations, OEM guidance, weather/current, "
    "navigation safety, charter requirements, statutory/company reserves and "
    "Master/company approval."
)


# ------------------------------------------------
# SAVE TAHAP 9 RESULTS
# ------------------------------------------------

st.session_state["t9_result_status"] = t9_status

st.session_state["t9_result_target_daily_consumption_l"] = (
    t9_target_daily_consumption_l
)

st.session_state["t9_result_daily_fuel_saving_l"] = (
    t9_daily_fuel_saving_l
)

st.session_state["t9_result_period_fuel_saving_l"] = (
    t9_period_fuel_saving_l
)

st.session_state["t9_result_optimized_endurance_days"] = (
    t9_optimized_endurance_days
)

st.session_state["t9_result_endurance_gain_days"] = (
    t9_endurance_gain_days
)

st.session_state["t9_result_estimated_saving_value"] = (
    t9_estimated_saving_value
)

st.session_state["t9_result_priority_actions"] = (
    t9_priority_actions
)

st.session_state["t9_result_intelligence"] = (
    t9_intelligence
)


st.success(
    "✅ TAHAP 9 ACTIVE — Fuel Optimization & Operating Strategy "
    "Intelligence is operational."
)

st.info(
    "TAHAP 9 results are stored in the application session "
    "and prepared for the next intelligence modules."
)


# ================================================================
# END TAHAP 9
# ================================================================

# ================================================================
# TAHAP 10 - MANAGEMENT KPI & FUEL PERFORMANCE CONTROL INTELLIGENCE
# ================================================================

st.divider()
st.header("📊 Management KPI & Fuel Performance Control Intelligence")

st.caption(
    "Executive fuel-performance control integrating inventory, voyage, "
    "consumption deviation, financial impact, risk and optimization results."
)


# ------------------------------------------------
# VESSEL CONTEXT
# ------------------------------------------------

t10_selected_vessel = st.session_state.get(
    "selected_fleet_vessel",
    st.session_state.get(
        "sidebar_vessel_name",
        globals().get("vessel_name", "ASL MANTRUS")
    )
)

st.subheader("🚢 Management Control Vessel")
st.info(f"Management fuel-performance assessment for: **{t10_selected_vessel}**")


# ------------------------------------------------
# COLLECT PREVIOUS INTELLIGENCE RESULTS
# ------------------------------------------------

t10_rob_l = float(
    st.session_state.get("t4_result_rob_l", 0.0) or 0.0
)

t10_rob_percent = float(
    st.session_state.get("t4_result_rob_percent", 0.0) or 0.0
)

t10_daily_consumption_l = float(
    st.session_state.get(
        "t4_result_daily_consumption_l",
        0.0
    ) or 0.0
)

t10_sailing_days = float(
    st.session_state.get(
        "t5_result_sailing_days",
        0.0
    ) or 0.0
)

t10_arrival_rob_l = float(
    st.session_state.get(
        "t5_result_arrival_rob_l",
        0.0
    ) or 0.0
)

t10_surplus_deficit_l = float(
    st.session_state.get(
        "t8_result_surplus_deficit_l",
        st.session_state.get(
            "t5_result_surplus_deficit_l",
            0.0
        )
    ) or 0.0
)

t10_excess_period_fuel = float(
    st.session_state.get(
        "t8_result_excess_period_fuel",
        st.session_state.get(
            "t6_result_excess_period_fuel",
            0.0
        )
    ) or 0.0
)

t10_cost_impact = float(
    st.session_state.get(
        "t8_result_cost_impact",
        0.0
    ) or 0.0
)

t10_projected_cost = float(
    st.session_state.get(
        "t8_result_projected_cost",
        0.0
    ) or 0.0
)

t10_saving_opportunity = float(
    st.session_state.get(
        "t8_result_saving_opportunity",
        0.0
    ) or 0.0
)

t10_target_daily_consumption_l = float(
    st.session_state.get(
        "t9_result_target_daily_consumption_l",
        t10_daily_consumption_l
    ) or 0.0
)

t10_daily_fuel_saving_l = float(
    st.session_state.get(
        "t9_result_daily_fuel_saving_l",
        0.0
    ) or 0.0
)

t10_period_fuel_saving_l = float(
    st.session_state.get(
        "t9_result_period_fuel_saving_l",
        0.0
    ) or 0.0
)

t10_optimized_endurance_days = float(
    st.session_state.get(
        "t9_result_optimized_endurance_days",
        0.0
    ) or 0.0
)

t10_endurance_gain_days = float(
    st.session_state.get(
        "t9_result_endurance_gain_days",
        0.0
    ) or 0.0
)

t10_estimated_saving_value = float(
    st.session_state.get(
        "t9_result_estimated_saving_value",
        0.0
    ) or 0.0
)

t10_t9_status = st.session_state.get(
    "t9_result_status",
    "NOT AVAILABLE"
)


# ------------------------------------------------
# MANAGEMENT KPI CALCULATIONS
# ------------------------------------------------

if t10_daily_consumption_l > 0:
    t10_reduction_pct = (
        (
            t10_daily_consumption_l
            - t10_target_daily_consumption_l
        )
        / t10_daily_consumption_l
    ) * 100.0
else:
    t10_reduction_pct = 0.0


if t10_daily_consumption_l > 0:
    t10_excess_ratio_pct = (
        t10_excess_period_fuel
        / max(t10_daily_consumption_l, 1.0)
    ) * 100.0
else:
    t10_excess_ratio_pct = 0.0


# ------------------------------------------------
# FUEL SECURITY SCORE
# ------------------------------------------------

if t10_rob_l <= 0:
    t10_fuel_security_score = 0

elif t10_surplus_deficit_l < 0:
    t10_fuel_security_score = 25

elif 0 < t10_rob_percent <= 20:
    t10_fuel_security_score = 50

elif 20 < t10_rob_percent <= 40:
    t10_fuel_security_score = 75

else:
    t10_fuel_security_score = 100


# ------------------------------------------------
# EFFICIENCY SCORE
# ------------------------------------------------

if t10_daily_consumption_l <= 0:
    t10_efficiency_score = 0

elif t10_excess_period_fuel <= 0:
    t10_efficiency_score = 100

elif t10_reduction_pct >= 10:
    t10_efficiency_score = 85

elif t10_reduction_pct >= 5:
    t10_efficiency_score = 75

else:
    t10_efficiency_score = 60


# ------------------------------------------------
# OPTIMIZATION SCORE
# ------------------------------------------------

if t10_daily_consumption_l <= 0:
    t10_optimization_score = 0

elif t10_daily_fuel_saving_l > 0:
    t10_optimization_score = 100

else:
    t10_optimization_score = 70


# ------------------------------------------------
# DATA QUALITY SCORE
# ------------------------------------------------

t10_data_quality_score = 100

if t10_rob_l <= 0:
    t10_data_quality_score -= 35

if t10_daily_consumption_l <= 0:
    t10_data_quality_score -= 35

if t10_sailing_days <= 0:
    t10_data_quality_score -= 15

if t10_target_daily_consumption_l <= 0:
    t10_data_quality_score -= 15

t10_data_quality_score = max(
    min(t10_data_quality_score, 100),
    0
)


# ------------------------------------------------
# OVERALL MANAGEMENT SCORE
# ------------------------------------------------

t10_overall_score = (
    (t10_fuel_security_score * 0.35)
    + (t10_efficiency_score * 0.30)
    + (t10_optimization_score * 0.20)
    + (t10_data_quality_score * 0.15)
)

t10_overall_score = round(t10_overall_score, 1)


# ------------------------------------------------
# MANAGEMENT STATUS
# ------------------------------------------------

if t10_rob_l <= 0 or t10_daily_consumption_l <= 0:
    t10_management_status = "DATA ATTENTION"

elif t10_surplus_deficit_l < 0:
    t10_management_status = "CRITICAL FUEL CONTROL"

elif t10_overall_score >= 90:
    t10_management_status = "STRONG CONTROL"

elif t10_overall_score >= 75:
    t10_management_status = "CONTROLLED"

elif t10_overall_score >= 60:
    t10_management_status = "MONITOR"

else:
    t10_management_status = "MANAGEMENT ACTION REQUIRED"


# ------------------------------------------------
# EXECUTIVE KPI DASHBOARD
# ------------------------------------------------

st.subheader("📈 Executive Fuel KPI Dashboard")

t10_k1, t10_k2, t10_k3, t10_k4 = st.columns(4)

t10_k1.metric(
    "Overall Control Score",
    f"{t10_overall_score:.1f}/100"
)

t10_k2.metric(
    "Fuel Security",
    f"{t10_fuel_security_score}/100"
)

t10_k3.metric(
    "Efficiency",
    f"{t10_efficiency_score}/100"
)

t10_k4.metric(
    "Optimization",
    f"{t10_optimization_score}/100"
)

t10_k5, t10_k6, t10_k7, t10_k8 = st.columns(4)

t10_k5.metric(
    "ROB",
    f"{t10_rob_l:,.0f} L"
)

t10_k6.metric(
    "Daily Consumption",
    f"{t10_daily_consumption_l:,.1f} L/day"
)

t10_k7.metric(
    "Target Consumption",
    f"{t10_target_daily_consumption_l:,.1f} L/day"
)

t10_k8.metric(
    "Management Status",
    t10_management_status
)


# ------------------------------------------------
# PERFORMANCE CONTROL TABLE
# ------------------------------------------------

st.subheader("📋 Performance Control Matrix")

t10_control_df = pd.DataFrame(
    {
        "Control Area": [
            "Fuel Security",
            "Fuel Efficiency",
            "Optimization",
            "Data Quality",
            "Overall Management Control",
        ],
        "Score": [
            t10_fuel_security_score,
            t10_efficiency_score,
            t10_optimization_score,
            t10_data_quality_score,
            t10_overall_score,
        ],
        "Maximum": [
            100,
            100,
            100,
            100,
            100,
        ],
    }
)

st.dataframe(
    t10_control_df,
    use_container_width=True,
    hide_index=True
)


# ------------------------------------------------
# MANAGEMENT INTELLIGENCE
# ------------------------------------------------

st.subheader("🧠 Management Intelligence")

t10_intelligence = []

if t10_surplus_deficit_l < 0:
    t10_intelligence.append(
        "Fuel sufficiency requires immediate management review because "
        "the integrated voyage assessment indicates a deficit."
    )

if 0 < t10_rob_percent <= 20:
    t10_intelligence.append(
        "ROB is within the reserve-protection range. Bunker planning and "
        "voyage fuel requirements should be reviewed."
    )

if t10_excess_period_fuel > 0:
    t10_intelligence.append(
        "Excess fuel consumption remains an efficiency-control issue and "
        "should be investigated against RPM/load, speed and operating conditions."
    )

if t10_daily_fuel_saving_l > 0:
    t10_intelligence.append(
        f"The current optimization target indicates a potential saving of "
        f"approximately {t10_daily_fuel_saving_l:,.1f} L/day."
    )

if t10_endurance_gain_days > 0:
    t10_intelligence.append(
        f"Optimized operation indicates a theoretical endurance improvement "
        f"of approximately {t10_endurance_gain_days:,.1f} days."
    )

if t10_cost_impact > 0:
    t10_intelligence.append(
        f"Recorded integrated cost impact is approximately "
        f"{t10_cost_impact:,.2f} in the configured financial basis."
    )

if not t10_intelligence:
    t10_intelligence.append(
        "Fuel-performance indicators are currently within the configured "
        "management-control logic."
    )

for t10_item in t10_intelligence:
    st.write(f"• {t10_item}")


# ------------------------------------------------
# MANAGEMENT PRIORITY ACTIONS
# ------------------------------------------------

st.subheader("📌 Management Priority Actions")

t10_priority_actions = []

if t10_rob_l <= 0:
    t10_priority_actions.append(
        "Verify actual ROB using tank soundings and approved calibration tables."
    )

if t10_surplus_deficit_l < 0:
    t10_priority_actions.append(
        "Review bunker requirement, voyage requirement and reserve protection."
    )

if t10_excess_period_fuel > 0:
    t10_priority_actions.append(
        "Investigate excess consumption against RPM/load, vessel speed, "
        "weather/current, draft/trim and hull/propeller condition."
    )

if t10_daily_fuel_saving_l > 0:
    t10_priority_actions.append(
        "Track actual consumption against the optimization target and record "
        "verified fuel savings."
    )

if t10_data_quality_score < 100:
    t10_priority_actions.append(
        "Complete missing or unreliable operational inputs before management approval."
    )

t10_priority_actions.append(
    "Review fuel performance during the next vessel-management reporting cycle."
)

for t10_i, t10_action in enumerate(
    t10_priority_actions,
    start=1
):
    st.write(f"{t10_i}. {t10_action}")


# ------------------------------------------------
# EXECUTIVE SUMMARY
# ------------------------------------------------

st.subheader("🗂️ Executive Management Summary")

t10_summary_df = pd.DataFrame(
    {
        "Parameter": [
            "Vessel",
            "Management Status",
            "Overall Control Score",
            "Fuel Security Score",
            "Efficiency Score",
            "Optimization Score",
            "Data Quality Score",
            "ROB",
            "Current Daily Consumption",
            "Target Daily Consumption",
            "Potential Daily Saving",
            "Period Fuel Saving",
            "Optimized Endurance",
            "Endurance Gain",
            "Optimization Status",
        ],
        "Result": [
            t10_selected_vessel,
            t10_management_status,
            f"{t10_overall_score:.1f}/100",
            f"{t10_fuel_security_score}/100",
            f"{t10_efficiency_score}/100",
            f"{t10_optimization_score}/100",
            f"{t10_data_quality_score}/100",
            f"{t10_rob_l:,.0f} L",
            f"{t10_daily_consumption_l:,.1f} L/day",
            f"{t10_target_daily_consumption_l:,.1f} L/day",
            f"{t10_daily_fuel_saving_l:,.1f} L/day",
            f"{t10_period_fuel_saving_l:,.1f} L",
            f"{t10_optimized_endurance_days:,.1f} days",
            f"{t10_endurance_gain_days:,.1f} days",
            t10_t9_status,
        ],
    }
)

st.dataframe(
    t10_summary_df,
    use_container_width=True,
    hide_index=True
)


# ------------------------------------------------
# DATA QUALITY & VALIDATION
# ------------------------------------------------

st.subheader("🛡️ Data Quality & Validation")

t10_validation = []

if t10_rob_l <= 0:
    t10_validation.append(
        "Fuel ROB is zero or unavailable."
    )

if t10_daily_consumption_l <= 0:
    t10_validation.append(
        "Daily fuel consumption is zero or unavailable."
    )

if t10_target_daily_consumption_l <= 0:
    t10_validation.append(
        "Optimization target consumption is zero or unavailable."
    )

if not t10_validation:
    st.success(
        "🟢 Management fuel-control inputs passed the basic validation checks."
    )
else:
    for t10_note in t10_validation:
        st.warning(f"🟠 {t10_note}")


st.info(
    "Management KPI scores are decision-support indicators generated from "
    "the application's configured logic. They are not substitutes for verified "
    "tank measurements, engine performance analysis, OEM limits, navigation "
    "requirements, charter obligations, statutory/company fuel reserves, "
    "approved budgets or Master/company authorization."
)


# ------------------------------------------------
# SAVE TAHAP 10 RESULTS
# ------------------------------------------------

st.session_state["t10_result_management_status"] = (
    t10_management_status
)

st.session_state["t10_result_overall_score"] = (
    t10_overall_score
)

st.session_state["t10_result_fuel_security_score"] = (
    t10_fuel_security_score
)

st.session_state["t10_result_efficiency_score"] = (
    t10_efficiency_score
)

st.session_state["t10_result_optimization_score"] = (
    t10_optimization_score
)

st.session_state["t10_result_data_quality_score"] = (
    t10_data_quality_score
)

st.session_state["t10_result_priority_actions"] = (
    t10_priority_actions
)

st.session_state["t10_result_intelligence"] = (
    t10_intelligence
)


st.success(
    "✅ TAHAP 10 ACTIVE — Management KPI & Fuel Performance "
    "Control Intelligence is operational."
)

st.info(
    "TAHAP 10 results are stored in the application session "
    "and prepared for the next intelligence modules."
)


# ================================================================
# END TAHAP 10
# ================================================================

# ============================================================
# TAHAP 11 - FLEET BENCHMARK & PERFORMANCE RANKING INTELLIGENCE
# ============================================================

st.divider()
st.header("🏆 Fleet Benchmark & Performance Ranking Intelligence")

st.caption(
    "Integrated vessel performance benchmarking using fuel efficiency, "
    "optimization, data quality, operating risk and management KPI results."
)

# ------------------------------------------------------------
# VESSEL CONTEXT
# ------------------------------------------------------------

t11_selected_vessel = st.session_state.get(
    "selected_fleet_vessel",
    st.session_state.get(
        "sidebar_vessel_name",
        globals().get("vessel_name", "ASL MANTRUS")
    )
)

st.subheader("🚢 Benchmark Vessel")
st.info(f"Performance benchmark analysis for: **{t11_selected_vessel}**")


# ------------------------------------------------------------
# SAFE NUMBER FUNCTION
# ------------------------------------------------------------

def t11_safe_float(value, default=0.0):
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


# ------------------------------------------------------------
# COLLECT PREVIOUS INTELLIGENCE RESULTS
# ------------------------------------------------------------

t11_efficiency_score = t11_safe_float(
    st.session_state.get("t10_result_efficiency_score", 0.0)
)

t11_optimization_score = t11_safe_float(
    st.session_state.get("t10_result_optimization_score", 0.0)
)

t11_data_quality_score = t11_safe_float(
    st.session_state.get("t10_result_data_quality_score", 0.0)
)

t11_excess_fuel = t11_safe_float(
    st.session_state.get("t6_result_excess_period_fuel", 0.0)
)

t11_excess_cost = t11_safe_float(
    st.session_state.get("t6_result_excess_period_cost", 0.0)
)

t11_saving_opportunity = t11_safe_float(
    st.session_state.get("t9_result_saving_opportunity", 0.0)
)

t11_days_to_reserve = t11_safe_float(
    st.session_state.get("t8_result_days_to_reserve", 0.0)
)


# ------------------------------------------------------------
# SCORE NORMALIZATION
# ------------------------------------------------------------

def t11_normalize_score(value):
    value = t11_safe_float(value, 0.0)
    return max(0.0, min(100.0, value))


t11_efficiency_score = t11_normalize_score(t11_efficiency_score)
t11_optimization_score = t11_normalize_score(t11_optimization_score)
t11_data_quality_score = t11_normalize_score(t11_data_quality_score)


# ------------------------------------------------------------
# MANAGEMENT PERFORMANCE SCORE
# ------------------------------------------------------------

t11_management_score = (
    (t11_efficiency_score * 0.40)
    + (t11_optimization_score * 0.35)
    + (t11_data_quality_score * 0.25)
)

t11_management_score = round(
    t11_normalize_score(t11_management_score),
    1
)


# ------------------------------------------------------------
# PERFORMANCE CLASSIFICATION
# ------------------------------------------------------------

if t11_management_score >= 90:
    t11_performance_class = "EXCELLENT"
    t11_performance_icon = "🟢"

elif t11_management_score >= 80:
    t11_performance_class = "GOOD"
    t11_performance_icon = "🟢"

elif t11_management_score >= 70:
    t11_performance_class = "MONITOR"
    t11_performance_icon = "🟡"

elif t11_management_score >= 60:
    t11_performance_class = "ATTENTION"
    t11_performance_icon = "🟠"

else:
    t11_performance_class = "CRITICAL REVIEW"
    t11_performance_icon = "🔴"


# ------------------------------------------------------------
# MANAGEMENT KPI DASHBOARD
# ------------------------------------------------------------

st.subheader("📊 Fleet Performance Benchmark")

t11_c1, t11_c2, t11_c3, t11_c4 = st.columns(4)

with t11_c1:
    st.metric(
        "Management Score",
        f"{t11_management_score:.1f}/100"
    )

with t11_c2:
    st.metric(
        "Fuel Efficiency",
        f"{t11_efficiency_score:.1f}/100"
    )

with t11_c3:
    st.metric(
        "Optimization",
        f"{t11_optimization_score:.1f}/100"
    )

with t11_c4:
    st.metric(
        "Data Quality",
        f"{t11_data_quality_score:.1f}/100"
    )


st.subheader("🎯 Performance Classification")

if t11_performance_class in ["EXCELLENT", "GOOD"]:
    st.success(
        f"{t11_performance_icon} {t11_performance_class} — "
        "Vessel fuel-performance indicators are within the stronger "
        "management benchmark range."
    )

elif t11_performance_class == "MONITOR":
    st.warning(
        f"{t11_performance_icon} {t11_performance_class} — "
        "Performance remains acceptable for monitoring, but improvement "
        "opportunities should be reviewed."
    )

else:
    st.error(
        f"{t11_performance_icon} {t11_performance_class} — "
        "Performance indicators require management review and verification."
    )


# ------------------------------------------------------------
# COMMERCIAL & OPERATIONAL EXPOSURE
# ------------------------------------------------------------

st.subheader("💰 Operational & Commercial Exposure")

t11_e1, t11_e2, t11_e3, t11_e4 = st.columns(4)

with t11_e1:
    st.metric(
        "Excess Fuel",
        f"{t11_excess_fuel:,.2f}"
    )

with t11_e2:
    st.metric(
        "Excess Cost",
        f"{t11_excess_cost:,.2f}"
    )

with t11_e3:
    st.metric(
        "Saving Opportunity",
        f"{t11_saving_opportunity:,.2f}"
    )

with t11_e4:
    if t11_days_to_reserve > 0:
        st.metric(
            "Days to Reserve",
            f"{t11_days_to_reserve:.1f} days"
        )
    else:
        st.metric(
            "Days to Reserve",
            "N/A"
        )


# ------------------------------------------------------------
# BENCHMARK INTELLIGENCE
# ------------------------------------------------------------

st.subheader("🧠 Benchmark Intelligence")

t11_intelligence = []

if t11_efficiency_score >= 80:
    t11_intelligence.append(
        "Fuel-efficiency KPI is currently within the stronger internal "
        "performance range."
    )
else:
    t11_intelligence.append(
        "Fuel-efficiency KPI indicates potential for further operational "
        "performance improvement."
    )

if t11_optimization_score < 80:
    t11_intelligence.append(
        "Optimization potential remains and should be reviewed against "
        "speed, RPM/load, voyage requirements and machinery limitations."
    )

if t11_excess_fuel > 0:
    t11_intelligence.append(
        "Excess fuel consumption has been detected in the upstream "
        "performance intelligence results."
    )

if t11_excess_cost > 0:
    t11_intelligence.append(
        "Excess fuel consumption is producing a measurable financial impact."
    )

if t11_saving_opportunity > 0:
    t11_intelligence.append(
        "A fuel-cost saving opportunity has been identified by the "
        "optimization intelligence module."
    )

if t11_data_quality_score < 70:
    t11_intelligence.append(
        "Data quality should be improved before relying on the benchmark "
        "for higher-impact management decisions."
    )

if not t11_intelligence:
    t11_intelligence.append(
        "No significant benchmark exception is currently identified."
    )

for item in t11_intelligence:
    st.write(f"• {item}")


# ------------------------------------------------------------
# PRIORITY ACTIONS
# ------------------------------------------------------------

st.subheader("📋 Priority Actions")

t11_priority_actions = []

if t11_management_score < 70:
    t11_priority_actions.append(
        "Perform management review of fuel-efficiency, optimization and "
        "data-quality indicators."
    )

if t11_excess_fuel > 0:
    t11_priority_actions.append(
        "Investigate excess consumption against RPM/load, vessel speed, "
        "weather/current, draft/trim, hull condition and propeller condition."
    )

if t11_excess_cost > 0:
    t11_priority_actions.append(
        "Verify the commercial impact against actual bunker price, invoices "
        "and approved operating budget."
    )

if t11_data_quality_score < 80:
    t11_priority_actions.append(
        "Verify source data including fuel measurements, tank soundings, "
        "engine readings and voyage information."
    )

if not t11_priority_actions:
    t11_priority_actions.append(
        "Continue monitoring vessel performance against the approved "
        "operational and fuel-efficiency baseline."
    )

for number, action in enumerate(t11_priority_actions, start=1):
    st.write(f"{number}. {action}")


# ------------------------------------------------------------
# DATA QUALITY & VALIDATION
# ------------------------------------------------------------

st.subheader("🛡️ Data Quality & Validation")

t11_validation = []

if t11_data_quality_score <= 0:
    t11_validation.append(
        "Management data-quality score is zero or unavailable."
    )

if t11_efficiency_score <= 0:
    t11_validation.append(
        "Fuel-efficiency score is zero or unavailable."
    )

if t11_optimization_score <= 0:
    t11_validation.append(
        "Optimization score is zero or unavailable."
    )

if not t11_validation:
    st.success(
        "🟢 Fleet benchmark inputs passed the basic validation checks."
    )
else:
    for note in t11_validation:
        st.warning(f"🟠 {note}")


st.info(
    "Fleet benchmark results are decision-support estimates and are not a "
    "substitute for verified vessel measurements or approved company "
    "performance standards. Before technical, commercial or management "
    "action, verify actual fuel consumption, engine performance, vessel "
    "condition, voyage conditions, bunker records, financial data and "
    "applicable company procedures."
)


# ------------------------------------------------------------
# SAVE TAHAP 11 RESULTS
# ------------------------------------------------------------

st.session_state["t11_result_vessel"] = t11_selected_vessel
st.session_state["t11_result_management_score"] = t11_management_score
st.session_state["t11_result_performance_class"] = t11_performance_class
st.session_state["t11_result_efficiency_score"] = t11_efficiency_score
st.session_state["t11_result_optimization_score"] = t11_optimization_score
st.session_state["t11_result_data_quality_score"] = t11_data_quality_score
st.session_state["t11_result_excess_fuel"] = t11_excess_fuel
st.session_state["t11_result_excess_cost"] = t11_excess_cost
st.session_state["t11_result_saving_opportunity"] = t11_saving_opportunity
st.session_state["t11_result_intelligence"] = t11_intelligence
st.session_state["t11_result_priority_actions"] = t11_priority_actions


st.success(
    "✅ TAHAP 11 ACTIVE — Fleet Benchmark & Performance Ranking "
    "Intelligence is operational."
)

st.info(
    "TAHAP 11 results are stored in the application session and "
    "prepared for the next intelligence modules."
)


# ============================================================
# END TAHAP 11
# ============================================================

# ============================================================
# TAHAP 12 - FUEL ANOMALY DETECTION & EARLY WARNING INTELLIGENCE
# ============================================================

st.divider()
st.header("🚨 Fuel Anomaly Detection & Early Warning Intelligence")

st.caption(
    "Integrated early-warning analysis for abnormal fuel consumption, "
    "performance deviation, commercial exposure and management response."
)


# ------------------------------------------------------------
# VESSEL CONTEXT
# ------------------------------------------------------------

t12_selected_vessel = st.session_state.get(
    "t11_result_vessel",
    st.session_state.get(
        "selected_fleet_vessel",
        st.session_state.get(
            "sidebar_vessel_name",
            globals().get("vessel_name", "ASL MANTRUS")
        )
    )
)

st.subheader("🚢 Early Warning Vessel")
st.info(
    f"Fuel anomaly and early-warning analysis for: "
    f"**{t12_selected_vessel}**"
)


# ------------------------------------------------------------
# SAFE NUMBER FUNCTION
# ------------------------------------------------------------

def t12_safe_float(value, default=0.0):
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


# ------------------------------------------------------------
# COLLECT UPSTREAM INTELLIGENCE
# ------------------------------------------------------------

t12_management_score = t12_safe_float(
    st.session_state.get(
        "t11_result_management_score",
        0.0
    )
)

t12_efficiency_score = t12_safe_float(
    st.session_state.get(
        "t11_result_efficiency_score",
        0.0
    )
)

t12_optimization_score = t12_safe_float(
    st.session_state.get(
        "t11_result_optimization_score",
        0.0
    )
)

t12_data_quality_score = t12_safe_float(
    st.session_state.get(
        "t11_result_data_quality_score",
        0.0
    )
)

t12_excess_fuel = t12_safe_float(
    st.session_state.get(
        "t11_result_excess_fuel",
        0.0
    )
)

t12_excess_cost = t12_safe_float(
    st.session_state.get(
        "t11_result_excess_cost",
        0.0
    )
)

t12_saving_opportunity = t12_safe_float(
    st.session_state.get(
        "t11_result_saving_opportunity",
        0.0
    )
)

t12_days_to_reserve = t12_safe_float(
    st.session_state.get(
        "t8_result_days_to_reserve",
        0.0
    )
)


# ------------------------------------------------------------
# NORMALIZE SCORES
# ------------------------------------------------------------

def t12_normalize_score(value):
    value = t12_safe_float(value, 0.0)
    return max(0.0, min(100.0, value))


t12_management_score = t12_normalize_score(
    t12_management_score
)

t12_efficiency_score = t12_normalize_score(
    t12_efficiency_score
)

t12_optimization_score = t12_normalize_score(
    t12_optimization_score
)

t12_data_quality_score = t12_normalize_score(
    t12_data_quality_score
)


# ------------------------------------------------------------
# ANOMALY POINT SYSTEM
# ------------------------------------------------------------

t12_anomaly_points = 0
t12_anomaly_reasons = []


# Fuel efficiency
if t12_efficiency_score < 60:
    t12_anomaly_points += 30
    t12_anomaly_reasons.append(
        "Fuel-efficiency score is below 60."
    )

elif t12_efficiency_score < 75:
    t12_anomaly_points += 15
    t12_anomaly_reasons.append(
        "Fuel-efficiency score is below the preferred benchmark."
    )


# Optimization
if t12_optimization_score < 60:
    t12_anomaly_points += 20
    t12_anomaly_reasons.append(
        "Optimization score indicates significant improvement potential."
    )

elif t12_optimization_score < 75:
    t12_anomaly_points += 10
    t12_anomaly_reasons.append(
        "Optimization performance requires monitoring."
    )


# Management performance
if t12_management_score < 60:
    t12_anomaly_points += 20
    t12_anomaly_reasons.append(
        "Integrated management performance score requires review."
    )

elif t12_management_score < 75:
    t12_anomaly_points += 10
    t12_anomaly_reasons.append(
        "Integrated management performance is below the preferred range."
    )


# Excess fuel
if t12_excess_fuel > 0:
    t12_anomaly_points += 15
    t12_anomaly_reasons.append(
        "Upstream intelligence detected excess fuel consumption."
    )


# Excess cost
if t12_excess_cost > 0:
    t12_anomaly_points += 10
    t12_anomaly_reasons.append(
        "Fuel deviation is producing a measurable cost impact."
    )


# Data quality
if t12_data_quality_score < 60:
    t12_anomaly_points += 15
    t12_anomaly_reasons.append(
        "Low data quality reduces confidence in the analysis."
    )

elif t12_data_quality_score < 80:
    t12_anomaly_points += 5
    t12_anomaly_reasons.append(
        "Source data should be further verified."
    )


# Reserve exposure
if 0 < t12_days_to_reserve <= 2:
    t12_anomaly_points += 30
    t12_anomaly_reasons.append(
        "Fuel reserve threshold may be reached within two days."
    )

elif 2 < t12_days_to_reserve <= 5:
    t12_anomaly_points += 15
    t12_anomaly_reasons.append(
        "Fuel reserve threshold may be approached within five days."
    )


t12_anomaly_score = min(
    100.0,
    float(t12_anomaly_points)
)


# ------------------------------------------------------------
# ALERT LEVEL
# ------------------------------------------------------------

if t12_anomaly_score >= 70:
    t12_alert_level = "CRITICAL"
    t12_alert_icon = "🔴"

elif t12_anomaly_score >= 45:
    t12_alert_level = "HIGH"
    t12_alert_icon = "🟠"

elif t12_anomaly_score >= 20:
    t12_alert_level = "WATCH"
    t12_alert_icon = "🟡"

else:
    t12_alert_level = "NORMAL"
    t12_alert_icon = "🟢"


# ------------------------------------------------------------
# EARLY WARNING DASHBOARD
# ------------------------------------------------------------

st.subheader("📊 Early Warning Dashboard")

t12_c1, t12_c2, t12_c3, t12_c4 = st.columns(4)

with t12_c1:
    st.metric(
        "Anomaly Score",
        f"{t12_anomaly_score:.0f}/100"
    )

with t12_c2:
    st.metric(
        "Alert Level",
        t12_alert_level
    )

with t12_c3:
    st.metric(
        "Excess Fuel",
        f"{t12_excess_fuel:,.2f}"
    )

with t12_c4:
    st.metric(
        "Excess Cost",
        f"{t12_excess_cost:,.2f}"
    )


# ------------------------------------------------------------
# MANAGEMENT ALERT
# ------------------------------------------------------------

st.subheader("🚦 Management Alert")

if t12_alert_level == "CRITICAL":

    st.error(
        f"{t12_alert_icon} CRITICAL — Multiple fuel-performance "
        "risk indicators require prompt operational and management review."
    )

elif t12_alert_level == "HIGH":

    st.error(
        f"{t12_alert_icon} HIGH — Significant fuel-performance "
        "deviation or operational exposure has been detected."
    )

elif t12_alert_level == "WATCH":

    st.warning(
        f"{t12_alert_icon} WATCH — Fuel-performance indicators "
        "should be monitored and verified."
    )

else:

    st.success(
        f"{t12_alert_icon} NORMAL — No significant integrated "
        "fuel anomaly is currently detected."
    )


# ------------------------------------------------------------
# DETECTED ANOMALIES
# ------------------------------------------------------------

st.subheader("🔎 Detected Anomalies")

if t12_anomaly_reasons:

    for reason in t12_anomaly_reasons:
        st.write(f"• {reason}")

else:

    st.success(
        "No significant anomaly trigger is currently identified."
    )


# ------------------------------------------------------------
# POSSIBLE CONTRIBUTING FACTORS
# ------------------------------------------------------------

st.subheader("🧠 Possible Contributing Factors")

t12_possible_causes = []

if t12_excess_fuel > 0:

    t12_possible_causes.extend(
        [
            "RPM/load may be above the efficient operating range.",
            "Vessel speed may not match the approved economical profile.",
            "Weather or current may be increasing propulsion demand.",
            "Draft or trim condition may be increasing resistance.",
            "Hull or propeller condition may be affecting efficiency.",
            "Machinery performance may differ from the approved baseline."
        ]
    )

if t12_optimization_score < 75:

    t12_possible_causes.append(
        "Current operating strategy may have additional optimization potential."
    )

if t12_data_quality_score < 80:

    t12_possible_causes.append(
        "Measurement or source-data uncertainty may be affecting "
        "the calculated performance indicators."
    )

if not t12_possible_causes:

    t12_possible_causes.append(
        "No specific contributing factor is identified from the "
        "available upstream intelligence."
    )

for cause in t12_possible_causes:
    st.write(f"• {cause}")


# ------------------------------------------------------------
# SAVING OPPORTUNITY
# ------------------------------------------------------------

st.subheader("💰 Financial Opportunity")

t12_f1, t12_f2 = st.columns(2)

with t12_f1:

    st.metric(
        "Current Excess Cost",
        f"{t12_excess_cost:,.2f}"
    )

with t12_f2:

    st.metric(
        "Identified Saving Opportunity",
        f"{t12_saving_opportunity:,.2f}"
    )


# ------------------------------------------------------------
# PRIORITY ACTIONS
# ------------------------------------------------------------

st.subheader("📋 Priority Actions")

t12_priority_actions = []

if t12_alert_level in ["CRITICAL", "HIGH"]:

    t12_priority_actions.append(
        "Verify actual fuel ROB, tank soundings and daily consumption "
        "before taking operational or commercial action."
    )

if t12_excess_fuel > 0:

    t12_priority_actions.append(
        "Compare actual RPM/load and vessel speed against the approved "
        "fuel-performance baseline."
    )

    t12_priority_actions.append(
        "Review weather/current, draft/trim, hull condition, propeller "
        "condition and machinery performance."
    )

if t12_excess_cost > 0:

    t12_priority_actions.append(
        "Verify bunker price, invoices and operating budget to confirm "
        "the financial impact."
    )

if 0 < t12_days_to_reserve <= 5:

    t12_priority_actions.append(
        "Review voyage fuel requirement, reserve policy and bunker "
        "availability before the projected reserve threshold."
    )

if t12_data_quality_score < 80:

    t12_priority_actions.append(
        "Improve source-data verification before escalating the "
        "anomaly for management decision."
    )

if not t12_priority_actions:

    t12_priority_actions.append(
        "Continue monitoring actual fuel consumption against the "
        "approved vessel baseline."
    )

for number, action in enumerate(
    t12_priority_actions,
    start=1
):
    st.write(f"{number}. {action}")


# ------------------------------------------------------------
# DATA QUALITY & VALIDATION
# ------------------------------------------------------------

st.subheader("🛡️ Data Quality & Validation")

t12_validation = []

if t12_efficiency_score <= 0:
    t12_validation.append(
        "Fuel-efficiency score is zero or unavailable."
    )

if t12_optimization_score <= 0:
    t12_validation.append(
        "Optimization score is zero or unavailable."
    )

if t12_management_score <= 0:
    t12_validation.append(
        "Management performance score is zero or unavailable."
    )

if t12_data_quality_score <= 0:
    t12_validation.append(
        "Data-quality score is zero or unavailable."
    )


if not t12_validation:

    st.success(
        "🟢 Fuel anomaly detection inputs passed "
        "the basic validation checks."
    )

else:

    for note in t12_validation:
        st.warning(f"🟠 {note}")


st.info(
    "Fuel anomaly and early-warning results are decision-support estimates. "
    "An alert does not by itself establish the cause of abnormal consumption. "
    "Before operational, technical, safety or commercial action, verify "
    "actual fuel measurements, tank calibration, fuel density, machinery "
    "performance, RPM/load, vessel speed, draft/trim, weather/current, "
    "voyage requirements, reserve requirements and applicable company "
    "procedures."
)


# ------------------------------------------------------------
# SAVE TAHAP 12 RESULTS
# ------------------------------------------------------------

st.session_state["t12_result_vessel"] = (
    t12_selected_vessel
)

st.session_state["t12_result_anomaly_score"] = (
    t12_anomaly_score
)

st.session_state["t12_result_alert_level"] = (
    t12_alert_level
)

st.session_state["t12_result_excess_fuel"] = (
    t12_excess_fuel
)

st.session_state["t12_result_excess_cost"] = (
    t12_excess_cost
)

st.session_state["t12_result_saving_opportunity"] = (
    t12_saving_opportunity
)

st.session_state["t12_result_anomaly_reasons"] = (
    t12_anomaly_reasons
)

st.session_state["t12_result_possible_causes"] = (
    t12_possible_causes
)

st.session_state["t12_result_priority_actions"] = (
    t12_priority_actions
)


st.success(
    "✅ TAHAP 12 ACTIVE — Fuel Anomaly Detection & Early Warning "
    "Intelligence is operational."
)

st.info(
    "TAHAP 12 results are stored in the application session and "
    "prepared for the next intelligence modules."
)


# ============================================================
# END TAHAP 12
# ============================================================

# ============================================================
# TAHAP 13 - FUEL FORECASTING & PREDICTIVE CONSUMPTION INTELLIGENCE
# ============================================================

st.divider()
st.header("🔮 Fuel Forecasting & Predictive Consumption Intelligence")

st.caption(
    "Forward-looking fuel consumption, ROB, endurance and bunker requirement "
    "forecast using available vessel fuel-intelligence results."
)


# ------------------------------------------------------------
# VESSEL CONTEXT
# ------------------------------------------------------------

t13_selected_vessel = st.session_state.get(
    "t12_result_vessel",
    st.session_state.get(
        "t11_result_vessel",
        st.session_state.get(
            "selected_fleet_vessel",
            st.session_state.get(
                "sidebar_vessel_name",
                globals().get("vessel_name", "ASL MANTRUS")
            )
        )
    )
)

st.subheader("🚢 Forecast Vessel")
st.info(
    f"Predictive fuel analysis for: **{t13_selected_vessel}**"
)


# ------------------------------------------------------------
# SAFE NUMBER FUNCTION
# ------------------------------------------------------------

def t13_safe_float(value, default=0.0):
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


# ------------------------------------------------------------
# COLLECT UPSTREAM RESULTS
# ------------------------------------------------------------

t13_current_rob = t13_safe_float(
    st.session_state.get(
        "t4_result_rob_1",
        st.session_state.get("t4_result_projected_rob_1", 0.0)
    )
)

t13_daily_consumption = t13_safe_float(
    st.session_state.get(
        "t4_result_daily_consumption_1",
        0.0
    )
)

t13_reserve = t13_safe_float(
    st.session_state.get(
        "t4_result_reserve_1",
        0.0
    )
)

t13_projected_rob = t13_safe_float(
    st.session_state.get(
        "t4_result_projected_rob_1",
        t13_current_rob
    )
)

t13_voyage_requirement = t13_safe_float(
    st.session_state.get(
        "t5_result_total_required_1",
        0.0
    )
)

t13_excess_fuel = t13_safe_float(
    st.session_state.get(
        "t12_result_excess_fuel",
        0.0
    )
)

t13_excess_cost = t13_safe_float(
    st.session_state.get(
        "t12_result_excess_cost",
        0.0
    )
)

t13_saving_opportunity = t13_safe_float(
    st.session_state.get(
        "t12_result_saving_opportunity",
        0.0
    )
)

t13_anomaly_score = t13_safe_float(
    st.session_state.get(
        "t12_result_anomaly_score",
        0.0
    )
)

t13_alert_level = st.session_state.get(
    "t12_result_alert_level",
    "NORMAL"
)


# ------------------------------------------------------------
# FORECAST INPUT
# ------------------------------------------------------------

st.subheader("⚙️ Forecast Configuration")

t13_i1, t13_i2, t13_i3 = st.columns(3)

with t13_i1:
    t13_forecast_days = st.number_input(
        "Forecast Period (days)",
        min_value=1,
        max_value=90,
        value=7,
        step=1,
        key="t13_forecast_days"
    )

with t13_i2:
    t13_consumption_adjustment = st.number_input(
        "Consumption Adjustment (%)",
        min_value=-50.0,
        max_value=100.0,
        value=0.0,
        step=1.0,
        key="t13_consumption_adjustment"
    )

with t13_i3:
    t13_safety_margin_percent = st.number_input(
        "Planning Safety Margin (%)",
        min_value=0.0,
        max_value=50.0,
        value=10.0,
        step=1.0,
        key="t13_safety_margin_percent"
    )


# ------------------------------------------------------------
# BASE CONSUMPTION FALLBACK
# ------------------------------------------------------------

if t13_daily_consumption <= 0:

    t13_daily_consumption = t13_safe_float(
        st.session_state.get(
            "daily_fuel_ton",
            st.session_state.get(
                "daily_consumption",
                0.0
            )
        )
    )


# ------------------------------------------------------------
# ADJUSTED DAILY CONSUMPTION
# ------------------------------------------------------------

t13_adjustment_factor = (
    1.0 + (t13_consumption_adjustment / 100.0)
)

t13_adjusted_daily_consumption = max(
    0.0,
    t13_daily_consumption * t13_adjustment_factor
)


# ------------------------------------------------------------
# FORECAST CONSUMPTION
# ------------------------------------------------------------

t13_forecast_consumption = (
    t13_adjusted_daily_consumption
    * float(t13_forecast_days)
)

t13_safety_margin_fuel = (
    t13_forecast_consumption
    * (t13_safety_margin_percent / 100.0)
)

t13_total_forecast_requirement = (
    t13_forecast_consumption
    + t13_safety_margin_fuel
    + t13_reserve
)


# ------------------------------------------------------------
# PROJECTED ROB
# ------------------------------------------------------------

t13_forecast_rob = (
    t13_current_rob
    - t13_forecast_consumption
)

t13_usable_after_reserve = (
    t13_forecast_rob
    - t13_reserve
)


# ------------------------------------------------------------
# ENDURANCE
# ------------------------------------------------------------

if t13_adjusted_daily_consumption > 0:

    t13_endurance_days = (
        t13_current_rob
        / t13_adjusted_daily_consumption
    )

    t13_usable_endurance_days = (
        max(0.0, t13_current_rob - t13_reserve)
        / t13_adjusted_daily_consumption
    )

else:

    t13_endurance_days = 0.0
    t13_usable_endurance_days = 0.0


# ------------------------------------------------------------
# BUNKER REQUIREMENT
# ------------------------------------------------------------

t13_bunker_required = max(
    0.0,
    t13_total_forecast_requirement
    - t13_current_rob
)


# ------------------------------------------------------------
# FORECAST STATUS
# ------------------------------------------------------------

if t13_adjusted_daily_consumption <= 0:

    t13_forecast_status = "DATA REQUIRED"
    t13_status_icon = "⚪"

elif t13_forecast_rob < 0:

    t13_forecast_status = "CRITICAL"
    t13_status_icon = "🔴"

elif t13_forecast_rob < t13_reserve:

    t13_forecast_status = "RESERVE RISK"
    t13_status_icon = "🟠"

elif t13_bunker_required > 0:

    t13_forecast_status = "BUNKER REVIEW"
    t13_status_icon = "🟡"

else:

    t13_forecast_status = "SUFFICIENT"
    t13_status_icon = "🟢"


# ------------------------------------------------------------
# FORECAST DASHBOARD
# ------------------------------------------------------------

st.subheader("📊 Predictive Fuel Forecast")

t13_c1, t13_c2, t13_c3, t13_c4 = st.columns(4)

with t13_c1:
    st.metric(
        "Current ROB",
        f"{t13_current_rob:,.2f}"
    )

with t13_c2:
    st.metric(
        "Adjusted Daily Fuel",
        f"{t13_adjusted_daily_consumption:,.2f}"
    )

with t13_c3:
    st.metric(
        f"{t13_forecast_days}-Day Consumption",
        f"{t13_forecast_consumption:,.2f}"
    )

with t13_c4:
    st.metric(
        "Forecast ROB",
        f"{t13_forecast_rob:,.2f}"
    )


t13_c5, t13_c6, t13_c7, t13_c8 = st.columns(4)

with t13_c5:
    st.metric(
        "Reserve",
        f"{t13_reserve:,.2f}"
    )

with t13_c6:
    st.metric(
        "Usable Endurance",
        f"{t13_usable_endurance_days:,.1f} days"
    )

with t13_c7:
    st.metric(
        "Bunker Required",
        f"{t13_bunker_required:,.2f}"
    )

with t13_c8:
    st.metric(
        "Forecast Status",
        t13_forecast_status
    )


# ------------------------------------------------------------
# FORECAST ALERT
# ------------------------------------------------------------

st.subheader("🚦 Predictive Status")

if t13_forecast_status == "CRITICAL":

    st.error(
        f"{t13_status_icon} CRITICAL — Forecast consumption exceeds "
        "the available fuel quantity within the selected forecast period."
    )

elif t13_forecast_status == "RESERVE RISK":

    st.error(
        f"{t13_status_icon} RESERVE RISK — Forecast ROB falls below "
        "the configured reserve quantity."
    )

elif t13_forecast_status == "BUNKER REVIEW":

    st.warning(
        f"{t13_status_icon} BUNKER REVIEW — Additional fuel may be "
        "required to satisfy forecast consumption, reserve and planning margin."
    )

elif t13_forecast_status == "DATA REQUIRED":

    st.warning(
        f"{t13_status_icon} DATA REQUIRED — Daily fuel consumption "
        "is zero or unavailable. Verify the upstream fuel data."
    )

else:

    st.success(
        f"{t13_status_icon} SUFFICIENT — Available fuel is sufficient "
        "for the selected forecast period under the current assumptions."
    )


# ------------------------------------------------------------
# FORECAST TABLE
# ------------------------------------------------------------

st.subheader("📋 Forecast Summary")

t13_forecast_summary = {
    "Parameter": [
        "Forecast Period",
        "Current ROB",
        "Base Daily Consumption",
        "Adjusted Daily Consumption",
        "Forecast Consumption",
        "Planning Safety Margin",
        "Reserve Fuel",
        "Total Forecast Requirement",
        "Forecast ROB",
        "Usable Fuel After Reserve",
        "Total Endurance",
        "Usable Endurance",
        "Bunker Requirement",
        "Upstream Anomaly Score",
        "Upstream Alert Level"
    ],
    "Value": [
        f"{t13_forecast_days} days",
        f"{t13_current_rob:,.2f}",
        f"{t13_daily_consumption:,.2f}",
        f"{t13_adjusted_daily_consumption:,.2f}",
        f"{t13_forecast_consumption:,.2f}",
        f"{t13_safety_margin_fuel:,.2f}",
        f"{t13_reserve:,.2f}",
        f"{t13_total_forecast_requirement:,.2f}",
        f"{t13_forecast_rob:,.2f}",
        f"{t13_usable_after_reserve:,.2f}",
        f"{t13_endurance_days:,.1f} days",
        f"{t13_usable_endurance_days:,.1f} days",
        f"{t13_bunker_required:,.2f}",
        f"{t13_anomaly_score:.0f}/100",
        str(t13_alert_level)
    ]
}

st.table(t13_forecast_summary)


# ------------------------------------------------------------
# PREDICTIVE INTELLIGENCE
# ------------------------------------------------------------

st.subheader("🧠 Predictive Intelligence")

t13_intelligence = []

if t13_adjusted_daily_consumption <= 0:

    t13_intelligence.append(
        "A reliable fuel forecast cannot be calculated until a valid "
        "daily consumption value is available."
    )

else:

    t13_intelligence.append(
        f"At the current adjusted consumption rate, estimated usable "
        f"endurance is approximately {t13_usable_endurance_days:.1f} days."
    )

if t13_forecast_rob < t13_reserve:

    t13_intelligence.append(
        "Projected ROB enters or passes the configured reserve level "
        "within the selected forecast horizon."
    )

if t13_bunker_required > 0:

    t13_intelligence.append(
        f"Estimated additional bunker requirement is approximately "
        f"{t13_bunker_required:,.2f} fuel units under the current assumptions."
    )

if t13_anomaly_score >= 45:

    t13_intelligence.append(
        "The upstream anomaly score is elevated; consumption forecasting "
        "should therefore be verified against actual vessel measurements."
    )

if t13_excess_fuel > 0:

    t13_intelligence.append(
        "Existing excess consumption may reduce endurance if it continues."
    )

if t13_saving_opportunity > 0:

    t13_intelligence.append(
        "Upstream optimization intelligence has identified a saving "
        "opportunity that may improve the forecast if operationally achievable."
    )

if not t13_intelligence:

    t13_intelligence.append(
        "No significant predictive fuel exception is currently identified."
    )

for item in t13_intelligence:
    st.write(f"• {item}")


# ------------------------------------------------------------
# PRIORITY ACTIONS
# ------------------------------------------------------------

st.subheader("📋 Priority Actions")

t13_priority_actions = []

if t13_adjusted_daily_consumption <= 0:

    t13_priority_actions.append(
        "Verify daily fuel consumption before using the predictive forecast."
    )

if t13_forecast_status in [
    "CRITICAL",
    "RESERVE RISK",
    "BUNKER REVIEW"
]:

    t13_priority_actions.append(
        "Verify actual ROB using approved tank sounding and calibration data."
    )

    t13_priority_actions.append(
        "Confirm remaining voyage distance, expected duration, weather/current "
        "and machinery consumption before final bunker planning."
    )

if t13_bunker_required > 0:

    t13_priority_actions.append(
        "Review bunker quantity, supplier availability, delivery location "
        "and applicable reserve requirements."
    )

if t13_anomaly_score >= 45:

    t13_priority_actions.append(
        "Investigate the upstream fuel anomaly before relying on the "
        "forecast for commercial or operational decisions."
    )

if not t13_priority_actions:

    t13_priority_actions.append(
        "Continue monitoring ROB and actual daily consumption against "
        "the predictive fuel forecast."
    )

for number, action in enumerate(
    t13_priority_actions,
    start=1
):
    st.write(f"{number}. {action}")


# ------------------------------------------------------------
# DATA QUALITY & VALIDATION
# ------------------------------------------------------------

st.subheader("🛡️ Data Quality & Validation")

t13_validation = []

if t13_current_rob <= 0:
    t13_validation.append(
        "Current ROB is zero or unavailable."
    )

if t13_daily_consumption <= 0:
    t13_validation.append(
        "Daily fuel consumption is zero or unavailable."
    )

if t13_reserve < 0:
    t13_validation.append(
        "Reserve fuel cannot be negative."
    )


if not t13_validation:

    st.success(
        "🟢 Fuel forecasting inputs passed the basic validation checks."
    )

else:

    for note in t13_validation:
        st.warning(f"🟠 {note}")


st.info(
    "Predictive fuel figures are planning estimates, not guaranteed future "
    "consumption. Actual results can differ because of RPM/load, vessel speed, "
    "draft/trim, loading or towing condition, weather/current, hull and "
    "propeller condition, machinery condition and voyage changes. Verify "
    "measured ROB, tank calibration, fuel density, actual consumption, voyage "
    "requirements and statutory/company reserves before operational or "
    "commercial decisions."
)


# ------------------------------------------------------------
# SAVE TAHAP 13 RESULTS
# ------------------------------------------------------------

st.session_state["t13_result_vessel"] = (
    t13_selected_vessel
)

st.session_state["t13_result_forecast_days"] = (
    t13_forecast_days
)

st.session_state["t13_result_adjusted_daily_consumption"] = (
    t13_adjusted_daily_consumption
)

st.session_state["t13_result_forecast_consumption"] = (
    t13_forecast_consumption
)

st.session_state["t13_result_forecast_rob"] = (
    t13_forecast_rob
)

st.session_state["t13_result_endurance_days"] = (
    t13_endurance_days
)

st.session_state["t13_result_usable_endurance_days"] = (
    t13_usable_endurance_days
)

st.session_state["t13_result_bunker_required"] = (
    t13_bunker_required
)

st.session_state["t13_result_forecast_status"] = (
    t13_forecast_status
)

st.session_state["t13_result_intelligence"] = (
    t13_intelligence
)

st.session_state["t13_result_priority_actions"] = (
    t13_priority_actions
)


st.success(
    "✅ TAHAP 13 ACTIVE — Fuel Forecasting & Predictive Consumption "
    "Intelligence is operational."
)

st.info(
    "TAHAP 13 results are stored in the application session and "
    "prepared for the next intelligence modules."
)


# ============================================================
# END TAHAP 13
# ============================================================

# ================================================================
# TAHAP 14 - BUNKER PLANNING & PROCUREMENT INTELLIGENCE
# ================================================================

st.divider()
st.header("⛽ Bunker Planning & Procurement Intelligence")

st.caption(
    "Bunker requirement, procurement planning, reserve protection, "
    "estimated purchasing cost and bunker decision support."
)

# ------------------------------------------------
# VESSEL CONTEXT
# ------------------------------------------------

t14_selected_vessel = st.session_state.get(
    "selected_fleet_vessel",
    st.session_state.get(
        "sidebar_vessel_name",
        globals().get("vessel_name", "ASL MANTRUS")
    )
)

st.subheader("🚢 Bunker Planning Vessel")
st.info(f"Bunker planning analysis for: **{t14_selected_vessel}**")


# ------------------------------------------------
# SAFE DATA FROM PREVIOUS STAGES
# ------------------------------------------------

def t14_safe_float(value, default=0.0):
    try:
        if value is None:
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


t14_current_rob = t14_safe_float(
    st.session_state.get(
        "t13_result_current_rob",
        st.session_state.get(
            "t8_result_current_rob",
            st.session_state.get("t4_result_projected_rob_l", 0.0)
        )
    )
)

t14_daily_consumption = t14_safe_float(
    st.session_state.get(
        "t13_result_daily_consumption",
        st.session_state.get(
            "t6_result_actual_daily_fuel",
            st.session_state.get("daily_fuel", 0.0)
        )
    )
)

t14_forecast_consumption = t14_safe_float(
    st.session_state.get(
        "t13_result_forecast_consumption",
        t14_daily_consumption
    )
)


# ------------------------------------------------
# BUNKER PLANNING INPUT
# ------------------------------------------------

st.subheader("📝 Bunker Procurement Data")

t14_c1, t14_c2, t14_c3 = st.columns(3)

with t14_c1:

    t14_required_days = st.number_input(
        "Required Operating Days",
        min_value=0.0,
        value=10.0,
        step=1.0,
        key="t14_required_days"
    )

    t14_safety_days = st.number_input(
        "Safety Reserve (Days)",
        min_value=0.0,
        value=3.0,
        step=0.5,
        key="t14_safety_days"
    )


with t14_c2:

    t14_manual_daily_consumption = st.number_input(
        "Planning Daily Fuel Consumption",
        min_value=0.0,
        value=float(max(t14_forecast_consumption, 0.0)),
        step=0.1,
        key="t14_manual_daily_consumption"
    )

    t14_manual_rob = st.number_input(
        "Current ROB for Planning",
        min_value=0.0,
        value=float(max(t14_current_rob, 0.0)),
        step=1.0,
        key="t14_manual_rob"
    )


with t14_c3:

    t14_bunker_price = st.number_input(
        "Estimated Bunker Price / Unit",
        min_value=0.0,
        value=650.0,
        step=10.0,
        key="t14_bunker_price"
    )

    t14_extra_margin_percent = st.number_input(
        "Procurement Margin (%)",
        min_value=0.0,
        max_value=100.0,
        value=5.0,
        step=1.0,
        key="t14_extra_margin_percent"
    )


# ------------------------------------------------
# CALCULATIONS
# ------------------------------------------------

t14_total_required_days = (
    t14_required_days + t14_safety_days
)

t14_base_requirement = (
    t14_manual_daily_consumption *
    t14_total_required_days
)

t14_margin_fuel = (
    t14_base_requirement *
    t14_extra_margin_percent / 100.0
)

t14_total_requirement = (
    t14_base_requirement +
    t14_margin_fuel
)

t14_bunker_required = max(
    t14_total_requirement -
    t14_manual_rob,
    0.0
)

t14_estimated_cost = (
    t14_bunker_required *
    t14_bunker_price
)

if t14_manual_daily_consumption > 0:
    t14_current_endurance = (
        t14_manual_rob /
        t14_manual_daily_consumption
    )
else:
    t14_current_endurance = 0.0


# ------------------------------------------------
# BUNKER REQUIREMENT DASHBOARD
# ------------------------------------------------

st.subheader("📊 Bunker Requirement Dashboard")

t14_m1, t14_m2, t14_m3, t14_m4 = st.columns(4)

t14_m1.metric(
    "Current ROB",
    f"{t14_manual_rob:,.2f}"
)

t14_m2.metric(
    "Current Endurance",
    f"{t14_current_endurance:,.1f} days"
)

t14_m3.metric(
    "Total Fuel Requirement",
    f"{t14_total_requirement:,.2f}"
)

t14_m4.metric(
    "Bunker Required",
    f"{t14_bunker_required:,.2f}"
)


t14_m5, t14_m6, t14_m7 = st.columns(3)

t14_m5.metric(
    "Operating Requirement",
    f"{t14_base_requirement:,.2f}"
)

t14_m6.metric(
    "Procurement Margin",
    f"{t14_margin_fuel:,.2f}"
)

t14_m7.metric(
    "Estimated Procurement Cost",
    f"${t14_estimated_cost:,.2f}"
)


# ------------------------------------------------
# PROCUREMENT STATUS
# ------------------------------------------------

st.subheader("🚦 Procurement Status")

if t14_manual_daily_consumption <= 0:

    t14_status = "DATA REQUIRED"

    st.warning(
        "Daily fuel consumption is zero or unavailable. "
        "Enter verified planning consumption before bunker approval."
    )

elif t14_manual_rob <= 0:

    t14_status = "ROB REQUIRED"

    st.warning(
        "Current ROB is zero or unavailable. "
        "Enter verified measured ROB before bunker procurement."
    )

elif t14_bunker_required <= 0:

    t14_status = "SUFFICIENT ROB"

    st.success(
        "Current ROB is sufficient for the entered operating period, "
        "reserve and procurement margin."
    )

elif t14_current_endurance < t14_safety_days:

    t14_status = "CRITICAL"

    st.error(
        "Current fuel endurance is below the entered safety reserve. "
        "Immediate bunker planning and operational verification are required."
    )

else:

    t14_status = "BUNKER REQUIRED"

    st.warning(
        "Additional bunker is required to meet the entered operating "
        "requirement, safety reserve and procurement margin."
    )


# ------------------------------------------------
# PROCUREMENT INTELLIGENCE
# ------------------------------------------------

st.subheader("🧠 Procurement Intelligence")

t14_intelligence = []

if t14_manual_daily_consumption <= 0:
    t14_intelligence.append(
        "Verified daily fuel consumption is required before calculating "
        "the final bunker quantity."
    )

if t14_manual_rob <= 0:
    t14_intelligence.append(
        "Verified current ROB is required before procurement approval."
    )

if t14_bunker_required > 0:
    t14_intelligence.append(
        f"Indicative additional bunker requirement is "
        f"{t14_bunker_required:,.2f} fuel units."
    )

if t14_estimated_cost > 0:
    t14_intelligence.append(
        f"Indicative procurement cost is "
        f"${t14_estimated_cost:,.2f} at the entered bunker price."
    )

if (
    t14_manual_daily_consumption > 0 and
    t14_bunker_required <= 0
):
    t14_intelligence.append(
        "Entered ROB currently covers the calculated operating requirement, "
        "reserve and procurement margin."
    )

if not t14_intelligence:
    t14_intelligence.append(
        "Enter verified ROB and consumption data to generate bunker "
        "procurement intelligence."
    )

for item in t14_intelligence:
    st.write(f"• {item}")


# ------------------------------------------------
# PRIORITY ACTIONS
# ------------------------------------------------

st.subheader("📋 Priority Actions")

t14_priority_actions = []

if t14_manual_rob <= 0:
    t14_priority_actions.append(
        "Verify actual ROB using approved tank sounding and calibration data."
    )

if t14_manual_daily_consumption <= 0:
    t14_priority_actions.append(
        "Verify actual daily fuel consumption and machinery operating profile."
    )

if t14_bunker_required > 0:
    t14_priority_actions.append(
        "Confirm bunker availability, supplier quotation, delivery location "
        "and required delivery quantity."
    )

if t14_estimated_cost > 0:
    t14_priority_actions.append(
        "Verify bunker price, currency, taxes, port charges, supplier terms "
        "and approved operating budget."
    )

if not t14_priority_actions:
    t14_priority_actions.append(
        "Continue monitoring ROB and consumption against voyage requirements."
    )

for idx, action in enumerate(t14_priority_actions, start=1):
    st.write(f"{idx}. {action}")


# ------------------------------------------------
# DATA QUALITY & VALIDATION
# ------------------------------------------------

st.subheader("🛡️ Data Quality & Validation")

t14_validation = []

if t14_manual_rob <= 0:
    t14_validation.append(
        "Current ROB is zero or unavailable."
    )

if t14_manual_daily_consumption <= 0:
    t14_validation.append(
        "Daily fuel consumption is zero or unavailable."
    )

if t14_bunker_price <= 0:
    t14_validation.append(
        "Bunker price is zero or unavailable."
    )

if not t14_validation:

    st.success(
        "🟢 Bunker planning inputs passed the basic validation checks."
    )

else:

    for note in t14_validation:
        st.warning(f"🟠 {note}")


st.info(
    "Bunker planning and procurement figures are decision-support estimates. "
    "Before purchasing fuel or making operational, commercial or voyage "
    "decisions, verify actual tank soundings, calibration tables, fuel "
    "density, measured ROB, machinery consumption, voyage requirements, "
    "weather/current, statutory/company reserves, bunker specifications, "
    "supplier quotations, port restrictions and applicable company procedures."
)


# ------------------------------------------------
# SAVE TAHAP 14 RESULTS
# ------------------------------------------------

st.session_state["t14_result_status"] = t14_status
st.session_state["t14_result_current_rob"] = t14_manual_rob
st.session_state["t14_result_daily_consumption"] = (
    t14_manual_daily_consumption
)
st.session_state["t14_result_current_endurance"] = (
    t14_current_endurance
)
st.session_state["t14_result_total_requirement"] = (
    t14_total_requirement
)
st.session_state["t14_result_bunker_required"] = (
    t14_bunker_required
)
st.session_state["t14_result_estimated_cost"] = (
    t14_estimated_cost
)
st.session_state["t14_result_priority_actions"] = (
    t14_priority_actions
)
st.session_state["t14_result_intelligence"] = (
    t14_intelligence
)


st.success(
    "✅ TAHAP 14 ACTIVE — Bunker Planning & Procurement "
    "Intelligence is operational."
)

st.info(
    "TAHAP 14 results are stored in the application session "
    "and prepared for the next intelligence modules."
)


# ================================================================
# END TAHAP 14
# ================================================================
