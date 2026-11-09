import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="India Air Quality", layout="wide")

DATA_URL = "https://raw.githubusercontent.com/Saketh1325/india-air-quality/refs/heads/main/air_quality_dashboard.csv"
ORDER = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
COLORS = ["#2e7d32", "#9ccc65", "#fdd835", "#fb8c00", "#e53935", "#6a1b9a"]

@st.cache_data
def load():
    d = pd.read_csv(DATA_URL, parse_dates=["date"])
    d["pm25_cat"] = pd.Categorical(d["pm25_cat"], categories=ORDER, ordered=True)
    return d

df = load()

st.title("Air Quality Across Indian Cities")
st.caption("Source: Kaggle 'India Daily Weather & Air Quality' (Aug 2022 - Oct 2026). "
           "Values may be modeled rather than ground-station readings. "
           "PM2.5 categories follow CPCB breakpoints.")

# ---- Sidebar filters ----
st.sidebar.header("Filters")
all_cities = sorted(df["city"].unique())
default = [c for c in ["Delhi", "Agra", "Kolkata", "Bengaluru", "Chennai"] if c in all_cities]
cities = st.sidebar.multiselect("Cities", all_cities, default=default)
years = st.sidebar.multiselect("Years", sorted(df["year"].unique()), default=[2023, 2024, 2025])
metric_label = st.sidebar.radio("Pollutant", ["PM2.5", "PM10"])
metric = {"PM2.5": "pm2_5_mean", "PM10": "pm10_mean"}[metric_label]
st.sidebar.caption("2022 and 2026 are partial years. Use 2023-2025 for fair comparisons.")

base = df[df["year"].isin(years)]
f = base[base["city"].isin(cities)]

if f.empty:
    st.warning("Select at least one city and one year.")
    st.stop()

# ---- KPIs ----
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Avg {metric_label} (µg/m³)", f"{f[metric].mean():.1f}")
c2.metric("Days Poor or worse (PM2.5)", f"{f['pm25_cat'].isin(ORDER[3:]).mean()*100:.1f}%")
c3.metric("Worst city (selected)", f.groupby("city")[metric].mean().idxmax())
c4.metric("Times over India limit (40)", f"{f['pm2_5_mean'].mean()/40:.1f}x")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Ranking", "Seasonality", "AQI categories", "Dust vs smoke", "Map"])

with tab1:
    rank = base.groupby("city")[metric].mean().sort_values(ascending=False).head(15).reset_index()
    fig = px.bar(rank.sort_values(metric), x=metric, y="city", orientation="h",
                 title=f"Top 15 cities by mean {metric_label} (all cities, selected years)")
    if metric == "pm2_5_mean":
        fig.add_vline(x=40, line_dash="dash", line_color="red",
                      annotation_text="India annual limit (40)")
    st.plotly_chart(fig, width="stretch")

with tab2:
    m = f.groupby(["month", "city"])[metric].mean().reset_index()
    fig = px.line(m, x="month", y=metric, color="city", markers=True,
                  title=f"Monthly mean {metric_label}")
    fig.update_xaxes(dtick=1, tickvals=list(range(1,13)),
       ticktext=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, width="stretch")
    st.info("Switch the pollutant in the sidebar: PM2.5 peaks in winter (smog), "
            "while PM10 peaks in spring in dusty cities like Agra and Delhi.")

with tab3:
    share = (pd.crosstab(f["city"], f["pm25_cat"], normalize="index") * 100).reset_index()
    share = share.melt(id_vars="city", var_name="category", value_name="% of days")
    share["category"] = share["category"].astype(str)
    fig = px.bar(share, x="% of days", y="city", color="category", orientation="h",
                 category_orders={"category": ORDER},
                 color_discrete_map=dict(zip(ORDER, COLORS)),
                 title="Share of days by PM2.5 category")
    st.plotly_chart(fig, width="stretch")

with tab4:
    s = base.groupby("city")[["pm2_5_mean", "pm10_mean"]].mean().reset_index()
    fig = px.scatter(s, x="pm2_5_mean", y="pm10_mean", hover_name="city",
                     title="City averages: fine (PM2.5) vs coarse (PM10) particles")
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, width="stretch")
    st.caption("Cities far above the cluster (e.g. Jodhpur, Jaipur) are dust-dominated.")

with tab5:
    g = base.groupby(["city", "lat", "lon"])[metric].mean().reset_index()
    fig = px.scatter_geo(g, lat="lat", lon="lon", size=metric, height=600, color=metric,
                         hover_name="city", color_continuous_scale="YlOrRd",
                         title=f"Mean {metric_label} by city")
    fig.update_geos(scope="asia", center=dict(lat=22, lon=80),
                    projection_scale=4, showcountries=True, showland=True)
    st.plotly_chart(fig, width="stretch")
  
