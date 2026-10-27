import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import io
from pathlib import Path

st.set_page_config(
    page_title="EcoPulse Energy Dashboard",
    page_icon="🌿",
    layout="wide"
)

st.markdown("""
<style>
.stApp { background-color: #F5FAF6; color: #173B2B; }
[data-testid="stSidebar"] { background-color: #E7F3E9; }
h1, h2, h3 { color: #176B45 !important; }
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #D4E8D8;
    padding: 14px;
    border-radius: 12px;
}
.stDownloadButton button {
    background-color: #176B45;
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.title("🌿 EcoPulse")
st.subheader("Household Energy Consumption Analytics")
st.caption("CA4 Capstone Project | Business Analytics")

REQUIRED_COLUMNS = [
    "Household_ID", "Date", "Energy_Consumption_kWh",
    "Household_Size", "Avg_Temperature_C", "Has_AC",
    "Peak_Hours_Usage_kWh"
]

uploaded_file = st.sidebar.file_uploader(
    "Upload Excel dataset", type=["xlsx"]
)

if uploaded_file is not None:
    raw = pd.read_excel(uploaded_file)
else:
    default_path = Path(__file__).parent / "household_energy_consumption.xlsx"
    if default_path.exists():
        raw = pd.read_excel(default_path)
    else:
        st.info("Upload your Excel file using the sidebar to start.")
        st.stop()

missing_columns = [c for c in REQUIRED_COLUMNS if c not in raw.columns]

if missing_columns:
    st.error("Missing required columns: " + ", ".join(missing_columns))
    st.stop()

st.success(f"Dataset loaded: {len(raw):,} original rows")

# DATA CLEANING
df = raw.copy()

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

numeric_columns = [
    "Energy_Consumption_kWh",
    "Household_Size",
    "Avg_Temperature_C",
    "Peak_Hours_Usage_kWh"
]

for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")

df["Has_AC"] = df["Has_AC"].astype("string").str.strip().str.title()

original_rows = len(df)
original_missing = int(df[REQUIRED_COLUMNS].isna().sum().sum())
original_duplicates = int(df.duplicated().sum())

df = df.dropna(subset=REQUIRED_COLUMNS).copy()
rows_after_missing = len(df)

df = df.drop_duplicates().copy()
rows_after_duplicates = len(df)

invalid_mask = (
    (df["Energy_Consumption_kWh"] < 0)
    | (df["Peak_Hours_Usage_kWh"] < 0)
    | (df["Household_Size"] <= 0)
)

invalid_rows = int(invalid_mask.sum())
df = df.loc[~invalid_mask].copy()

if df.empty:
    st.error("No valid records remain after cleaning.")
    st.stop()

# SIDEBAR FILTERS
st.sidebar.markdown("---")
st.sidebar.header("Dashboard Filters")

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Select date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

ac_options = sorted(df["Has_AC"].dropna().unique().tolist())
selected_ac = st.sidebar.multiselect(
    "AC availability",
    ac_options,
    default=ac_options
)

size_options = sorted(df["Household_Size"].dropna().unique().tolist())
selected_sizes = st.sidebar.multiselect(
    "Household size",
    size_options,
    default=size_options
)

if isinstance(date_range, (tuple, list)):
    if len(date_range) == 2:
        start_date, end_date = date_range
    elif len(date_range) == 1:
        start_date = end_date = date_range[0]
    else:
        start_date, end_date = min_date, max_date
else:
    start_date = end_date = date_range

filtered = df[
    df["Date"].dt.date.between(start_date, end_date)
    & df["Has_AC"].isin(selected_ac)
    & df["Household_Size"].isin(selected_sizes)
].copy()

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()

# KPI CARDS
st.markdown("## 📊 Energy Overview")

total_energy = filtered["Energy_Consumption_kWh"].sum()
average_energy = filtered["Energy_Consumption_kWh"].mean()
average_peak = filtered["Peak_Hours_Usage_kWh"].mean()
unique_households = filtered["Household_ID"].nunique()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Energy", f"{total_energy:,.2f} kWh")
col2.metric("Average per Record", f"{average_energy:,.2f} kWh")
col3.metric("Average Peak Usage", f"{average_peak:,.2f} kWh")
col4.metric("Unique Household IDs", f"{unique_households:,}")

# ENERGY CHARTS
st.markdown("## 📈 Consumption Analysis")

daily = (
    filtered.groupby(filtered["Date"].dt.date)["Energy_Consumption_kWh"]
    .sum()
    .reset_index()
)
daily.columns = ["Date", "Total Energy (kWh)"]

fig_daily = px.line(
    daily,
    x="Date",
    y="Total Energy (kWh)",
    markers=True,
    title="Daily Energy Consumption",
    color_discrete_sequence=["#218653"]
)
st.plotly_chart(fig_daily, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    ac_data = (
        filtered.groupby("Has_AC")["Energy_Consumption_kWh"]
        .mean()
        .reset_index()
    )
    ac_data.columns = ["Has AC?", "Average Energy (kWh)"]

    fig_ac = px.bar(
        ac_data,
        x="Has AC?",
        y="Average Energy (kWh)",
        title="Average Consumption by AC Availability",
        color_discrete_sequence=["#218653"]
    )
    st.plotly_chart(fig_ac, use_container_width=True)

with col2:
    size_data = (
        filtered.groupby("Household_Size")["Energy_Consumption_kWh"]
        .mean()
        .reset_index()
    )
    size_data.columns = ["Household Size", "Average Energy (kWh)"]

    fig_size = px.bar(
        size_data,
        x="Household Size",
        y="Average Energy (kWh)",
        title="Average Consumption by Household Size",
        color_discrete_sequence=["#218653"]
    )
    st.plotly_chart(fig_size, use_container_width=True)

fig_temp = px.scatter(
    filtered,
    x="Avg_Temperature_C",
    y="Energy_Consumption_kWh",
    color="Has_AC",
    title="Temperature vs Energy Consumption"
)
st.plotly_chart(fig_temp, use_container_width=True)

st.markdown("### Correlation Heatmap")

correlation_columns = [
    "Energy_Consumption_kWh",
    "Household_Size",
    "Avg_Temperature_C",
    "Peak_Hours_Usage_kWh"
]

correlation = filtered[correlation_columns].corr()

fig_corr = px.imshow(
    correlation,
    text_auto=".2f",
    color_continuous_scale="Greens",
    zmin=-1,
    zmax=1,
    title="Correlation Between Numeric Variables"
)
st.plotly_chart(fig_corr, use_container_width=True)

# AUTOMATIC BUSINESS INSIGHTS
st.markdown("## 💡 Automatic Business Insights")

st.info(
    f"Total recorded energy consumption for the selected data is "
    f"{total_energy:,.2f} kWh."
)

st.info(
    f"Average consumption per record is {average_energy:,.2f} kWh."
)

ac_means = filtered.groupby("Has_AC")["Energy_Consumption_kWh"].mean()

if len(ac_means) >= 2:
    highest_ac = ac_means.idxmax()
    lowest_ac = ac_means.idxmin()

    st.write(
        f"The {highest_ac} group has the higher observed average "
        f"consumption: {ac_means[highest_ac]:,.2f} kWh per record."
    )

    st.write(
        f"The {lowest_ac} group has the lower observed average "
        f"consumption: {ac_means[lowest_ac]:,.2f} kWh per record."
    )

size_means = filtered.groupby("Household_Size")["Energy_Consumption_kWh"].mean()

if len(size_means) >= 2:
    small_size = size_means.index.min()
    large_size = size_means.index.max()

    st.write(
        f"Household size {small_size} has an average of "
        f"{size_means.loc[small_size]:,.2f} kWh per record, while "
        f"size {large_size} has an average of "
        f"{size_means.loc[large_size]:,.2f} kWh per record."
    )

st.caption(
    "These insights describe observed data and do not establish "
    "that AC, temperature or household size causes the differences."
)

# HIGH-CONSUMPTION ALERTS
st.markdown("## 🚨 High-Consumption Alerts")

method = st.selectbox(
    "Alert threshold method",
    ["95th percentile", "Mean + 2 standard deviations"]
)

energy = filtered["Energy_Consumption_kWh"]

if method == "95th percentile":
    threshold = energy.quantile(0.95)
else:
    threshold = energy.mean() + 2 * energy.std(ddof=0)

alerts = filtered[energy >= threshold].copy()

st.metric("Alert Threshold", f"{threshold:,.2f} kWh")
st.metric("Flagged Records", f"{len(alerts):,}")

if not alerts.empty:
    st.dataframe(
        alerts.sort_values("Energy_Consumption_kWh", ascending=False),
        use_container_width=True
    )

    st.download_button(
        "Download High-Consumption Alerts",
        alerts.to_csv(index=False).encode("utf-8"),
        file_name="high_consumption_alerts.csv",
        mime="text/csv"
    )
else:
    st.success("No records were flagged.")

st.caption(
    "High consumption is not automatically an error or evidence of waste."
)

# ENERGY-SAVING CALCULATOR
st.markdown("## 🌱 Energy-Saving Calculator")

reduction = st.slider(
    "Assumed reduction in consumption (%)",
    min_value=0,
    max_value=50,
    value=10,
    step=5
)

estimated_saving = total_energy * reduction / 100
remaining_energy = total_energy - estimated_saving

col1, col2, col3 = st.columns(3)

col1.metric("Current Energy", f"{total_energy:,.2f} kWh")
col2.metric("Estimated Saving", f"{estimated_saving:,.2f} kWh")
col3.metric("Energy After Scenario", f"{remaining_energy:,.2f} kWh")

scenario = pd.DataFrame({
    "Scenario": ["Current", "After assumed reduction"],
    "Energy (kWh)": [total_energy, remaining_energy]
})

fig_saving = px.bar(
    scenario,
    x="Scenario",
    y="Energy (kWh)",
    title="Current vs Hypothetical Energy Consumption",
    color_discrete_sequence=["#A5D6A7", "#218653"]
)
st.plotly_chart(fig_saving, use_container_width=True)

tariff = st.number_input(
    "Verified electricity tariff per kWh (optional)",
    min_value=0.0,
    value=0.0,
    step=0.5
)

if tariff > 0:
    st.metric(
        "Estimated Cost Saving",
        f"{estimated_saving * tariff:,.2f} currency units"
    )
else:
    st.info("Enter a verified tariff to calculate an estimated cost saving.")

st.download_button(
    "Download Savings Scenario",
    scenario.to_csv(index=False).encode("utf-8"),
    file_name="energy_savings_scenario.csv",
    mime="text/csv"
)

# DATA QUALITY REPORT
st.markdown("## 🧹 Data Quality Report")

quality = pd.DataFrame({
    "Column": REQUIRED_COLUMNS,
    "Missing Values in Original Data": [
        int(raw[col].isna().sum()) for col in REQUIRED_COLUMNS
    ],
    "Unique Values in Original Data": [
        int(raw[col].nunique(dropna=True)) for col in REQUIRED_COLUMNS
    ]
})

col1, col2, col3 = st.columns(3)

col1.metric("Original Rows", f"{original_rows:,}")
col2.metric("Original Missing Cells", f"{original_missing:,}")
col3.metric("Original Duplicate Rows", f"{original_duplicates:,}")

st.dataframe(quality, use_container_width=True)

cleaning_report = pd.DataFrame({
    "Cleaning Stage": [
        "Original rows",
        "After missing-value removal",
        "After duplicate removal",
        "Invalid rows removed",
        "Final cleaned rows"
    ],
    "Rows": [
        original_rows,
        rows_after_missing,
        rows_after_duplicates,
        invalid_rows,
        len(df)
    ]
})

st.dataframe(cleaning_report, use_container_width=True)

st.download_button(
    "Download Data Quality Report",
    quality.to_csv(index=False).encode("utf-8"),
    file_name="data_quality_report.csv",
    mime="text/csv"
)

# SIMPLE LINEAR TREND FORECAST
st.markdown("## 🔮 Exploratory Consumption Forecast")

forecast_days = st.slider(
    "Forecast days",
    min_value=1,
    max_value=7,
    value=3
)

daily_energy = (
    filtered.groupby(filtered["Date"].dt.date)["Energy_Consumption_kWh"]
    .sum()
    .sort_index()
)

if len(daily_energy) < 3:
    st.warning(
        "At least three distinct dates are needed for this simple forecast."
    )
else:
    y = daily_energy.to_numpy(dtype=float)
    x = np.arange(len(y), dtype=float)

    slope, intercept = np.polyfit(x, y, 1)

    future_x = np.arange(
        len(y), len(y) + forecast_days, dtype=float
    )

    predictions = np.maximum(slope * future_x + intercept, 0)

    future_dates = pd.date_range(
        start=pd.Timestamp(daily_energy.index[-1]) + pd.Timedelta(days=1),
        periods=forecast_days,
        freq="D"
    )

    history = pd.DataFrame({
        "Date": pd.to_datetime(daily_energy.index),
        "Energy (kWh)": y,
        "Type": "Observed"
    })

    future = pd.DataFrame({
        "Date": future_dates,
        "Energy (kWh)": predictions,
        "Type": "Exploratory forecast"
    })

    chart_data = pd.concat([history, future], ignore_index=True)

    fig_forecast = px.line(
        chart_data,
        x="Date",
        y="Energy (kWh)",
        color="Type",
        markers=True,
        title="Observed and Forecast Daily Energy"
    )

    st.plotly_chart(fig_forecast, use_container_width=True)

    st.dataframe(future.round(2), use_container_width=True)

    st.download_button(
        "Download Forecast",
        future.to_csv(index=False).encode("utf-8"),
        file_name="energy_forecast.csv",
        mime="text/csv"
    )

st.warning(
    "This is a simple trend demonstration. A short or incomplete date "
    "range can make the forecast unreliable."
)

# DOWNLOAD CENTRE
st.markdown("## 📥 Download Centre")

st.download_button(
    "Download Filtered Data",
    filtered.to_csv(index=False).encode("utf-8"),
    file_name="filtered_household_energy.csv",
    mime="text/csv"
)

business_summary = filtered.groupby("Has_AC").agg(
    Record_Count=("Household_ID", "count"),
    Unique_Households=("Household_ID", "nunique"),
    Average_Energy_kWh=("Energy_Consumption_kWh", "mean"),
    Total_Energy_kWh=("Energy_Consumption_kWh", "sum"),
    Average_Peak_Usage_kWh=("Peak_Hours_Usage_kWh", "mean")
).reset_index().round(2)

st.dataframe(business_summary, use_container_width=True)

st.download_button(
    "Download Business Summary",
    business_summary.to_csv(index=False).encode("utf-8"),
    file_name="energy_business_summary.csv",
    mime="text/csv"
)

st.caption("EcoPulse | Household Energy Consumption | CA4 Capstone")
