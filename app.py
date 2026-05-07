import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

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

    parametr = st.selectbox("Wybierz parametr", parametry)
    typ = st.radio("Typ danych:", ["MŁYN", "BLEND"])

    data = df[df["TYP"] == typ]

    # ===== TREND =====
    st.subheader("📈 Trend tygodniowy")

    weekly = (
        data.groupby(["TYDZIEŃ"])[parametr]
        .mean()
        .reset_index()
    )

    if not weekly.empty:
        st.line_chart(weekly.set_index("TYDZIEŃ"))

    # ===== STABILNOŚĆ =====
    st.subheader("📊 Stabilność")

    stats = data.groupby("PREFIX")[parametr].agg(["mean", "std"]).reset_index()
    stats["CV %"] = stats["std"] / stats["mean"] * 100
    st.dataframe(stats)

    # =============================
    # 🔥 KORELACJA
    # =============================
    st.subheader("🧠 Korelacja parametrów")

    corr = df[parametry].apply(pd.to_numeric, errors='coerce').corr()

    fig, ax = plt.subplots(figsize=(8,6))
    sns.heatmap(corr, cmap="coolwarm", center=0)
    st.pyplot(fig)

    # =============================
    # 🔥 PREDYKCJA
    # =============================
    st.subheader("🔮 Predykcja problemów")

    if len(weekly) > 3:

        y = weekly[parametr].values

        # prosty trend
        trend = np.polyfit(range(len(y)), y, 1)[0]

        current = y[-1]
        previous = y[-3]

        change = current - previous

        st.write(f"Trend: {round(trend,4)}")

        # ===== REGUŁY =====

        if trend < 0:
            st.warning(f"📉 Trend spadkowy ({parametr}) – możliwe pogorszenie jakości")

        if trend > 0:
            st.info(f"📈 Trend wzrostowy ({parametr})")

        if abs(change) > 0.1 * np.mean(y):
            st.warning("⚠️ Szybka zmiana parametru – ryzyko destabilizacji")

        # konkretne przypadki
        if parametr.lower() == "w" and trend < 0:
            st.error("🔥 Spadek W → ryzyko utraty objętości pieczywa")

        if parametr.lower() == "p/l" and trend > 0:
            st.error("🔥 Wzrost P/L → ryzyko problemów z laminacją")

    # =============================
    # 🔥 NOWA INTERPRETACJA
    # =============================
    st.subheader("🧠 Interpretacja technologiczna")

    if not data.empty:

        mean_val = data[parametr].mean()
        std_val = data[parametr].std()

        st.write(f"Średnia: {round(mean_val,2)}, zmienność: {round(std_val,2)}")

        # OGÓLNA
        if std_val > 0.1 * mean_val:
            st.warning("⚠️ Wysoka zmienność → niestabilny proces")

        # KONKRETNE PARAMETRY
        if parametr.lower() == "w":
            if mean_val < 250:
                st.warning("Niskie W → słaba objętość")
            elif mean_val > 350:
                st.info("Wysokie W → trudniejsze mieszanie / napięte ciasto")

        if parametr.lower() == "p/l":
            if mean_val > 1:
                st.warning("Wysokie P/L → ciasto sztywne (problemy z laminacją)")
            elif mean_val < 0.5:
                st.warning("Niskie P/L → zbyt rozciągliwe ciasto")

        if parametr.lower() == "skrobia uszkodzona":
            if mean_val > 25:
                st.warning("Wysoka skrobia → kleistość miękiszu i problemy z krojeniem")
            elif mean_val < 15:
                st.info("Niska skrobia → niższa wodochłonność")

        if parametr.lower() == "białko":
            if mean_val < 11:
                st.warning("Niskie białko → słaba struktura glutenu")
