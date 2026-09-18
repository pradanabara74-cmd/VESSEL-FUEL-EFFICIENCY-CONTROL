import io
from datetime import date

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Vessel Fuel Efficiency", page_icon="⛽", layout="wide")

KNOWN_VESSELS = [
    "ASL MANTRUS", "ASL MULIA", "ASL SENTOSA", "ASL VICTORY", "ASL INTAN",
    "ASL GEMINI", "ASL BEAVER", "ASL CRESST", "ASL CALYPSO", "ASL PHOENIX",
    "ASL MARINE 8", "AST LEGEND", "TERAS HYDRA", "AST MAJU", "KARYA ABADI 8",
    "NUSANTARA ABADI 1", "CAPITOL T2002", "CAPITOL T2001", "TB1000-06",
    "TB1000-07", "WHALE 3",
]
RPM_POINTS = [600, 700, 800, 900, 1000, 1100, 1200, 1300]
MODES = ["Free Sailing", "Towing", "Standby", "Maneuvering", "Port / Idle", "Anchor"]
COLUMNS = [
    "Date", "Vessel", "Operating Mode", "RPM", "Main Engines Running",
    "Running Hours", "Opening ROB MT", "Bunker Received MT", "Closing ROB MT",
    "Actual Consumption MT", "Distance NM", "Average Speed Knots", "Remarks",
]

if "fuel_reports" not in st.session_state:
    st.session_state.fuel_reports = pd.DataFrame(columns=COLUMNS)

st.title("⛽ VESSEL FUEL EFFICIENCY — DAILY KKM REPORT")
st.caption("Input sederhana Daily Report KKM → konsumsi aktual → baseline historis → status → tindakan.")

with st.sidebar:
    st.header("🚢 Vessel")
    vessel_source = st.radio(
        "Pilih sumber nama kapal",
        ["Pilih dari daftar", "Ketik kapal lain"],
        horizontal=True,
    )
    if vessel_source == "Pilih dari daftar":
        vessel = st.selectbox("Kapal", KNOWN_VESSELS)
    else:
        vessel = st.text_input(
            "Nama Kapal (bebas)",
            placeholder="Contoh: EVER GIVEN / MAERSK ...",
        ).strip().upper()
        if not vessel:
            st.warning("Masukkan nama kapal untuk memulai Daily Report.")
    mode = st.selectbox("Operating Mode", MODES)
    st.info("RPM 600–1300+ dianalisis dari data aktual kapal yang tersimpan. Sistem tidak mengarang konsumsi bila baseline belum tersedia.")

# ---------- INPUT ----------
st.header("1. 📝 Daily Report KKM")
with st.form("daily_report_form", clear_on_submit=False):
    a, b, c, d = st.columns(4)
    report_date = a.date_input("Tanggal", value=date.today())
    rpm = b.selectbox("RPM", RPM_POINTS)
    engines = c.radio("Main Engine Running", [1, 2], horizontal=True)
    running_hours = d.number_input("Running Hours", min_value=0.0, max_value=24.0, value=24.0, step=0.5)

    e, f, g = st.columns(3)
    opening_rob = e.number_input("Opening ROB (MT)", min_value=0.0, value=0.0, step=0.1, format="%.3f")
    bunker = f.number_input("Bunker Received (MT)", min_value=0.0, value=0.0, step=0.1, format="%.3f")
    closing_rob = g.number_input("Closing ROB (MT)", min_value=0.0, value=0.0, step=0.1, format="%.3f")

    h, i = st.columns(2)
    distance = h.number_input("Distance (NM) — optional", min_value=0.0, value=0.0, step=1.0)
    speed = i.number_input("Average Speed (knots) — optional", min_value=0.0, value=0.0, step=0.1)
    remarks = st.text_input("Remarks — optional")
    submitted = st.form_submit_button("🔎 ANALYZE & SAVE DAILY REPORT", type="primary", use_container_width=True)

if submitted:
    available = opening_rob + bunker
    actual = available - closing_rob
    errors = []
    if opening_rob <= 0:
        errors.append("Opening ROB harus lebih dari 0 MT.")
    if closing_rob > available:
        errors.append("Closing ROB tidak boleh lebih besar dari Opening ROB + Bunker Received.")
    if actual < 0:
        errors.append("Konsumsi aktual menjadi negatif; periksa ROB dan bunker.")
    if running_hours <= 0:
        errors.append("Running Hours harus lebih dari 0 jam.")

    if errors:
        for msg in errors:
            st.error(msg)
    else:
        hist = st.session_state.fuel_reports.copy()
        if not hist.empty:
            match = hist[
                (hist["Vessel"] == vessel)
                & (hist["Operating Mode"] == mode)
                & (pd.to_numeric(hist["RPM"], errors="coerce") == rpm)
                & (pd.to_numeric(hist["Main Engines Running"], errors="coerce") == engines)
            ]
        else:
            match = hist

        baseline = pd.to_numeric(match.get("Actual Consumption MT", pd.Series(dtype=float)), errors="coerce").dropna().mean() if len(match) else None

        new_row = pd.DataFrame([{
            "Date": str(report_date), "Vessel": vessel, "Operating Mode": mode,
            "RPM": rpm, "Main Engines Running": engines, "Running Hours": running_hours,
            "Opening ROB MT": opening_rob, "Bunker Received MT": bunker,
            "Closing ROB MT": closing_rob, "Actual Consumption MT": actual,
            "Distance NM": distance, "Average Speed Knots": speed, "Remarks": remarks,
        }])
        st.session_state.fuel_reports = pd.concat([st.session_state.fuel_reports, new_row], ignore_index=True)

        st.session_state.last_result = {
            "vessel": vessel, "mode": mode, "rpm": rpm, "engines": engines,
            "actual": actual, "baseline": baseline, "baseline_n": len(match),
        }
        st.success("Daily Report tersimpan dan dianalisis.")

# ---------- RESULT ----------
st.header("2. 📊 Hasil Hari Ini")
res = st.session_state.get("last_result")
if not res:
    st.info("Masukkan Daily Report KKM di atas untuk mendapatkan hasil.")
else:
    actual = res["actual"]
    baseline = res["baseline"]
    baseline_n = res["baseline_n"]
    x1, x2, x3, x4 = st.columns(4)
    x1.metric("Actual Consumption", f"{actual:.3f} MT/day")
    x2.metric("RPM", f"{res['rpm']}")
    x3.metric("Engine Running", f"{res['engines']} ME")
    if baseline is None or pd.isna(baseline) or baseline_n < 3:
        x4.metric("Status", "⚪ DATA NEEDED")
        st.warning(f"Baseline belum cukup: baru ada {baseline_n} laporan pembanding sebelumnya untuk kombinasi kapal/mode/RPM/engine ini. Minimum 3 laporan disarankan sebelum menilai deviasi.")
    else:
        deviation = ((actual - baseline) / baseline * 100) if baseline > 0 else 0.0
        excess = actual - baseline
        if deviation <= 5:
            status = "🟢 NORMAL"
            st.success("Konsumsi berada dalam +5% dari baseline historis yang sebanding.")
        elif deviation <= 10:
            status = "🟠 ATTENTION"
            st.warning("Konsumsi lebih tinggi dari baseline. Verifikasi kondisi operasi dan data ROB.")
        else:
            status = "🔴 HIGH"
            st.error("Konsumsi >10% di atas baseline historis. Perlu review dan verifikasi.")
        x4.metric("Status", status)
        y1, y2, y3 = st.columns(3)
        y1.metric("Historical Baseline", f"{baseline:.3f} MT/day", help=f"Rata-rata {baseline_n} laporan sebelumnya dengan kapal, mode, RPM dan jumlah engine yang sama.")
        y2.metric("Deviation", f"{deviation:+.1f}%")
        y3.metric("Excess / Saving", f"{excess:+.3f} MT/day")

# ---------- RPM PROFILE ----------
st.header("3. ⚙️ RPM → Pemakaian BBM")
st.caption(f"Kapal: {vessel} | Nilai berasal dari historical Daily Report KKM pada operating mode yang sama: {mode}.")
hist = st.session_state.fuel_reports.copy()
profile_rows = []
for r in RPM_POINTS:
    row = {"RPM": r}
    for eng in [1, 2]:
        if hist.empty:
            vals = pd.Series(dtype=float)
        else:
            subset = hist[
                (hist["Vessel"] == vessel)
                & (hist["Operating Mode"] == mode)
                & (pd.to_numeric(hist["RPM"], errors="coerce") == r)
                & (pd.to_numeric(hist["Main Engines Running"], errors="coerce") == eng)
            ]
            vals = pd.to_numeric(subset["Actual Consumption MT"], errors="coerce").dropna()
        row[f"{eng} Mesin (MT/day)"] = f"{vals.mean():.3f}" if len(vals) else "Belum ada data"
        row[f"Data {eng} Mesin"] = len(vals)
    profile_rows.append(row)
st.dataframe(pd.DataFrame(profile_rows), use_container_width=True, hide_index=True)

# ---------- ACTION ----------
st.header("4. 🎯 Check / Action")
st.markdown(""" Jika konsumsi lebih tinggi dari baseline, verifikasi **ROB & bunker**, **RPM/engine load**, **running hours**, **speed**, **draft/trim**, **weather/current/sea state**, dan **hull/propeller condition**. Status aplikasi adalah decision support; penyebab tidak dinyatakan pasti tanpa data pendukung. """)

# ---------- IMPORT / EXPORT ----------
st.header("5. 📁 Daily Report Import / Export")
left, right = st.columns(2)
with left:
    uploaded = st.file_uploader("Upload historical Daily Report (CSV)", type=["csv"])
    if uploaded is not None:
        try:
            imported = pd.read_csv(uploaded)
            missing = [c for c in COLUMNS if c not in imported.columns]
            if missing:
                st.error("Kolom CSV belum lengkap: " + ", ".join(missing))
            elif st.button("Import CSV ke Historical Database"):
                st.session_state.fuel_reports = pd.concat([st.session_state.fuel_reports, imported[COLUMNS]], ignore_index=True)
                st.success(f"{len(imported)} laporan berhasil diimport.")
                st.rerun()
        except Exception as exc:
            st.error(f"CSV tidak dapat dibaca: {exc}")
with right:
    template = pd.DataFrame(columns=COLUMNS).to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Template Daily Report CSV", template, "kkm_daily_report_template.csv", "text/csv", use_container_width=True)
    data_csv = st.session_state.fuel_reports.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export Historical Data CSV", data_csv, "vessel_fuel_history.csv", "text/csv", use_container_width=True)

if not st.session_state.fuel_reports.empty:
    st.subheader("Historical Daily Reports")
    st.dataframe(st.session_state.fuel_reports.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
else:
    st.info("Belum ada historical Daily Report. Masukkan laporan pertama atau upload CSV.")
# ---------- TERAS HYDRA REAL FUEL INTELLIGENCE ----------
if vessel == "TERAS HYDRA":
    st.header("6. ⚡ TERAS HYDRA — Real Fuel Intelligence")

    st.caption(
        "Analisis konsumsi BBM berdasarkan Daily Progress Report (DPR) "
        "TERAS HYDRA dan historical Daily Report yang tersimpan."
    )

    # Reference operating point confirmed from TERAS HYDRA DPR
    HYDRA_REFERENCE_RPM = 1300

    hydra_hist = st.session_state.fuel_reports.copy()

    if not hydra_hist.empty:
        hydra_hist = hydra_hist[
            hydra_hist["Vessel"].astype(str).str.upper() == "TERAS HYDRA"
        ].copy()

    c1, c2, c3 = st.columns(3)

    c1.metric("Reference RPM", f"{HYDRA_REFERENCE_RPM} RPM")
    c2.metric("Selected RPM", f"{rpm} RPM")
    c3.metric("Main Engines", f"{engines} ME")

    if hydra_hist.empty:
        st.info(
            "Belum ada cukup historical fuel data TERAS HYDRA. "
            "Masukkan Daily Report atau import CSV untuk membangun baseline real."
        )
    else:
        hydra_hist["Actual Consumption MT"] = pd.to_numeric(
            hydra_hist["Actual Consumption MT"], errors="coerce"
        )

        hydra_hist["RPM"] = pd.to_numeric(
            hydra_hist["RPM"], errors="coerce"
        )

        hydra_hist["Main Engines Running"] = pd.to_numeric(
            hydra_hist["Main Engines Running"], errors="coerce"
        )

        reference = hydra_hist[
            (hydra_hist["RPM"] == rpm)
            & (hydra_hist["Main Engines Running"] == engines)
        ]["Actual Consumption MT"].dropna()

        if len(reference) > 0:
            real_baseline = reference.mean()
            actual_now = float(actual)

            deviation_mt = actual_now - real_baseline
            deviation_pct = (
                deviation_mt / real_baseline * 100
                if real_baseline > 0 else 0.0
            )

            a1, a2, a3, a4 = st.columns(4)

            a1.metric(
                "Actual Fuel",
                f"{actual_now:.3f} MT/day"
            )

            a2.metric(
                "Real DPR Baseline",
                f"{real_baseline:.3f} MT/day"
            )

            a3.metric(
                "Deviation",
                f"{deviation_pct:+.1f}%"
            )

            a4.metric(
                "Excess / Saving",
                f"{deviation_mt:+.3f} MT/day"
            )

            if deviation_pct <= 5:
                st.success(
                    "🟢 EFFICIENT — Konsumsi BBM berada dalam batas "
                    "normal terhadap historical baseline."
                )
            elif deviation_pct <= 10:
                st.warning(
                    "🟠 ATTENTION — Konsumsi BBM mulai lebih tinggi "
                    "dari historical baseline."
                )
            else:
                st.error(
                    "🔴 HIGH FUEL CONSUMPTION — Konsumsi BBM lebih dari "
                    "10% di atas historical baseline. Perlu investigasi."
                )

            st.markdown(
                "**Fuel Intelligence Check:** periksa RPM/load engine, "
                "running hours, speed, weather/current, draft/trim, "
                "hull/propeller condition dan akurasi ROB/bunker."
            )

        else:
            st.warning(
                f"Belum tersedia historical baseline TERAS HYDRA untuk "
                f"{rpm} RPM dengan {engines} mesin. "
                "Tambahkan Daily Report pada kondisi operasi yang sama."
            )




st.divider()
st.success("✅ SIMPLE KKM FUEL MONITOR READY — RPM 600–1300 | 1 ME / 2 ME | Historical Baseline | Daily Report")
