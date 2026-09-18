import io
import re
from datetime import datetime

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

APP_TITLE = "VESSEL FUEL EFFICIENCY & CONTROL INTELLIGENCE CENTER"

st.title(f"⚓ {APP_TITLE}")
st.caption(
    "UNIVERSAL CSV DPR MASTER • Dynamic Columns • Real DPR Data • Fuel in Liter"
)


# ============================================================
# SESSION STATE
# ============================================================

if "dpr_database" not in st.session_state:
    st.session_state.dpr_database = pd.DataFrame()

if "dpr_mapping" not in st.session_state:
    st.session_state.dpr_mapping = {}

if "current_file_name" not in st.session_state:
    st.session_state.current_file_name = ""

if "current_vessel" not in st.session_state:
    st.session_state.current_vessel = ""


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_vessel(value):
    return clean_text(value).upper()


def numeric_series(series):
    return pd.to_numeric(series, errors="coerce")


def parse_rpm(value):
    """
    Supports:
    1300
    1300 & 800
    900 / 1000
    1300-1200
    """

    if pd.isna(value):
        return []

    text = str(value)

    values = re.findall(r"\d+(?:\.\d+)?", text)

    result = []

    for value in values:
        try:
            result.append(float(value))
        except ValueError:
            pass

    return result


def rpm_matches(value, target):
    values = parse_rpm(value)

    return any(
        abs(float(x) - float(target)) < 0.001
        for x in values
    )


def safe_mean(series):
    values = numeric_series(series).dropna()

    if values.empty:
        return None

    return float(values.mean())


def safe_sum(series):
    values = numeric_series(series).dropna()

    if values.empty:
        return None

    return float(values.sum())


def fmt(value, decimals=1, suffix=""):
    if value is None or pd.isna(value):
        return "NO DATA"

    try:
        return f"{float(value):,.{decimals}f}{suffix}"
    except Exception:
        return f"{value}{suffix}"


def detect_column(columns, candidates):
    """
    Exact normalized match first.
    Then contains-match.
    """

    normalized = {
        str(col).strip().lower(): col
        for col in columns
    }

    for candidate in candidates:
        key = candidate.strip().lower()

        if key in normalized:
            return normalized[key]

    for candidate in candidates:
        candidate_lower = candidate.strip().lower()

        for col in columns:
            col_lower = str(col).strip().lower()

            if candidate_lower in col_lower:
                return col

    return None


def date_from_excel_or_text(value):
    if pd.isna(value):
        return pd.NaT

    # Excel serial date
    try:
        number = float(value)

        if 20000 <= number <= 80000:
            return pd.Timestamp(
                "1899-12-30"
            ) + pd.to_timedelta(number, unit="D")

    except Exception:
        pass

    return pd.to_datetime(
        value,
        errors="coerce",
        dayfirst=True,
    )


def normalize_dates(series):
    return series.apply(date_from_excel_or_text)


def valid_data_rows(df, mapping):
    """
    Remove obvious footer/note rows without changing original columns.
    """

    if df.empty:
        return df.copy()

    result = df.copy()

    date_col = mapping.get("date")

    if date_col and date_col in result.columns:
        parsed = normalize_dates(result[date_col])

        # Keep rows with a recognizable DPR date
        result = result[parsed.notna()].copy()

    return result.reset_index(drop=True)


def engine_count_from_row(row, port_col, stbd_col):
    count = 0

    if port_col and port_col in row.index:
        port = pd.to_numeric(
            pd.Series([row[port_col]]),
            errors="coerce"
        ).iloc[0]

        if pd.notna(port) and port > 0:
            count += 1

    if stbd_col and stbd_col in row.index:
        stbd = pd.to_numeric(
            pd.Series([row[stbd_col]]),
            errors="coerce"
        ).iloc[0]

        if pd.notna(stbd) and stbd > 0:
            count += 1

    return count


def merge_dynamic_database(existing, new_data):
    """
    Dynamic schema:
    union of every column from every DPR.
    Unknown columns are preserved.
    """

    if existing.empty:
        combined = new_data.copy()
    else:
        combined = pd.concat(
            [existing, new_data],
            ignore_index=True,
            sort=False,
        )

    return combined.reset_index(drop=True)


# ============================================================
# SIDEBAR — GLOBAL VESSEL
# ============================================================

st.sidebar.header("⚓ Vessel Control")

vessel = st.sidebar.text_input(
    "Kapal / Vessel",
    value=st.session_state.current_vessel,
    placeholder="Ketik nama kapal apa pun...",
).strip().upper()

if vessel:
    st.session_state.current_vessel = vessel

st.sidebar.caption(
    "Nama kapal bebas. Tidak ada daftar kapal tetap."
)


# ============================================================
# MASTER RULE
# ============================================================

st.info(
    "🔐 KUNCI UTAMA: FILE DPR kapal adalah sumber data utama. "
    "Aplikasi menerima CSV dengan jumlah kolom dinamis/unlimited. "
    "Kolom yang tidak dikenali tidak dibuang."
)


# ============================================================
# 1. UNIVERSAL DPR MASTER DATA ENGINE
# ============================================================

st.header("1. 📥 UNIVERSAL DPR MASTER DATA ENGINE")

st.write(
    "Upload CSV hasil DPR kapal. Sistem membaca seluruh kolom yang tersedia, "
    "kemudian memetakan field operasional penting untuk analisis."
)

uploaded = st.file_uploader(
    "Upload DPR kapal dalam format CSV",
    type=["csv"],
    key="universal_dpr_upload",
)

uploaded_df = None
working_df = None
mapping = {}


if uploaded is not None:

    try:
        # Try common CSV encodings
        raw_bytes = uploaded.getvalue()

        read_success = False
        last_error = None

        for encoding in [
            "utf-8-sig",
            "utf-8",
            "latin-1",
            "cp1252",
        ]:
            try:
                uploaded_df = pd.read_csv(
                    io.BytesIO(raw_bytes),
                    encoding=encoding,
                )

                read_success = True
                break

            except Exception as e:
                last_error = e

        if not read_success:
            raise ValueError(
                f"CSV tidak dapat dibaca: {last_error}"
            )

        # Clean column labels only.
        # Original data values are preserved.
        uploaded_df.columns = [
            str(col).strip()
            for col in uploaded_df.columns
        ]

        st.session_state.current_file_name = uploaded.name

        st.success(
            f"CSV berhasil dibaca • "
            f"{len(uploaded_df)} baris • "
            f"{len(uploaded_df.columns)} kolom."
        )

        st.subheader("Preview DPR Asli")

        st.dataframe(
            uploaded_df,
            use_container_width=True,
            hide_index=True,
        )


        # ====================================================
        # AUTO FIELD DETECTION
        # ====================================================

        columns = list(uploaded_df.columns)

        auto_mapping = {
            "date": detect_column(
                columns,
                [
                    "Tanggal",
                    "Date",
                    "Report Date",
                    "DPR Date",
                ],
            ),

            "status": detect_column(
                columns,
                [
                    "Status Data",
                    "Status",
                ],
            ),

            "position": detect_column(
                columns,
                [
                    "Posisi (Lat/Long)",
                    "Position",
                    "Lat/Long",
                ],
            ),

            "origin": detect_column(
                columns,
                [
                    "Pelabuhan Asal",
                    "Origin",
                    "From",
                ],
            ),

            "destination": detect_column(
                columns,
                [
                    "Tujuan Berikutnya",
                    "Destination",
                    "To",
                ],
            ),

            "distance": detect_column(
                columns,
                [
                    "DMG (nm)",
                    "Distance NM",
                    "Distance",
                ],
            ),

            "speed": detect_column(
                columns,
                [
                    "Avg Speed (kt)",
                    "Average Speed",
                    "Speed",
                ],
            ),

            "rpm": detect_column(
                columns,
                [
                    "RPM M/E",
                    "RPM",
                    "Main Engine RPM",
                    "ME RPM",
                ],
            ),

            "me_port": detect_column(
                columns,
                [
                    "M/E Port (hr)",
                    "ME Port",
                    "Main Engine Port",
                ],
            ),

            "me_stbd": detect_column(
                columns,
                [
                    "M/E Stbd (hr)",
                    "ME Stbd",
                    "Main Engine Stbd",
                    "Main Engine Starboard",
                ],
            ),

            "total_rh": detect_column(
                columns,
                [
                    "Total RH*",
                    "Total RH",
                    "Running Hours",
                ],
            ),

            "opening": detect_column(
                columns,
                [
                    "Opening",
                    "Opening ROB",
                ],
            ),

            "received": detect_column(
                columns,
                [
                    "Received",
                    "Bunker Received",
                ],
            ),

            "transferred": detect_column(
                columns,
                [
                    "Transferred",
                    "Transfer",
                ],
            ),

            "consume": detect_column(
                columns,
                [
                    "Consume",
                    "Consumption",
                    "Fuel Consumption",
                ],
            ),

            "closing_report": detect_column(
                columns,
                [
                    "Closing (Lapor)",
                    "Closing ROB",
                    "Closing",
                ],
            ),

            "closing_calc": detect_column(
                columns,
                [
                    "Closing (Hitung)*",
                    "Closing (Hitung)",
                    "Calculated Closing",
                ],
            ),

            "difference": detect_column(
                columns,
                [
                    "Selisih*",
                    "Selisih",
                    "Difference",
                ],
            ),

            "tow_condition": detect_column(
                columns,
                [
                    "Kondisi Tow",
                    "Tow Condition",
                ],
            ),

            "wind_speed": detect_column(
                columns,
                [
                    "Wind Speed",
                ],
            ),

            "beaufort": detect_column(
                columns,
                [
                    "Beaufort",
                ],
            ),

            "sea_state": detect_column(
                columns,
                [
                    "Sea State",
                ],
            ),

            "draft_fwd": detect_column(
                columns,
                [
                    "Fwd (m)",
                    "Draft Fwd",
                    "Forward Draft",
                ],
            ),

            "draft_aft": detect_column(
                columns,
                [
                    "Aft (m)",
                    "Draft Aft",
                    "Aft Draft",
                ],
            ),
        }


        # ====================================================
        # FIELD MAPPING REVIEW
        # ====================================================

        st.subheader("🔗 DPR Field Mapping")

        st.caption(
            "Sistem mencoba mengenali field secara otomatis. "
            "Jika nama kolom DPR kapal berbeda, pilih kolom yang benar."
        )

        mapping_options = ["— TIDAK ADA —"] + columns

        def mapped_select(label, key):
            detected = auto_mapping.get(key)

            default_index = 0

            if detected in columns:
                default_index = (
                    columns.index(detected) + 1
                )

            selected = st.selectbox(
                label,
                mapping_options,
                index=default_index,
                key=f"map_{key}",
            )

            return (
                None
                if selected == "— TIDAK ADA —"
                else selected
            )


        with st.expander(
            "Periksa / Ubah Mapping DPR",
            expanded=False,
        ):

            m1, m2, m3 = st.columns(3)

            mapping["date"] = mapped_select(
                "Tanggal DPR",
                "date"
            )

            mapping["status"] = mapped_select(
                "Status Data",
                "status"
            )

            mapping["position"] = mapped_select(
                "Position",
                "position"
            )

            mapping["origin"] = mapped_select(
                "Origin",
                "origin"
            )

            mapping["destination"] = mapped_select(
                "Destination",
                "destination"
            )

            mapping["distance"] = mapped_select(
                "Distance / DMG",
                "distance"
            )

            mapping["speed"] = mapped_select(
                "Average Speed",
                "speed"
            )

            mapping["rpm"] = mapped_select(
                "Main Engine RPM",
                "rpm"
            )

            mapping["me_port"] = mapped_select(
                "M/E Port Running Hours",
                "me_port"
            )

            mapping["me_stbd"] = mapped_select(
                "M/E Stbd Running Hours",
                "me_stbd"
            )

            mapping["total_rh"] = mapped_select(
                "Total Running Hours",
                "total_rh"
            )

            mapping["opening"] = mapped_select(
                "Fuel Opening (Liter)",
                "opening"
            )

            mapping["received"] = mapped_select(
                "Fuel Received (Liter)",
                "received"
            )

            mapping["transferred"] = mapped_select(
                "Fuel Transferred (Liter)",
                "transferred"
            )

            mapping["consume"] = mapped_select(
                "Fuel Consume (Liter)",
                "consume"
            )

            mapping["closing_report"] = mapped_select(
                "Fuel Closing Report (Liter)",
                "closing_report"
            )

            mapping["closing_calc"] = mapped_select(
                "Fuel Closing Calculated (Liter)",
                "closing_calc"
            )

            mapping["difference"] = mapped_select(
                "Fuel Difference",
                "difference"
            )

            mapping["tow_condition"] = mapped_select(
                "Tow Condition",
                "tow_condition"
            )

            mapping["wind_speed"] = mapped_select(
                "Wind Speed",
                "wind_speed"
            )

            mapping["beaufort"] = mapped_select(
                "Beaufort",
                "beaufort"
            )

            mapping["sea_state"] = mapped_select(
                "Sea State",
                "sea_state"
            )

            mapping["draft_fwd"] = mapped_select(
                "Draft Forward",
                "draft_fwd"
            )

            mapping["draft_aft"] = mapped_select(
                "Draft Aft",
                "draft_aft"
            )


        # If expander controls haven't been interacted with,
        # use their selected values already generated above.
        st.session_state.dpr_mapping = mapping.copy()

        working_df = valid_data_rows(
            uploaded_df,
            mapping
        )

        st.write(
            f"**DPR data rows detected:** "
            f"{len(working_df)}"
        )


        # ====================================================
        # IMPORT
        # ====================================================

        if st.button(
            "✅ VALIDATE & IMPORT TO DPR MASTER DATABASE",
            type="primary",
            use_container_width=True,
        ):

            if not vessel:
                st.error(
                    "Ketik nama kapal pada sidebar sebelum import."
                )

            elif mapping.get("date") is None:
                st.error(
                    "Kolom Tanggal DPR harus dipetakan sebelum import."
                )

            else:

                import_df = working_df.copy()

                # Add system metadata without deleting DPR fields
                import_df.insert(
                    0,
                    "__VESSEL__",
                    vessel,
                )

                import_df.insert(
                    1,
                    "__SOURCE_FILE__",
                    uploaded.name,
                )

                import_df.insert(
                    2,
                    "__IMPORTED_AT__",
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                )

                import_df.insert(
                    3,
                    "__DPR_DATE__",
                    normalize_dates(
                        import_df[mapping["date"]]
                    ),
                )

                # Store mapping as metadata columns
                for key, value in mapping.items():
                    import_df[
                        f"__MAP_{key.upper()}__"
                    ] = value or ""

                st.session_state.dpr_database = (
                    merge_dynamic_database(
                        st.session_state.dpr_database,
                        import_df,
                    )
                )

                st.success(
                    f"{len(import_df)} DPR record "
                    f"untuk {vessel} berhasil di-import."
                )

                st.rerun()

    except Exception as e:
        st.error(
            f"DPR CSV ERROR: {e}"
        )


# ============================================================
# DATABASE
# ============================================================

database = st.session_state.dpr_database.copy()

if (
    not database.empty
    and vessel
    and "__VESSEL__" in database.columns
):
    vessel_db = database[
        database["__VESSEL__"]
        .astype(str)
        .str.upper()
        == vessel
    ].copy()
else:
    vessel_db = pd.DataFrame()


# ============================================================
# DATABASE STATUS
# ============================================================

st.divider()
st.header("2. 🗄️ DPR MASTER DATABASE STATUS")

s1, s2, s3, s4 = st.columns(4)

s1.metric(
    "DPR Records",
    len(database)
)

if database.empty:

    s2.metric("Vessels", 0)
    s3.metric("DPR Columns", 0)
    s4.metric("Latest DPR", "NO DATA")

else:

    vessel_count = (
        database["__VESSEL__"].nunique()
        if "__VESSEL__" in database.columns
        else 0
    )

    raw_columns = [
        col
        for col in database.columns
        if not str(col).startswith("__")
    ]

    latest = "NO DATA"

    if "__DPR_DATE__" in database.columns:
        dates = pd.to_datetime(
            database["__DPR_DATE__"],
            errors="coerce"
        ).dropna()

        if not dates.empty:
            latest = dates.max().date().isoformat()

    s2.metric(
        "Vessels",
        vessel_count
    )

    s3.metric(
        "Dynamic DPR Columns",
        len(raw_columns)
    )

    s4.metric(
        "Latest DPR",
        latest
    )


# ============================================================
# GET MAPPING FROM IMPORTED DATABASE
# ============================================================

def get_imported_mapping(df):
    result = {}

    if df.empty:
        return result

    for col in df.columns:

        if (
            str(col).startswith("__MAP_")
            and str(col).endswith("__")
        ):

            key = (
                str(col)
                .replace("__MAP_", "")
                .replace("__", "")
                .lower()
            )

            values = (
                df[col]
                .dropna()
                .astype(str)
            )

            values = values[
                values.str.strip() != ""
            ]

            if not values.empty:
                result[key] = values.iloc[-1]

    return result


active_mapping = get_imported_mapping(
    vessel_db
)


# ============================================================
# 3. DAILY REPORT KKM
# ============================================================

st.divider()
st.header("3. 🧾 DAILY REPORT KKM")

if not vessel:

    st.warning(
        "Ketik nama kapal pada sidebar."
    )

elif vessel_db.empty:

    st.info(
        f"Belum ada DPR MASTER DATABASE untuk {vessel}."
    )

else:

    dates = pd.to_datetime(
        vessel_db["__DPR_DATE__"],
        errors="coerce"
    )

    valid_dates = (
        dates
        .dropna()
        .dt.date
        .sort_values(ascending=False)
        .unique()
        .tolist()
    )

    if not valid_dates:

        st.warning(
            "Tanggal DPR tidak dapat dibaca."
        )

    else:

        selected_date = st.selectbox(
            "Pilih tanggal DPR",
            valid_dates,
        )

        day_mask = (
            pd.to_datetime(
                vessel_db["__DPR_DATE__"],
                errors="coerce"
            ).dt.date
            == selected_date
        )

        day_data = vessel_db[
            day_mask
        ].copy()

        if not day_data.empty:

            report = day_data.iloc[-1]

            def mapped_value(key):
                col = active_mapping.get(key)

                if (
                    col
                    and col in report.index
                ):
                    return report[col]

                return None


            report_rpm = mapped_value("rpm")
            report_port = mapped_value("me_port")
            report_stbd = mapped_value("me_stbd")
            report_rh = mapped_value("total_rh")

            report_opening = mapped_value("opening")
            report_received = mapped_value("received")
            report_transfer = mapped_value("transferred")
            report_consume = mapped_value("consume")
            report_closing = mapped_value("closing_report")

            report_distance = mapped_value("distance")
            report_speed = mapped_value("speed")
            report_position = mapped_value("position")

            report_origin = mapped_value("origin")
            report_destination = mapped_value(
                "destination"
            )

            report_tow = mapped_value(
                "tow_condition"
            )

            engine_count = engine_count_from_row(
                report,
                active_mapping.get("me_port"),
                active_mapping.get("me_stbd"),
            )

            st.success(
                "Daily Report KKM dibaca langsung "
                "dari DPR MASTER DATABASE."
            )

            k1, k2, k3, k4 = st.columns(4)

            k1.metric(
                "RPM M/E",
                clean_text(report_rpm)
                or "NO DATA"
            )

            k2.metric(
                "Main Engines Running",
                f"{engine_count} ME"
            )

            k3.metric(
                "M/E Port RH",
                fmt(
                    pd.to_numeric(
                        report_port,
                        errors="coerce"
                    ),
                    1,
                    " h"
                )
            )

            k4.metric(
                "M/E Stbd RH",
                fmt(
                    pd.to_numeric(
                        report_stbd,
                        errors="coerce"
                    ),
                    1,
                    " h"
                )
            )

            f1, f2, f3, f4, f5 = st.columns(5)

            f1.metric(
                "Opening",
                fmt(
                    pd.to_numeric(
                        report_opening,
                        errors="coerce"
                    ),
                    0,
                    " L"
                )
            )

            f2.metric(
                "Received",
                fmt(
                    pd.to_numeric(
                        report_received,
                        errors="coerce"
                    ),
                    0,
                    " L"
                )
            )

            f3.metric(
                "Transferred",
                fmt(
                    pd.to_numeric(
                        report_transfer,
                        errors="coerce"
                    ),
                    0,
                    " L"
                )
            )

            f4.metric(
                "Consume",
                fmt(
                    pd.to_numeric(
                        report_consume,
                        errors="coerce"
                    ),
                    0,
                    " L"
                )
            )

            f5.metric(
                "Closing",
                fmt(
                    pd.to_numeric(
                        report_closing,
                        errors="coerce"
                    ),
                    0,
                    " L"
                )
            )

            st.write(
                f"**Position:** "
                f"{clean_text(report_position) or 'NO DATA'}"
            )

            st.write(
                f"**Voyage:** "
                f"{clean_text(report_origin) or 'NO DATA'}"
                f" → "
                f"{clean_text(report_destination) or 'NO DATA'}"
            )

            st.write(
                f"**Tow Condition:** "
                f"{clean_text(report_tow) or 'NO DATA'}"
            )


# ============================================================
# 4. HASIL HARI INI
# ============================================================

st.divider()
st.header("4. 📊 HASIL HARI INI")

if vessel_db.empty:

    st.info(
        "Upload dan import DPR untuk menampilkan hasil."
    )

else:

    consume_col = active_mapping.get("consume")
    rpm_col = active_mapping.get("rpm")
    speed_col = active_mapping.get("speed")
    distance_col = active_mapping.get("distance")

    latest_rows = vessel_db.copy()

    latest_rows["__DATE_SORT__"] = pd.to_datetime(
        latest_rows["__DPR_DATE__"],
        errors="coerce"
    )

    latest_rows = latest_rows.sort_values(
        "__DATE_SORT__",
        ascending=False
    )

    latest_row = latest_rows.iloc[0]

    h1, h2, h3, h4 = st.columns(4)

    h1.metric(
        "Latest DPR",
        latest_row["__DATE_SORT__"].date().isoformat()
        if pd.notna(latest_row["__DATE_SORT__"])
        else "NO DATA"
    )

    h2.metric(
        "RPM",
        clean_text(
            latest_row[rpm_col]
            if rpm_col in latest_row.index
            else None
        ) or "NO DATA"
    )

    h3.metric(
        "Fuel Consumption",
        fmt(
            pd.to_numeric(
                latest_row[consume_col]
                if consume_col in latest_row.index
                else None,
                errors="coerce"
            ),
            0,
            " L/day"
        )
    )

    h4.metric(
        "Average Speed",
        fmt(
            pd.to_numeric(
                latest_row[speed_col]
                if speed_col in latest_row.index
                else None,
                errors="coerce"
            ),
            2,
            " kn"
        )
    )


# ============================================================
# 5. RPM → PEMAKAIAN BBM
# ============================================================

st.divider()
st.header("5. ⚙️ RPM → PEMAKAIAN BBM")

st.caption(
    "Baseline dihitung dari konsumsi Liter yang benar-benar "
    "tercatat pada historical DPR kapal."
)

rpm_col = active_mapping.get("rpm")
consume_col = active_mapping.get("consume")
port_col = active_mapping.get("me_port")
stbd_col = active_mapping.get("me_stbd")

if (
    vessel_db.empty
    or not rpm_col
    or not consume_col
    or rpm_col not in vessel_db.columns
    or consume_col not in vessel_db.columns
):

    st.info(
        "RPM dan/atau Fuel Consume belum tersedia atau belum dipetakan."
    )

else:

    fuel_df = vessel_db.copy()

    fuel_df["__ENGINE_COUNT__"] = fuel_df.apply(
        lambda row: engine_count_from_row(
            row,
            port_col,
            stbd_col,
        ),
        axis=1,
    )

    fuel_df["__CONSUME_L__"] = pd.to_numeric(
        fuel_df[consume_col],
        errors="coerce"
    )

    observed_rpms = set()

    for value in fuel_df[rpm_col]:
        for rpm in parse_rpm(value):
            observed_rpms.add(int(rpm))

    standard_rpms = {
        600, 700, 800, 900,
        1000, 1100, 1200, 1300
    }

    all_rpms = sorted(
        standard_rpms.union(observed_rpms)
    )

    rpm_results = []

    for target_rpm in all_rpms:

        matched = fuel_df[
            fuel_df[rpm_col].apply(
                lambda x: rpm_matches(
                    x,
                    target_rpm
                )
            )
        ].copy()

        one_me = matched[
            matched["__ENGINE_COUNT__"] == 1
        ]

        two_me = matched[
            matched["__ENGINE_COUNT__"] == 2
        ]

        avg_1 = safe_mean(
            one_me["__CONSUME_L__"]
        )

        avg_2 = safe_mean(
            two_me["__CONSUME_L__"]
        )

        rpm_results.append(
            {
                "RPM": target_rpm,

                "1 Mesin - Liter/day":
                    round(avg_1, 1)
                    if avg_1 is not None
                    else "NO DATA",

                "DPR Samples 1 ME":
                    int(
                        one_me[
                            "__CONSUME_L__"
                        ].notna().sum()
                    ),

                "2 Mesin - Liter/day":
                    round(avg_2, 1)
                    if avg_2 is not None
                    else "NO DATA",

                "DPR Samples 2 ME":
                    int(
                        two_me[
                            "__CONSUME_L__"
                        ].notna().sum()
                    ),
            }
        )

    st.dataframe(
        pd.DataFrame(rpm_results),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# 6. CHECK / ACTION
# ============================================================

st.divider()
st.header("6. 🚦 CHECK / ACTION")

if vessel_db.empty:

    st.info(
        "Belum ada DPR untuk dianalisis."
    )

elif not consume_col or consume_col not in vessel_db.columns:

    st.warning(
        "Fuel Consume belum dipetakan."
    )

else:

    analysis = vessel_db.copy()

    analysis["__FUEL__"] = pd.to_numeric(
        analysis[consume_col],
        errors="coerce"
    )

    valid_fuel = analysis[
        analysis["__FUEL__"].notna()
    ].copy()

    if valid_fuel.empty:

        st.warning(
            "Tidak ada data konsumsi BBM yang valid."
        )

    else:

        valid_fuel["__DATE__"] = pd.to_datetime(
            valid_fuel["__DPR_DATE__"],
            errors="coerce"
        )

        valid_fuel = valid_fuel.sort_values(
            "__DATE__"
        )

        latest = valid_fuel.iloc[-1]

        actual = latest["__FUEL__"]

        current_rpm = (
            latest[rpm_col]
            if rpm_col
            and rpm_col in latest.index
            else None
        )

        comparable = valid_fuel.copy()

        if rpm_col and current_rpm is not None:

            current_rpms = parse_rpm(
                current_rpm
            )

            if current_rpms:

                comparable = comparable[
                    comparable[rpm_col].apply(
                        lambda value:
                        any(
                            rpm_matches(
                                value,
                                rpm
                            )
                            for rpm
                            in current_rpms
                        )
                    )
                ]

        # Exclude current row where possible
        historical = comparable.iloc[:-1]

        baseline = safe_mean(
            historical["__FUEL__"]
        )

        if baseline is None or baseline <= 0:

            st.info(
                "🔵 BASELINE BELUM CUKUP — "
                "Tambahkan historical DPR pada kondisi RPM yang sama."
            )

        else:

            deviation_l = actual - baseline

            deviation_pct = (
                deviation_l / baseline
            ) * 100

            a1, a2, a3, a4 = st.columns(4)

            a1.metric(
                "Actual",
                f"{actual:,.0f} L/day"
            )

            a2.metric(
                "Historical Baseline",
                f"{baseline:,.0f} L/day"
            )

            a3.metric(
                "Deviation",
                f"{deviation_pct:+.1f}%"
            )

            a4.metric(
                "Excess / Saving",
                f"{deviation_l:+,.0f} L/day"
            )

            if deviation_pct <= 5:

                st.success(
                    "🟢 NORMAL — konsumsi berada "
                    "dalam historical baseline."
                )

            elif deviation_pct <= 10:

                st.warning(
                    "🟠 ATTENTION — konsumsi mulai "
                    "di atas historical baseline."
                )

            else:

                st.error(
                    "🔴 HIGH FUEL CONSUMPTION — "
                    "perlu pemeriksaan operasional."
                )

            st.markdown(
                """
**CHECK / ACTION**

Periksa data DPR aktual:

- RPM / engine load
- M/E Port dan Starboard running hours
- Speed dan distance
- Weather / Beaufort / sea state
- Draft
- Tow condition
- Opening / Received / Transferred / Closing
- Akurasi pencatatan fuel
"""
            )


# ============================================================
# 7. HISTORICAL DAILY REPORTS
# ============================================================

st.divider()
st.header("7. 📚 HISTORICAL DAILY REPORTS")

if vessel_db.empty:

    st.info(
        "Belum ada Historical Daily Reports."
    )

else:

    raw_columns = [
        col
        for col in vessel_db.columns
        if not str(col).startswith("__")
    ]

    display_history = vessel_db.copy()

    display_history = display_history.sort_values(
        "__DPR_DATE__",
        ascending=False,
        na_position="last",
    )

    st.write(
        f"**{vessel} • {len(display_history)} DPR records • "
        f"{len(raw_columns)} original DPR columns**"
    )

    st.dataframe(
        display_history[raw_columns],
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# 8. DPR FUEL INTELLIGENCE
# ============================================================

st.divider()
st.header("8. 🧠 DPR FUEL INTELLIGENCE")

if (
    vessel_db.empty
    or not consume_col
    or consume_col not in vessel_db.columns
):

    st.info(
        "Belum ada data Fuel Consume untuk dianalisis."
    )

else:

    intelligence = vessel_db.copy()

    intelligence["__FUEL_L__"] = pd.to_numeric(
        intelligence[consume_col],
        errors="coerce"
    )

    intelligence["__DATE__"] = pd.to_datetime(
        intelligence["__DPR_DATE__"],
        errors="coerce"
    )

    valid = intelligence.dropna(
        subset=[
            "__DATE__",
            "__FUEL_L__",
        ]
    ).copy()

    if valid.empty:

        st.info(
            "Tidak ada record konsumsi yang valid."
        )

    else:

        total_fuel = valid["__FUEL_L__"].sum()
        avg_fuel = valid["__FUEL_L__"].mean()
        max_fuel = valid["__FUEL_L__"].max()
        min_fuel = valid["__FUEL_L__"].min()

        i1, i2, i3, i4 = st.columns(4)

        i1.metric(
            "Total Fuel",
            f"{total_fuel:,.0f} L"
        )

        i2.metric(
            "Average / DPR",
            f"{avg_fuel:,.0f} L"
        )

        i3.metric(
            "Maximum",
            f"{max_fuel:,.0f} L"
        )

        i4.metric(
            "Minimum",
            f"{min_fuel:,.0f} L"
        )

        chart = (
            valid[
                [
                    "__DATE__",
                    "__FUEL_L__",
                ]
            ]
            .sort_values("__DATE__")
            .set_index("__DATE__")
        )

        st.subheader(
            "Fuel Consumption Trend"
        )

        st.line_chart(
            chart
        )


# ============================================================
# 9. DPR DATA QUALITY CONTROL
# ============================================================

st.divider()
st.header("9. 🔎 DPR DATA QUALITY CONTROL")

if vessel_db.empty:

    st.info(
        "Belum ada DPR untuk diperiksa."
    )

else:

    qc = vessel_db.copy()

    qc_results = []

    for _, row in qc.iterrows():

        issues = []

        dpr_date = row.get(
            "__DPR_DATE__",
            None
        )

        if pd.isna(dpr_date):
            issues.append(
                "Tanggal DPR tidak valid"
            )

        if rpm_col and rpm_col in row.index:
            if clean_text(row[rpm_col]) == "":
                issues.append(
                    "RPM kosong"
                )

        if consume_col and consume_col in row.index:
            fuel_value = pd.to_numeric(
                pd.Series(
                    [row[consume_col]]
                ),
                errors="coerce"
            ).iloc[0]

            if pd.isna(fuel_value):
                issues.append(
                    "Fuel Consume kosong"
                )

        opening_col = active_mapping.get(
            "opening"
        )

        received_col = active_mapping.get(
            "received"
        )

        transfer_col = active_mapping.get(
            "transferred"
        )

        closing_col = active_mapping.get(
            "closing_report"
        )

        if (
            opening_col
            and consume_col
            and closing_col
            and opening_col in row.index
            and consume_col in row.index
            and closing_col in row.index
        ):

            opening = pd.to_numeric(
                pd.Series(
                    [row[opening_col]]
                ),
                errors="coerce"
            ).iloc[0]

            received = pd.to_numeric(
                pd.Series(
                    [row[received_col]]
                ),
                errors="coerce"
            ).iloc[0] if (
                received_col
                and received_col in row.index
            ) else 0

            transferred = pd.to_numeric(
                pd.Series(
                    [row[transfer_col]]
                ),
                errors="coerce"
            ).iloc[0] if (
                transfer_col
                and transfer_col in row.index
            ) else 0

            consume = pd.to_numeric(
                pd.Series(
                    [row[consume_col]]
                ),
                errors="coerce"
            ).iloc[0]

            closing = pd.to_numeric(
                pd.Series(
                    [row[closing_col]]
                ),
                errors="coerce"
            ).iloc[0]

            if pd.isna(received):
                received = 0

            if pd.isna(transferred):
                transferred = 0

            if (
                pd.notna(opening)
                and pd.notna(consume)
                and pd.notna(closing)
            ):

                calculated = (
                    opening
                    + received
                    - transferred
                    - consume
                )

                difference = (
                    closing - calculated
                )

                if abs(difference) > 1:
                    issues.append(
                        f"Fuel balance difference "
                        f"{difference:,.0f} L"
                    )

        qc_results.append(
            {
                "DPR Date":
                    pd.to_datetime(
                        dpr_date,
                        errors="coerce"
                    ).date()
                    if pd.notna(
                        pd.to_datetime(
                            dpr_date,
                            errors="coerce"
                        )
                    )
                    else "NO DATE",

                "Status":
                    "COMPLETE"
                    if not issues
                    else "CHECK",

                "Issues":
                    " | ".join(issues)
                    if issues
                    else "OK",
            }
        )

    qc_df = pd.DataFrame(
        qc_results
    )

    q1, q2 = st.columns(2)

    q1.metric(
        "Complete",
        int(
            (
                qc_df["Status"]
                == "COMPLETE"
            ).sum()
        )
    )

    q2.metric(
        "Need Check",
        int(
            (
                qc_df["Status"]
                == "CHECK"
            ).sum()
        )
    )

    st.dataframe(
        qc_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# 10. DPR IMPORT / EXPORT CENTER
# ============================================================

st.divider()
st.header("10. 📁 DPR IMPORT / EXPORT CENTER")

st.caption(
    "Tidak ada template dengan jumlah kolom tetap. "
    "Gunakan struktur CSV DPR asli kapal."
)

if not vessel_db.empty:

    raw_columns = [
        col
        for col in vessel_db.columns
        if not str(col).startswith("__")
    ]

    export_df = vessel_db[
        raw_columns
    ].copy()

    export_csv = export_df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "⬇️ EXPORT HISTORICAL DPR CSV",
        data=export_csv,
        file_name=(
            f"{vessel.replace(' ', '_')}"
            "_HISTORICAL_DPR.csv"
        ),
        mime="text/csv",
        use_container_width=True,
    )


# ============================================================
# SYSTEM STATUS
# ============================================================

st.divider()

st.success(
    "SYSTEM ONLINE • UNIVERSAL CSV DPR MASTER ACTIVE • "
    "DYNAMIC/UNLIMITED COLUMNS • GLOBAL VESSEL • "
    "FUEL IN LITER • REAL DPR DATA"
)
