import streamlit as st
import pandas as pd
import numpy as np

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
        if x in mills:
            return "MŁYN"
        elif x in blends:
            return "BLEND"
        else:
            return "INNE"

    df["TYP"] = df["PREFIX"].apply(classify)

    df["DATA"] = pd.to_datetime(df["Data badania Excel"])
    df["TYDZIEŃ"] = df["DATA"].dt.to_period("W").astype(str)

    # ===== FILTR DATY =====

    st.sidebar.header("📅 Zakres dat")

    min_date = df["DATA"].min()
    max_date = df["DATA"].max()

    date_range = st.sidebar.date_input(
        "Wybierz zakres",
        [min_date, max_date]
    )

    df = df[(df["DATA"] >= pd.to_datetime(date_range[0])) &
            (df["DATA"] <= pd.to_datetime(date_range[1]))]

    # ===== AUTOMATYCZNE PARAMETRY =====

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()

    # usuwamy kolumny techniczne
    excluded = ["Lp."]
    parametry = [col for col in numeric_cols if col not in excluded]

    parametr = st.selectbox("Wybierz parametr", parametry)

    # ===== WYBÓR TYP =====

    typ = st.radio("Wybierz typ danych:", ["MŁYN", "BLEND"])

    data = df[df["TYP"] == typ]

    # ===== TREND =====

    st.subheader("📈 Trend tygodniowy")

    weekly = (
        data.groupby(["TYDZIEŃ", "PREFIX"])[parametr]
        .agg(["mean", "std"])
        .reset_index()
    )

    st.line_chart(weekly.pivot(index="TYDZIEŃ", columns="PREFIX", values="mean"))

    # ===== STABILNOŚĆ =====

    st.subheader("📊 Stabilność")

    stats = (
        data.groupby("PREFIX")[parametr]
        .agg(["mean", "std"])
        .reset_index()
    )

    stats["CV %"] = stats["std"] / stats["mean"] * 100

    st.dataframe(stats)

    # ===== SPECYFIKACJA WIELOPARAMETROWA =====

    st.subheader("⚙️ Specyfikacja dostawcy")

    spec_df = pd.DataFrame({
        "Parametr": parametry,
        "Min": [None]*len(parametry),
        "Max": [None]*len(parametry)
    })

    edited_spec = st.data_editor(spec_df, num_rows="fixed")

    # ===== WALIDACJA =====

    st.subheader("✅ Walidacja")

    results = []

    for _, row in edited_spec.iterrows():
        param = row["Parametr"]
        min_val = row["Min"]
        max_val = row["Max"]

        if pd.notna(min_val) and pd.notna(max_val):

            temp = data.copy()
            temp["STATUS"] = temp[param].apply(
                lambda x: "OK" if min_val <= x <= max_val else "POZA"
            )

            poza = (temp["STATUS"] == "POZA").sum()
            total = len(temp)

            results.append({
                "Parametr": param,
                "% poza spec": round(poza / total * 100, 1) if total > 0 else 0
            })

    if results:
        st.dataframe(pd.DataFrame(results))

    # ===== ALERTY =====

    st.subheader("🚨 Alarmy")

    alerts_list = []

    for _, row in edited_spec.iterrows():
        param = row["Parametr"]
        min_val = row["Min"]
        max_val = row["Max"]

        if pd.notna(min_val) and pd.notna(max_val):

            temp = data[
                (data[param] < min_val) | (data[param] > max_val)
            ]

            if not temp.empty:
                temp = temp[["PREFIX", "DATA", param]]
                temp["Parametr"] = param
                alerts_list.append(temp)

    if alerts_list:
        alerts = pd.concat(alerts_list)
        st.dataframe(alerts)

    # ===== INTERPRETACJA =====

    st.subheader("🧠 Interpretacja technologiczna")

    if parametr == "W" and data[parametr].mean() < 250:
        st.warning("Niskie W → ryzyko słabej objętości i struktury")

    if parametr == "P/L" and data[parametr].mean() > 1:
        st.warning("Wysokie P/L → ciasto sztywne")

    if parametr == "Białko" and data[parametr].mean() < 11:
        st.warning("Niskie białko → słaba struktura glutenu")

    if parametr == "Skrobia uszkodzona" and data[parametr].mean() > 25:
        st.warning("Wysoka skrobia → kleistość miękiszu")
