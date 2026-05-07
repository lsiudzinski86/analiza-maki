import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Analiza Mąki", layout="wide")

st.title("📊 Monitoring jakości mąki")

# ========= WCZYTANIE DANYCH =========

file = st.file_uploader("Wgraj plik Excel z wynikami", type=["xlsx"])

if file:

    df = pd.read_excel(file)

    # ========= PARSOWANIE =========

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

    # ========= FILTR DATY =========

    st.sidebar.header("📅 Zakres dat")

    min_date = df["DATA"].min()
    max_date = df["DATA"].max()

    date_range = st.sidebar.date_input(
        "Wybierz zakres",
        [min_date, max_date]
    )

    if len(date_range) == 2:
        df = df[
            (df["DATA"] >= pd.to_datetime(date_range[0])) &
            (df["DATA"] <= pd.to_datetime(date_range[1]))
        ]

    # ========= PARAMETRY =========

    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    excluded = ["Lp."]
    parametry = [col for col in numeric_cols if col not in excluded]

    parametr = st.selectbox("Wybierz parametr", parametry)

    typ = st.radio("Wybierz typ danych:", ["MŁYN", "BLEND"])
    data = df[df["TYP"] == typ]

    # ========= TREND =========

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

    # ========= STABILNOŚĆ =========

    st.subheader("📊 Stabilność")

    if not data.empty:

        stats = (
            data.groupby("PREFIX")[parametr]
            .agg(["mean", "std"])
            .reset_index()
        )

        stats["CV %"] = stats["std"] / stats["mean"] * 100
        st.dataframe(stats)

    # ========= SPECYFIKACJA =========

    st.subheader("⚙️ Specyfikacja dostawców")

    unique_prefix = sorted(data["PREFIX"].dropna().unique())

    default_spec = pd.DataFrame({
        "Młyn": np.repeat(unique_prefix, len(parametry)),
        "Parametr": parametry * len(unique_prefix),
        "Min": [None]*(len(unique_prefix)*len(parametry)),
        "Max": [None]*(len(unique_prefix)*len(parametry))
    })

    # ========= WCZYTYWANIE SPECYFIKACJI =========

    uploaded_spec = st.file_uploader(
        "📂 Wczytaj specyfikację (CSV lub Excel)",
        type=["csv", "xlsx"]
    )

    if uploaded_spec:

        if uploaded_spec.name.endswith(".xlsx"):
            spec_df = pd.read_excel(uploaded_spec)

        else:
            try:
                spec_df = pd.read_csv(uploaded_spec, sep=";")
            except:
                spec_df = pd.read_csv(uploaded_spec, sep=",")

        # czyszczenie typów
        spec_df["Min"] = pd.to_numeric(spec_df["Min"], errors="coerce")
        spec_df["Max"] = pd.to_numeric(spec_df["Max"], errors="coerce")

    else:
        spec_df = default_spec

    # ========= EDYTOR =========

    edited_spec = st.data_editor(spec_df, num_rows="dynamic")

    # ========= ZAPIS =========

    st.subheader("💾 Zapis specyfikacji")

    col1, col2 = st.columns(2)

    # CSV
    csv = edited_spec.to_csv(index=False).encode("utf-8")

    col1.download_button(
        label="💾 Pobierz CSV",
        data=csv,
        file_name="specyfikacja.csv",
        mime="text/csv"
    )

    # Excel
    from io import BytesIO
    buffer = BytesIO()
    edited_spec.to_excel(buffer, index=False)
    buffer.seek(0)

    col2.download_button(
        label="💾 Pobierz Excel",
        data=buffer,
        file_name="specyfikacja.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ========= WALIDACJA =========

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

    # ========= ALARMY =========

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

    # ========= INTERPRETACJA =========

    st.subheader("🧠 Interpretacja technologiczna")

    if parametr == "W" and data[parametr].mean() < 250:
        st.warning("Niskie W → ryzyko słabej objętości")

    if parametr == "P/L" and data[parametr].mean() > 1:
        st.warning("Wysokie P/L → ciasto sztywne")

    if parametr == "Białko" and data[parametr].mean() < 11:
        st.warning("Niskie białko → słaba struktura glutenu")

    if parametr == "Skrobia uszkodzona" and data[parametr].mean() > 25:
        st.warning("Wysoka skrobia → kleistość miękiszu")
