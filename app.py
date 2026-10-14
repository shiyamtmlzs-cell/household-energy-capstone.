import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="Household Energy Analysis",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Household Energy Consumption Dashboard")
st.write("CA4 Capstone Project | Business Analytics")

# Load the dataset
uploaded_file = st.sidebar.file_uploader(
    "Upload household energy Excel file",
    type=["xlsx"]
)

@st.cache_data
def load_data(file):
    if file is None:
        path = Path(__file__).parent / "household_energy_consumption.xlsx"
        data = pd.read_excel(path)
    else:
        data = pd.read_excel(file)

    data["Date"] = pd.to_datetime(
        data["Date"], errors="coerce"
    )

    numeric_columns = [
        "Energy_Consumption_kWh",
        "Household_Size",
        "Avg_Temperature_C",
        "Peak_Hours_Usage_kWh"
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column], errors="coerce"
        )

    data["Has_AC"] = (
        data["Has_AC"].astype("string").str.strip().str.title()
    )

    data = data.dropna().drop_duplicates()

    data = data[
        (data["Energy_Consumption_kWh"] >= 0) &
        (data["Peak_Hours_Usage_kWh"] >= 0) &
        (data["Household_Size"] > 0)
    ].copy()

    return data

try:
    df = load_data(uploaded_file)
except Exception as error:
    st.error(f"Dataset loading failed: {error}")
    st.stop()

if df.empty:
    st.error("No usable data is available.")
    st.stop()

# Filters
st.sidebar.header("Filters")

dates = st.sidebar.date_input(
    "Select date range",
    value=(df["Date"].min().date(),
           df["Date"].max().date()),
    min_value=df["Date"].min().date(),
    max_value=df["Date"].max().date()
)

ac_options = sorted(df["Has_AC"].unique().tolist())

selected_ac = st.sidebar.multiselect(
    "AC availability",
    ac_options,
    default=ac_options
)

sizes = sorted(df["Household_Size"].unique().tolist())

selected_sizes = st.sidebar.multiselect(
    "Household size",
    sizes,
    default=sizes
)

if isinstance(dates, (tuple, list)) and len(dates) == 2:
    start_date, end_date = dates
else:
    start_date = end_date = dates

filtered = df[
    df["Date"].dt.date.between(start_date, end_date)
    & df["Has_AC"].isin(selected_ac)
    & df["Household_Size"].isin(selected_sizes)
].copy()

if filtered.empty:
    st.warning("No records match your filters.")
    st.stop()

# KPI cards
total = filtered["Energy_Consumption_kWh"].sum()
average = filtered["Energy_Consumption_kWh"].mean()
peak = filtered["Peak_Hours_Usage_kWh"].mean()
households = filtered["Household_ID"].nunique()

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Energy (kWh)", f"{total:,.2f}")
c2.metric("Average Energy (kWh)", f"{average:,.2f}")
c3.metric("Average Peak Usage (kWh)", f"{peak:,.2f}")
c4.metric("Unique Household IDs", f"{households:,}")

# Daily trend
st.subheader("1. Daily Energy Consumption")

daily = (
    filtered.groupby(filtered["Date"].dt.date)
    ["Energy_Consumption_kWh"].sum()
    .reset_index()
)

daily.columns = ["Date", "Total Energy (kWh)"]

fig = px.line(
    daily,
    x="Date",
    y="Total Energy (kWh)",
    markers=True,
    title="Total Recorded Energy by Date"
)

st.plotly_chart(fig, use_container_width=True)

# AC comparison
st.subheader("2. Energy Consumption by AC Availability")

ac_data = (
    filtered.groupby("Has_AC")["Energy_Consumption_kWh"]
    .mean().reset_index()
)

ac_data.columns = ["Has AC?", "Average Energy (kWh)"]

fig = px.bar(
    ac_data,
    x="Has AC?",
    y="Average Energy (kWh)",
    color="Has AC?",
    title="Average Consumption: AC vs Non-AC"
)

st.plotly_chart(fig, use_container_width=True)

# Household size
st.subheader("3. Household Size Analysis")

size_data = (
    filtered.groupby("Household_Size")
    ["Energy_Consumption_kWh"].mean()
    .reset_index()
)

size_data.columns = ["Household Size", "Average Energy (kWh)"]

fig = px.bar(
    size_data,
    x="Household Size",
    y="Average Energy (kWh)",
    title="Average Consumption by Household Size"
)

st.plotly_chart(fig, use_container_width=True)

# Temperature relationship
st.subheader("4. Temperature and Energy Consumption")

fig = px.scatter(
    filtered,
    x="Avg_Temperature_C",
    y="Energy_Consumption_kWh",
    color="Has_AC",
    opacity=0.5,
    title="Temperature vs Energy Consumption",
    labels={
        "Avg_Temperature_C": "Temperature (°C)",
        "Energy_Consumption_kWh": "Energy (kWh)"
    }
)

st.plotly_chart(fig, use_container_width=True)

# Peak-hour analysis
st.subheader("5. Peak-Hour Usage")

fig = px.scatter(
    filtered,
    x="Peak_Hours_Usage_kWh",
    y="Energy_Consumption_kWh",
    color="Has_AC",
    opacity=0.5,
    title="Peak Usage vs Total Energy"
)

st.plotly_chart(fig, use_container_width=True)

# Summary and download
st.subheader("6. Summary Table")

summary = filtered.groupby("Has_AC").agg(
    Records=("Household_ID", "count"),
    Average_Energy=("Energy_Consumption_kWh", "mean"),
    Average_Peak_Usage=("Peak_Hours_Usage_kWh", "mean")
).round(2)

st.dataframe(summary, use_container_width=True)

st.download_button(
    "Download Filtered Data",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="filtered_energy_data.csv",
    mime="text/csv"
)

st.caption(
    "Results describe patterns in the supplied dataset; "
    "they do not establish causation."
)
