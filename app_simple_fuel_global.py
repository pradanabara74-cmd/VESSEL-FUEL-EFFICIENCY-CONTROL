import io
import re
from datetime import date

import pandas as pd
import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Vessel Fuel Efficiency & Control Intelligence Center",
    page_icon="⚓",
    layout="wide",
)


# ============================================================
# SYSTEM CONFIG
# ============================================================

APP_TITLE = "VESSEL FUEL EFFICIENCY & CONTROL INTELLIGENCE CENTER"

RPM_POINTS = [
    600, 700, 800, 900, 1000, 1100, 1200, 1230, 1300
]

OPERATING_MODES = [
    "Free Sailing",
    "Towing",
    "Standby",
    "Maneuvering",
    "In Port",
    "Anchorage",
    "Other",
]

MASTER_COLUMNS = [
    "Date",
    "Vessel",
    "Operating Mode",
    "RPM",
    "Main Engines Running",
    "Running Hours",
    "Opening ROB MT",
    "Bunker Received MT",
    "Closing ROB MT",
    "Actual Consumption MT",
    "Distance NM",
    "Average Speed Knots",
    "Remarks",
]


# ============================================================
# SESSION STATE
# ============================================================

if "dpr_master" not in st.session_state:
    st.session_state.dpr_master = pd.DataFrame(columns=MASTER_COLUMNS)

if "selected_dpr_index" not in st.session_state:
    st.session_state.selected_dpr_index = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_vessel_name(value):
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def to_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def normalize_dataframe(df):
    """
    DPR MASTER DATA ENGINE
    Normalizes imported CSV into the application's 13 master fields.
    Missing data remains missing. No operational value is invented.
    """

    df = df.copy()

    # Remove accidental CSV index columns
    for col in list(df.columns):
        if str(col).lower().startswith("unnamed"):
            df = df.drop(columns=[col])

    if "index" in df.columns:
        df = df.drop(columns=["index"])

    missing = [col for col in MASTER_COLUMNS if col not in df.columns]

    if missing:
        raise ValueError(
            "Kolom DPR belum sesuai DPR MASTER DATA ENGINE.\n\n"
            "Kolom yang belum tersedia:\n- "
            + "\n- ".join(missing)
        )

    df = df[MASTER_COLUMNS].copy()

    df["Vessel"] = df["Vessel"].apply(clean_vessel_name)

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    ).dt.date

    numeric_columns = [
        "Main Engines Running",
        "Running Hours",
        "Opening ROB MT",
        "Bunker Received MT",
        "Closing ROB MT",
        "Actual Consumption MT",
        "Distance NM",
        "Average Speed Knots",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def rpm_numbers(value):
    """
    Reads both single RPM and mixed RPM strings:
    1300
    1300 & 800
    900 & 1000
    """

    if pd.isna(value):
        return []

    values = re.findall(r"\d+(?:\.\d+)?", str(value))

    result = []

    for item in values:
        try:
            result.append(float(item))
        except ValueError:
            pass

    return result


def rpm_matches(value, target):
    numbers = rpm_numbers(value)

    return any(
        abs(number - float(target)) < 0.001
        for number in numbers
    )


def safe_mean(series):
    values = pd.to_numeric(series, errors="coerce").dropna()

    if len(values) == 0:
        return None

    return float(values.mean())


def display_value(value, decimals=3, suffix=""):
    if pd.isna(value):
        return "NO DATA"

    try:
        return f"{float(value):,.{decimals}f}{suffix}"
    except Exception:
        return str(value)


def append_master_data(new_df):
    combined = pd.concat(
        [
            st.session_state.dpr_master,
            new_df
        ],
        ignore_index=True
    )

    # Prevent duplicate DPR rows
    combined = combined.drop_duplicates(
        subset=[
            "Date",
            "Vessel",
            "Operating Mode",
            "RPM",
            "Main Engines Running",
            "Actual Consumption MT",
        ],
        keep="last"
    )

    combined = combined.sort_values(
        by=["Vessel", "Date"],
        na_position="last"
    ).reset_index(drop=True)

    st.session_state.dpr_master = combined


# ============================================================
# HEADER
# ============================================================

st.title("⚓ " + APP_TITLE)

st.caption(
    "DPR MASTER DATA ENGINE — File DPR adalah sumber utama "
    "Daily Report KKM, Fuel Intelligence, Check/Action dan Historical Reports."
)

st.info(
    "🔐 MASTER RULE: Data operasional berasal dari DPR. "
    "Data yang tidak tersedia tidak akan dibuat atau diasumsikan oleh sistem."
)


# ============================================================
# SIDEBAR — GLOBAL VESSEL
# ============================================================

st.sidebar.header("⚓ Vessel Control")

vessel = st.sidebar.text_input(
    "Kapal / Vessel",
    placeholder="Ketik nama kapal...",
).strip().upper()

operating_mode = st.sidebar.selectbox(
    "Operating Mode",
    OPERATING_MODES,
)

st.sidebar.caption(
    "Nama kapal bebas. Aplikasi tidak dibatasi daftar kapal tertentu."
)


# ============================================================
# 1. DPR MASTER DATA ENGINE
# ============================================================

st.header("1. 📥 DPR MASTER DATA ENGINE")

st.write(
    "Upload file DPR yang telah dikonversi ke format CSV DPR Master. "
    "Satu file dapat berisi satu hari atau historical DPR."
)

uploaded_dpr = st.file_uploader(
    "Upload DPR / Daily Progress Report (CSV)",
    type=["csv"],
    key="master_dpr_upload",
)

if uploaded_dpr is not None:

    try:
        raw_df = pd.read_csv(uploaded_dpr)

        normalized_df = normalize_dataframe(raw_df)

        st.success(
            f"File DPR berhasil dibaca: "
            f"{len(normalized_df)} record."
        )

        st.dataframe(
            normalized_df,
            use_container_width=True,
            hide_index=True,
        )

        if st.button(
            "IMPORT KE DPR MASTER DATABASE",
            type="primary",
            use_container_width=True,
        ):
            append_master_data(normalized_df)

            st.success(
                f"{len(normalized_df)} DPR berhasil diproses "
                "ke DPR MASTER DATA ENGINE."
            )

            st.rerun()

    except Exception as e:
        st.error(str(e))


# ============================================================
# MASTER DATABASE STATUS
# ============================================================

master = st.session_state.dpr_master.copy()

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "DPR Records",
    len(master)
)

if master.empty:
    c2.metric("Vessels", 0)
    c3.metric("Fuel Records", 0)
    c4.metric("Latest DPR", "NO DATA")

else:

    vessel_count = (
        master["Vessel"]
        .replace("", pd.NA)
        .dropna()
        .nunique()
    )

    fuel_records = (
        pd.to_numeric(
            master["Actual Consumption MT"],
            errors="coerce"
        )
        .notna()
        .sum()
    )

    valid_dates = pd.to_datetime(
        master["Date"],
        errors="coerce"
    ).dropna()

    latest_date = (
        valid_dates.max().date().isoformat()
        if len(valid_dates)
        else "NO DATA"
    )

    c2.metric("Vessels", vessel_count)
    c3.metric("Fuel Records", int(fuel_records))
    c4.metric("Latest DPR", latest_date)


# ============================================================
# SELECT VESSEL DATA
# ============================================================

if vessel:

    vessel_history = master[
        master["Vessel"].astype(str).str.upper() == vessel
    ].copy()

else:
    vessel_history = pd.DataFrame(columns=MASTER_COLUMNS)


# ============================================================
# 2. DAILY REPORT KKM
# ============================================================

st.divider()
st.header("2. 🧾 Daily Report KKM")

st.caption(
    "Daily Report KKM dapat dibaca dari DPR Master atau "
    "dimasukkan manual apabila DPR hari tersebut belum tersedia."
)


# ------------------------------------------------------------
# DPR AUTO SELECT
# ------------------------------------------------------------

if not vessel_history.empty:

    available_dates = (
        pd.to_datetime(
            vessel_history["Date"],
            errors="coerce"
        )
        .dropna()
        .dt.date
        .sort_values(ascending=False)
        .unique()
        .tolist()
    )

else:
    available_dates = []


source_mode = st.radio(
    "Sumber Daily Report",
    [
        "DPR MASTER DATABASE",
        "INPUT MANUAL"
    ],
    horizontal=True,
)


selected_record = None


if source_mode == "DPR MASTER DATABASE":

    if not vessel:
        st.warning(
            "Ketik nama kapal pada sidebar."
        )

    elif vessel_history.empty:
        st.warning(
            f"Belum ada DPR MASTER DATABASE untuk {vessel}."
        )

    elif not available_dates:
        st.warning(
            "Tanggal DPR tidak tersedia."
        )

    else:

        selected_date = st.selectbox(
            "Pilih tanggal DPR",
            available_dates,
        )

        day_records = vessel_history[
            pd.to_datetime(
                vessel_history["Date"],
                errors="coerce"
            ).dt.date == selected_date
        ].copy()

        if not day_records.empty:
            selected_record = day_records.iloc[-1]


# ============================================================
# INPUT / DISPLAY DAILY REPORT
# ============================================================

if selected_record is not None:

    report_date = selected_record["Date"]
    report_vessel = selected_record["Vessel"]
    report_mode = selected_record["Operating Mode"]
    report_rpm = selected_record["RPM"]
    report_engines = selected_record["Main Engines Running"]
    report_hours = selected_record["Running Hours"]
    opening_rob = selected_record["Opening ROB MT"]
    bunker_received = selected_record["Bunker Received MT"]
    closing_rob = selected_record["Closing ROB MT"]
    actual_fuel = selected_record["Actual Consumption MT"]
    distance_nm = selected_record["Distance NM"]
    avg_speed = selected_record["Average Speed Knots"]
    remarks = selected_record["Remarks"]

    st.success(
        "Daily Report KKM terhubung langsung dengan DPR MASTER DATABASE."
    )

else:

    report_date = st.date_input(
        "Tanggal",
        value=date.today()
    )

    report_vessel = vessel

    report_mode = operating_mode

    a1, a2, a3 = st.columns(3)

    report_rpm = a1.text_input(
        "RPM",
        placeholder="Contoh: 1300 atau 1300 & 800"
    )

    report_engines = a2.selectbox(
        "Main Engine Running",
        [0, 1, 2]
    )

    report_hours = a3.number_input(
        "Running Hours",
        min_value=0.0,
        max_value=24.0,
        value=24.0,
        step=0.5,
    )

    b1, b2, b3 = st.columns(3)

    opening_rob = b1.number_input(
        "Opening ROB (MT)",
        min_value=0.0,
        value=0.0,
        step=0.001,
        format="%.3f",
    )

    bunker_received = b2.number_input(
        "Bunker Received (MT)",
        min_value=0.0,
        value=0.0,
        step=0.001,
        format="%.3f",
    )

    closing_rob = b3.number_input(
        "Closing ROB (MT)",
        min_value=0.0,
        value=0.0,
        step=0.001,
        format="%.3f",
    )

    actual_fuel = max(
        float(opening_rob)
        + float(bunker_received)
        - float(closing_rob),
        0.0
    )

    c1, c2 = st.columns(2)

    distance_nm = c1.number_input(
        "Distance (NM)",
        min_value=0.0,
        value=0.0,
        step=1.0,
    )

    avg_speed = c2.number_input(
        "Average Speed (Knots)",
        min_value=0.0,
        value=0.0,
        step=0.1,
    )

    remarks = st.text_area(
        "Remarks",
        placeholder="Catatan dari DPR / KKM..."
    )

    if st.button(
        "SAVE DAILY REPORT TO DPR MASTER",
        type="primary",
        use_container_width=True,
    ):

        if not report_vessel:
            st.error(
                "Nama kapal wajib diisi."
            )

        else:

            manual_row = pd.DataFrame(
                [{
                    "Date": report_date,
                    "Vessel": report_vessel,
                    "Operating Mode": report_mode,
                    "RPM": report_rpm,
                    "Main Engines Running": report_engines,
                    "Running Hours": report_hours,
                    "Opening ROB MT": opening_rob,
                    "Bunker Received MT": bunker_received,
                    "Closing ROB MT": closing_rob,
                    "Actual Consumption MT": actual_fuel,
                    "Distance NM": distance_nm,
                    "Average Speed Knots": avg_speed,
                    "Remarks": remarks,
                }]
            )

            append_master_data(
                normalize_dataframe(manual_row)
            )

            st.success(
                "Daily Report berhasil disimpan ke DPR MASTER DATABASE."
            )

            st.rerun()


# ============================================================
# 3. HASIL HARI INI
# ============================================================

st.divider()
st.header("3. 📊 HASIL HARI INI")

if selected_record is None and source_mode == "DPR MASTER DATABASE":

    st.info(
        "Pilih kapal dan tanggal DPR untuk menampilkan hasil."
    )

else:

    h1, h2, h3, h4 = st.columns(4)

    h1.metric(
        "RPM",
        str(report_rpm) if str(report_rpm).strip() else "NO DATA"
    )

    h2.metric(
        "Main Engines",
        display_value(
            report_engines,
            0,
            " ME"
        )
    )

    h3.metric(
        "Running Hours",
        display_value(
            report_hours,
            1,
            " h"
        )
    )

    h4.metric(
        "Fuel Consumption",
        display_value(
            actual_fuel,
            3,
            " MT"
        )
    )

    h5, h6, h7 = st.columns(3)

    h5.metric(
        "Opening ROB",
        display_value(
            opening_rob,
            3,
            " MT"
        )
    )

    h6.metric(
        "Closing ROB",
        display_value(
            closing_rob,
            3,
            " MT"
        )
    )

    h7.metric(
        "Average Speed",
        display_value(
            avg_speed,
            2,
            " kn"
        )
    )


# ============================================================
# 4. RPM → PEMAKAIAN BBM
# ============================================================

st.divider()
st.header("4. ⚙️ RPM → PEMAKAIAN BBM")

st.caption(
    "Baseline dihitung hanya dari DPR aktual kapal yang dipilih."
)

rpm_rows = []

if vessel_history.empty:

    st.info(
        "Belum ada historical DPR untuk kapal ini."
    )

else:

    for target_rpm in RPM_POINTS:

        matched = vessel_history[
            vessel_history["RPM"].apply(
                lambda value: rpm_matches(
                    value,
                    target_rpm
                )
            )
        ].copy()

        one_engine = matched[
            pd.to_numeric(
                matched["Main Engines Running"],
                errors="coerce"
            ) == 1
        ]

        two_engine = matched[
            pd.to_numeric(
                matched["Main Engines Running"],
                errors="coerce"
            ) == 2
        ]

        one_avg = safe_mean(
            one_engine["Actual Consumption MT"]
        )

        two_avg = safe_mean(
            two_engine["Actual Consumption MT"]
        )

        rpm_rows.append(
            {
                "RPM": target_rpm,
                "1 Mesin - BBM MT/day":
                    round(one_avg, 3)
                    if one_avg is not None
                    else "NO DATA",

                "2 Mesin - BBM MT/day":
                    round(two_avg, 3)
                    if two_avg is not None
                    else "NO DATA",

                "DPR Samples 1 ME":
                    len(
                        one_engine[
                            pd.to_numeric(
                                one_engine["Actual Consumption MT"],
                                errors="coerce"
                            ).notna()
                        ]
                    ),

                "DPR Samples 2 ME":
                    len(
                        two_engine[
                            pd.to_numeric(
                                two_engine["Actual Consumption MT"],
                                errors="coerce"
                            ).notna()
                        ]
                    ),
            }
        )

    rpm_table = pd.DataFrame(rpm_rows)

    st.dataframe(
        rpm_table,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# 5. CHECK / ACTION
# ============================================================

st.divider()
st.header("5. 🚦 CHECK / ACTION")

if selected_record is None and source_mode == "DPR MASTER DATABASE":

    st.info(
        "Pilih DPR untuk menjalankan Check / Action."
    )

else:

    current_fuel = pd.to_numeric(
        pd.Series([actual_fuel]),
        errors="coerce"
    ).iloc[0]

    current_engines = pd.to_numeric(
        pd.Series([report_engines]),
        errors="coerce"
    ).iloc[0]

    comparable = vessel_history.copy()

    if not comparable.empty:

        comparable = comparable[
            comparable["RPM"].apply(
                lambda value:
                any(
                    rpm_matches(value, rpm_value)
                    for rpm_value in rpm_numbers(report_rpm)
                )
            )
        ]

        if not pd.isna(current_engines):
            comparable = comparable[
                pd.to_numeric(
                    comparable["Main Engines Running"],
                    errors="coerce"
                ) == current_engines
            ]

        baseline = safe_mean(
            comparable["Actual Consumption MT"]
        )

    else:
        baseline = None


    if pd.isna(current_fuel):

        st.warning(
            "🟡 FUEL DATA INCOMPLETE — "
            "Actual Consumption tidak tersedia pada DPR."
        )

        st.write(
            "ACTION: Verifikasi fuel/ROB pada DPR kapal."
        )

    elif baseline is None or baseline <= 0:

        st.info(
            "🔵 BASELINE BELUM TERBENTUK — "
            "Belum cukup DPR pembanding pada RPM dan jumlah mesin yang sama."
        )

        st.write(
            "ACTION: Tambahkan DPR aktual. "
            "Sistem tidak membuat baseline buatan."
        )

    else:

        deviation_mt = current_fuel - baseline

        deviation_pct = (
            deviation_mt / baseline
        ) * 100

        x1, x2, x3 = st.columns(3)

        x1.metric(
            "Actual",
            f"{current_fuel:.3f} MT/day"
        )

        x2.metric(
            "DPR Baseline",
            f"{baseline:.3f} MT/day"
        )

        x3.metric(
            "Deviation",
            f"{deviation_pct:+.1f}%"
        )

        if deviation_pct <= 5:

            st.success(
                "🟢 NORMAL / EFFICIENT — "
                "Konsumsi berada dalam batas historical DPR."
            )

        elif deviation_pct <= 10:

            st.warning(
                "🟠 ATTENTION — "
                "Konsumsi mulai berada di atas historical DPR."
            )

        else:

            st.error(
                "🔴 HIGH FUEL CONSUMPTION — "
                "Konsumsi lebih dari 10% di atas historical DPR."
            )

        st.markdown(
            """
**CHECK / ACTION**

Periksa data DPR dan kondisi aktual:

- RPM dan engine load
- Main engine running
- Running hours
- Speed dan distance
- Weather / current
- Draft dan trim
- Hull / propeller condition
- Opening dan Closing ROB
- Bunker received
- Akurasi pengukuran fuel
"""
        )


# ============================================================
# 6. HISTORICAL DAILY REPORTS
# ============================================================

st.divider()
st.header("6. 📚 HISTORICAL DAILY REPORTS")

if vessel:

    historical_display = vessel_history.copy()

else:

    historical_display = master.copy()


if historical_display.empty:

    st.info(
        "Belum ada Historical Daily Reports."
    )

else:

    historical_display = historical_display.sort_values(
        "Date",
        ascending=False,
        na_position="last"
    )

    st.dataframe(
        historical_display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# 7. DPR FUEL INTELLIGENCE
# ============================================================

st.divider()
st.header("7. 🧠 DPR FUEL INTELLIGENCE")

if vessel_history.empty:

    st.info(
        "Upload DPR kapal untuk membangun Fuel Intelligence."
    )

else:

    fuel_series = pd.to_numeric(
        vessel_history["Actual Consumption MT"],
        errors="coerce"
    ).dropna()

    distance_series = pd.to_numeric(
        vessel_history["Distance NM"],
        errors="coerce"
    ).dropna()

    speed_series = pd.to_numeric(
        vessel_history["Average Speed Knots"],
        errors="coerce"
    ).dropna()

    f1, f2, f3, f4 = st.columns(4)

    f1.metric(
        "Historical DPR",
        len(vessel_history)
    )

    f2.metric(
        "Average Fuel",
        (
            f"{fuel_series.mean():.3f} MT/day"
            if len(fuel_series)
            else "NO DATA"
        )
    )

    f3.metric(
        "Maximum Fuel",
        (
            f"{fuel_series.max():.3f} MT/day"
            if len(fuel_series)
            else "NO DATA"
        )
    )

    f4.metric(
        "Minimum Fuel",
        (
            f"{fuel_series.min():.3f} MT/day"
            if len(fuel_series)
            else "NO DATA"
        )
    )

    if len(fuel_series):

        chart_df = vessel_history.copy()

        chart_df["Date"] = pd.to_datetime(
            chart_df["Date"],
            errors="coerce"
        )

        chart_df["Actual Consumption MT"] = pd.to_numeric(
            chart_df["Actual Consumption MT"],
            errors="coerce"
        )

        chart_df = (
            chart_df[
                ["Date", "Actual Consumption MT"]
            ]
            .dropna()
            .sort_values("Date")
            .set_index("Date")
        )

        if not chart_df.empty:

            st.subheader(
                "Fuel Consumption Trend"
            )

            st.line_chart(chart_df)


# ============================================================
# 8. DATA QUALITY CONTROL
# ============================================================

st.divider()
st.header("8. 🔎 DPR DATA QUALITY CONTROL")

if vessel_history.empty:

    st.info(
        "Belum ada DPR untuk diperiksa."
    )

else:

    quality = vessel_history.copy()

    quality["Missing RPM"] = (
        quality["RPM"]
        .astype(str)
        .str.strip()
        .isin(["", "nan", "None"])
    )

    quality["Missing Fuel"] = (
        pd.to_numeric(
            quality["Actual Consumption MT"],
            errors="coerce"
        )
        .isna()
    )

    quality["Missing ROB"] = (
        pd.to_numeric(
            quality["Closing ROB MT"],
            errors="coerce"
        )
        .isna()
    )

    quality["DATA STATUS"] = quality.apply(
        lambda row:
        "INCOMPLETE"
        if (
            row["Missing RPM"]
            or row["Missing Fuel"]
            or row["Missing ROB"]
        )
        else "COMPLETE",
        axis=1,
    )

    q1, q2 = st.columns(2)

    q1.metric(
        "Complete DPR",
        int(
            (quality["DATA STATUS"] == "COMPLETE")
            .sum()
        )
    )

    q2.metric(
        "Incomplete DPR",
        int(
            (quality["DATA STATUS"] == "INCOMPLETE")
            .sum()
        )
    )

    incomplete = quality[
        quality["DATA STATUS"] == "INCOMPLETE"
    ]

    if incomplete.empty:

        st.success(
            "Semua DPR yang diperiksa memiliki field fuel utama."
        )

    else:

        st.warning(
            "Ditemukan DPR dengan data belum lengkap. "
            "Sistem tidak mengisi data tersebut secara otomatis."
        )

        st.dataframe(
            incomplete[
                [
                    "Date",
                    "Vessel",
                    "RPM",
                    "Main Engines Running",
                    "Actual Consumption MT",
                    "Closing ROB MT",
                    "DATA STATUS",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# 9. IMPORT / EXPORT CENTER
# ============================================================

st.divider()
st.header("9. 📁 DPR IMPORT / EXPORT CENTER")

template_df = pd.DataFrame(
    columns=MASTER_COLUMNS
)

template_csv = template_df.to_csv(
    index=False
).encode("utf-8-sig")

st.download_button(
    "⬇️ DOWNLOAD DPR MASTER CSV TEMPLATE",
    data=template_csv,
    file_name="DPR_MASTER_TEMPLATE.csv",
    mime="text/csv",
    use_container_width=True,
)


if not master.empty:

    export_csv = master.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "⬇️ EXPORT DPR MASTER DATABASE",
        data=export_csv,
        file_name="DPR_MASTER_DATABASE.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.success(
    "SYSTEM ONLINE • DPR MASTER DATA ENGINE ACTIVE • "
    "GLOBAL VESSEL • REAL DPR BASELINE • NO INVENTED DATA"
)
