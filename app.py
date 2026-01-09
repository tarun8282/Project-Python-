import json
import pandas as pd
import plotly.express as px
import streamlit as st

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="COVID-19 India Dashboard",
    layout="wide"
)

st.title("🦠 COVID-19 India District-wise Dashboard")

# -------------------- LOAD DATA --------------------
@st.cache_data
def load_data():
    with open("india.geojson", "r") as f:
        geojson = json.load(f)

    df = pd.read_csv("districts.csv")
    return geojson, df


india_districts, df = load_data()

# -------------------- PREPROCESS --------------------
# Build district -> dt_code map SAFELY
district_code_map = {}

for feature in india_districts["features"]:
    props = feature.get("properties", {})

    district = props.get("district")
    dt_code = props.get("dt_code")

    if district and dt_code:
        district_code_map[district.strip()] = dt_code
        feature["id"] = dt_code


# Clean CSV
df["District"] = df["District"].str.strip()
df["State"] = df["State"].str.strip()
df["dt_code"] = df["District"].map(district_code_map)

# Convert Date
df["Date"] = pd.to_datetime(df["Date"])

# Numeric columns
metrics = ["Confirmed", "Recovered", "Deceased", "Other", "Tested"]
df[metrics] = df[metrics].apply(pd.to_numeric, errors="coerce").fillna(0)

# -------------------- SIDEBAR CONTROLS --------------------
st.sidebar.header("🔎 Filters")

# Date picker
selected_date = st.sidebar.date_input(
    "Select Date",
    min_value=df["Date"].min().date(),
    max_value=df["Date"].max().date(),
    value=df["Date"].max().date()
)

# State selector
states = ["All"] + sorted(df["State"].unique().tolist())
selected_state = st.sidebar.selectbox("Select State", states)

# Metric selector
selected_metric = st.sidebar.selectbox(
    "Select Metric",
    metrics
)

# -------------------- FILTER DATA --------------------
filtered_df = df[df["Date"] == pd.to_datetime(selected_date)]

if selected_state != "All":
    filtered_df = filtered_df[filtered_df["State"] == selected_state]

# -------------------- SUMMARY METRICS --------------------
st.subheader(f"📅 Data for {selected_date}")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Confirmed", int(filtered_df["Confirmed"].sum()))
col2.metric("Recovered", int(filtered_df["Recovered"].sum()))
col3.metric("Deceased", int(filtered_df["Deceased"].sum()))
col4.metric("Tested", int(filtered_df["Tested"].sum()))

# -------------------- CHOROPLETH MAP --------------------
fig = px.choropleth(
    filtered_df,
    geojson=india_districts,
    locations="dt_code",
    color=selected_metric,
    hover_name="District",
    hover_data=["State", "Confirmed", "Recovered", "Deceased", "Tested"],
    featureidkey="id",
    color_continuous_scale="Reds",
    title=f"{selected_metric} Cases by District"
)

fig.update_geos(
    fitbounds="locations",
    visible=False
)

fig.update_layout(
    margin={"r":0,"t":50,"l":0,"b":0}
)



# -------------------- SEVERITY CLASSIFICATION --------------------
def severity_level(confirmed):
    if confirmed >= 10000:
        return "🔴 Severe"
    elif confirmed >= 5000:
        return "🟠 High"
    else:
        return "🟡 Moderate"

severity_df = filtered_df.copy()
severity_df["Severity"] = severity_df["Confirmed"].apply(severity_level)

# Custom order for sorting
severity_order = {"🔴 Severe": 0, "🟠 High": 1, "🟡 Moderate": 2}
severity_df["severity_rank"] = severity_df["Severity"].map(severity_order)

# Sort by severity then confirmed cases
severity_df = severity_df.sort_values(
    ["severity_rank", "Confirmed"],
    ascending=[True, False]
)

# Keep only required columns
alert_table = severity_df[[
    "District",
    "State",
    "Confirmed",
    "Severity"
]].head(10)





st.plotly_chart(fig, use_container_width=True)

# -------------------- FOOTER --------------------
st.markdown("---")
st.caption("Data Source: COVID-19 India | Visualization using Plotly & Streamlit")
