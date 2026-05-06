import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Analiza Mąki", layout="wide")

st.title("📊 Monitoring jakości mąki")

# ===== Upload =====
file = st.file_uploader("Wgraj plik Excel", type=["xlsx"])

if file:

    df = pd.read_excel(file, engine="openpyxl")

    # ===== PARSOWANIE =====

    def get_prefix(name):
        if pd.isna(name):
            return "UNKNOWN"
        return str(name).split("_")[0]

    df["PREFIX"] = df["Nazwa próbki"].apply(get_prefix)

    # klasyfikacja
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

    # daty
    df["DATA"] = pd.to_datetime(df["Data badania Excel"])
    df["TYDZIEŃ"] = df["DATA"].dt.to_period("W").astype(str)

    # ===== WYBÓR PARAMETRU =====

    parametry = [
        "Białko", "Popiół", "Wilgotność", "Gluten Ilość",
        "Skrobia uszkodzona", "Wodochłonność", "W", "P/L"
    ]

    parametr = st.selectbox("Wybierz parametr", parametry)

    # ===== FILTRY =====

    typ = st.radio("Wybierz typ danych:", ["MŁYN", "BLEND"])

    data = df[df["TYP"] == typ]

    # ===== ANALIZA =====

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

    # ===== SPECYFIKACJE =====

    st.subheader("⚙️ Walidacja specyfikacji")

    min_val = st.number_input("Min", value=0.0)
    max_val = st.number_input("Max", value=100.0)

    data["STATUS"] = data[parametr].apply(
        lambda x: "OK" if min_val <= x <= max_val else "POZA SPEC"
    )

    st.write("📌 Wyniki")

    st.dataframe(data[["PREFIX", "DATA", parametr, "STATUS"]])

    st.subheader("⚠️ Alarmy")

    alarms = data[data["STATUS"] == "POZA SPEC"]

    st.dataframe(alarms)

    # ===== KOMENTARZE TECHNOLOGICZNE =====

    st.subheader("🧠 Interpretacja")

    if parametr == "W" and data[parametr].mean() < 250:
        st.warning("Niskie W → ryzyko słabej objętości i struktury")

    if parametr == "P/L" and data[parametr].mean() > 1:
        st.warning("Wysokie P/L → ciasto sztywne, trudne w obróbce")

    if parametr == "Białko" and data[parametr].mean() < 11:
        st.warning("Niskie białko → słaba struktura glutenu")

    if parametr == "Skrobia uszkodzona" and data[parametr].mean() > 25:
        st.warning("Wysoka skrobia → ryzyko kleistości miękiszu")
