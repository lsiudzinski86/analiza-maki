import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Analiza Mąki", layout="wide")

st.title("📊 Monitoring jakości mąki")

# ===== WCZYTANIE =====
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
        if x in mills:
            return "MŁYN"
        elif x in blends:
            return "BLEND"
        else:
            return "INNE"

    df["TYP"] = df["PREFIX"].apply(classify)

    df["DATA"] = pd.to_datetime(df["Data badania Excel"], errors="coerce")
    df["TYDZIEŃ"] = df["DATA"].dt.to_period("W").astype(str)

    # ===== FILTR DAT =====
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
    parametry = [col for col in numeric_cols if col != "Lp."]

    parametr = st.selectbox("Wybierz parametr", parametry)
    typ = st.radio("Typ danych:", ["MŁYN", "BLEND"])

    data = df[df["TYP"] == typ]

    # ===== TREND =====
    st.subheader("📈 Trend tygodniowy")

    weekly = (
        data.groupby(["TYDZIEŃ", "PREFIX"])[parametr]
        .mean()
        .reset_index()
    )

    if not weekly.empty:
        st.line_chart(
            weekly.pivot(index="TYDZIEŃ", columns="PREFIX", values=parametr)
        )

    # ===== STABILNOŚĆ =====
    st.subheader("📊 Stabilność")

    if not data.empty:
        stats = (
            data.groupby("PREFIX")[parametr]
            .agg(["mean", "std"])
            .reset_index()
        )

        stats["CV %"] = stats["std"] / stats["mean"] * 100
        st.dataframe(stats)

    # =============================
    # ✅ SPECYFIKACJA (NAJWAŻNIEJSZE)
    # =============================

    st.subheader("⚙️ Specyfikacja dostawców")

    unique_prefix = sorted(data["PREFIX"].dropna().unique())

    spec_df = pd.DataFrame({
        "Młyn": np.repeat(unique_prefix, len(parametry)),
        "Parametr": parametry * len(unique_prefix),
        "Min": [None]*(len(unique_prefix)*len(parametry)),
        "Max": [None]*(len(unique_prefix)*len(parametry))
    })

    edited_spec = st.data_editor(spec_df, num_rows="dynamic")

    # ===== WALIDACJA =====

    st.subheader("✅ Walidacja")

    results = []

    for _, row in edited_spec.iterrows():
        mill = row.get("Młyn")
        param = row.get("Parametr")
        min_val = row.get("Min")
        max_val = row.get("Max")

        if pd.notna(min_val) and pd.notna(max_val):

            temp = data[data["PREFIX"] == mill]

            if param in temp.columns and not temp.empty:

                poza = ((temp[param] < min_val) | (temp[param] > max_val)).sum()
                total = len(temp)

                results.append({
                    "Młyn": mill,
                    "Parametr": param,
                    "% poza spec": round(poza / total * 100, 1)
                })

    if results:
        st.dataframe(pd.DataFrame(results))

    # ===== ALARMY =====

    st.subheader("🚨 Alarmy")

    alerts_list = []

    for _, row in edited_spec.iterrows():
        mill = row.get("Młyn")
        param = row.get("Parametr")
        min_val = row.get("Min")
        max_val = row.get("Max")

        if pd.notna(min_val) and pd.notna(max_val):

            temp = data[
                (data["PREFIX"] == mill) &
                ((data[param] < min_val) | (data[param] > max_val))
            ]

            if not temp.empty:
                temp = temp[["PREFIX", "DATA", param]].copy()
                temp["Parametr"] = param
                alerts_list.append(temp)

    if alerts_list:
        alerts = pd.concat(alerts_list)
        st.dataframe(alerts)

    # =============================
    # ✅ INTERPRETACJA (UPROSZCZONA I CZYTELNA)
    # =============================

    st.subheader("🧠 Interpretacja technologiczna")

    if not data.empty:

        mean_val = data[parametr].mean()
        std_val = data[parametr].std()

        st.write(f"Średnia: {round(mean_val,2)}")
        st.write(f"Zmienność (STD): {round(std_val,2)}")

        if std_val > 0.1 * mean_val:
            st.warning("⚠️ Wysoka zmienność → niestabilny proces")

        if parametr.lower() == "w":
            if mean_val < 250:
                st.warning("Niskie W → słaba objętość pieczywa")
            elif mean_val > 350:
                st.info("Wysokie W → mocne ciasto, trudniejsze mieszanie")

        if parametr.lower() == "p/l":
            if mean_val > 1:
                st.warning("Wysokie P/L → ciasto sztywne (problemy z laminacją)")
            elif mean_val < 0.5:
                st.warning("Niskie P/L → ciasto zbyt rozciągliwe")

        if parametr.lower() == "skrobia uszkodzona":
            if mean_val > 25:
                st.warning("Wysoka skrobia → kleistość miękiszu")
            elif mean_val < 15:
                st.info("Niska skrobia → niższa wodochłonność")

        if parametr.lower() == "białko":
            if mean_val < 11:
                st.warning("Niskie białko → słaby gluten")
