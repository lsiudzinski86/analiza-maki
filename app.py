import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Analiza Mąki", layout="wide")

st.title("📊 Monitoring jakości mąki")

file = st.file_uploader("Wgraj plik Excel", type=["xlsx"])

if file:

    df = pd.read_excel(file)

    # ===== PARSOWANIE =====
    def get_prefix(name):
        if pd.isna(name):
            return "UNKNOWN"
        return str(name).split("_")[0]

    df["PREFIX"] = df["Nazwa próbki"].apply(get_prefix)

    mills = ["PZZ", "SM", "SZ", "JE", "KA", "PM", "GM"]
    blends = ["CN", "CS", "550"]

    def classify(x):
        return "MŁYN" if x in mills else "BLEND" if x in blends else "INNE"

    df["TYP"] = df["PREFIX"].apply(classify)

    df["DATA"] = pd.to_datetime(df["Data badania Excel"], errors="coerce")
    df["TYDZIEŃ"] = df["DATA"].dt.to_period("W").astype(str)

    # ===== FILTR DATY =====
    st.sidebar.header("📅 Zakres dat")

    min_date = df["DATA"].min()
    max_date = df["DATA"].max()

    date_range = st.sidebar.date_input("Zakres", [min_date, max_date])

    if len(date_range) == 2:
        df = df[
            (df["DATA"] >= pd.to_datetime(date_range[0])) &
            (df["DATA"] <= pd.to_datetime(date_range[1]))
        ]

    # ===== PARAMETRY =====
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    parametry = [c for c in numeric_cols if c != "Lp."]

    parametr = st.selectbox("Parametr główny", parametry)

    # ===== TREND =====
    st.subheader("📈 Trend")

    trend_df = df.groupby("TYDZIEŃ")[parametr].mean().reset_index()

    if not trend_df.empty:
        st.line_chart(trend_df.set_index("TYDZIEŃ"))

    # ===== STABILNOŚĆ =====
    st.subheader("📊 Stabilność")

    stats = df.groupby("PREFIX")[parametr].agg(["mean", "std"]).reset_index()
    stats["CV %"] = stats["std"] / stats["mean"] * 100
    st.dataframe(stats)

    # =============================
    # ✅ SPECYFIKACJA – WRACA
    # =============================

    st.subheader("⚙️ Specyfikacja")

    spec_df = pd.DataFrame({
        "Młyn": df["PREFIX"].unique(),
        "Min": [None]*len(df["PREFIX"].unique()),
        "Max": [None]*len(df["PREFIX"].unique())
    })

    edited_spec = st.data_editor(spec_df)

    st.subheader("✅ Walidacja")

    results = []

    for _, row in edited_spec.iterrows():
        mill = row["Młyn"]
        min_val = row["Min"]
        max_val = row["Max"]

        if pd.notna(min_val) and pd.notna(max_val):

            temp = df[df["PREFIX"] == mill]

            poza = ((temp[parametr] < min_val) | (temp[parametr] > max_val)).sum()
            total = len(temp)

            results.append({
                "Młyn": mill,
                "% poza spec": round(poza / total * 100, 1)
            })

    if results:
        st.dataframe(pd.DataFrame(results))

    # =============================
    # 🔥 REKOMENDACJA BLENDU
    # =============================

    st.subheader("⚙️ Rekomendacja blendu")

    blend_df = df[df["TYP"] == "BLEND"]
    mill_df = df[df["TYP"] == "MŁYN"]

    if not blend_df.empty and not mill_df.empty:

        blend_mean = blend_df[parametr].mean()

        mill_avg = mill_df.groupby("PREFIX")[parametr].mean().reset_index()
        mill_avg["Różnica"] = mill_avg[parametr] - blend_mean

        st.dataframe(mill_avg)

        for _, row in mill_avg.iterrows():
            if row["Różnica"] > 0:
                st.success(f"{row['PREFIX']} podnosi {parametr}")
            else:
                st.warning(f"{row['PREFIX']} obniża {parametr}")

    # =============================
    # 🔮 PREDYKCJA
    # =============================

    st.subheader("🔮 Predykcja")

    if len(trend_df) > 3:

        y = trend_df[parametr].values
        trend = np.polyfit(range(len(y)), y, 1)[0]

        if trend < 0:
            st.warning("Trend spadkowy – możliwe pogorszenie jakości")
        else:
            st.info("Trend stabilny/wzrostowy")

    # =============================
    # ✅ PROSTA KORELACJA (NOWA)
    # =============================

    st.subheader("🧠 Zależności między parametrami")

    corr = df[parametry].corr()

    ważne = corr[parametr].drop(parametr)

    for p, val in ważne.items():

        if abs(val) > 0.6:

            if val > 0:
                st.write(f"✔ {parametr} rośnie razem z {p}")
            else:
                st.write(f"⚠️ {parametr} rośnie gdy {p} spada")

    # =============================
    # ✅ INTERPRETACJA – POPRAWIONA
    # =============================

    st.subheader("🧠 Interpretacja technologiczna")

    mean_val = df[parametr].mean()

    st.write(f"Średnia wartość: {round(mean_val,2)}")

    if parametr.lower() == "w":
        st.write("➡ Wpływ na objętość i strukturę pieczywa")

    if parametr.lower() == "p/l":
        st.write("➡ Wpływ na rozciągliwość ciasta")

    if parametr.lower() == "skrobia uszkodzona":
        st.write("➡ Wpływ na wodę i kleistość")
