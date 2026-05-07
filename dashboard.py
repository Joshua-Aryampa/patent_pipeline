import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pycountry
import streamlit as st

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')

st.set_page_config(
    page_title="Global Patent Intelligence",
    page_icon="📊",
    layout="wide"
)

# Navigation and layout styling
st.markdown("""
<style>
    /* Remove default top padding */
    .block-container { padding-top: 1.5rem; }

    /* Hide the sidebar entirely */
    [data-testid="stSidebar"] { display: none; }

    /* Give the tab list a solid background so it reads as a navbar */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 4px;
        border-bottom: none;
        margin-bottom: 1.5rem;
    }

    /* Each tab looks like a pill button */
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        padding: 12px 32px;
        font-size: 15px;
        font-weight: 600;
        color: #444;
        border: none;
        letter-spacing: 0.3px;
    }

    /* Active tab is clearly highlighted */
    .stTabs [aria-selected="true"] {
        background-color: #0068c9 !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(0, 104, 201, 0.35);
    }

    /* Hover state so users know it's clickable */
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #dce6f5;
        color: #0068c9;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# DATA LOADING
# =============================================================================

@st.cache_data
def load_data():
    inventors = pd.read_csv(os.path.join(OUTPUT_DIR, 'top_inventors.csv'))
    companies = pd.read_csv(os.path.join(OUTPUT_DIR, 'top_companies.csv'))
    countries = pd.read_csv(os.path.join(OUTPUT_DIR, 'country_trends.csv'))
    yearly    = pd.read_csv(os.path.join(OUTPUT_DIR, 'yearly_trends.csv'))
    with open(os.path.join(OUTPUT_DIR, 'report.json')) as f:
        summary = json.load(f)
    return inventors, companies, countries, yearly, summary


def iso2_to_iso3(code):
    try:
        return pycountry.countries.get(alpha_2=code).alpha_3
    except Exception:
        return None


inventors, companies, countries, yearly, summary = load_data()

# =============================================================================
# HEADER
# =============================================================================

st.title("📊 Global Patent Intelligence")
st.markdown(
    "Analysis of **{:,} US granted patents** from the USPTO PatentsView dataset.".format(
        summary['total_patents']
    )
)
st.markdown("---")

# =============================================================================
# TOP NAVIGATION TABS
# =============================================================================

st.markdown("#### 🗂️ Navigate between pages")
tab1, tab2 = st.tabs(["📊  Dashboard", "🔍  Insights & Analysis"])


# =============================================================================
# TAB 1 — DASHBOARD
# =============================================================================

with tab1:

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Patents", f"{summary['total_patents']:,}")
    with col2:
        st.metric("Top Inventor", summary['top_inventors'][0]['name'],
                  f"{summary['top_inventors'][0]['patents']:,} patents")
    with col3:
        st.metric("Top Company", summary['top_companies'][0]['name'][:28] + "...",
                  f"{summary['top_companies'][0]['patents']:,} patents")
    with col4:
        st.metric("Top Country", summary['top_countries'][0]['country'],
                  f"{summary['top_countries'][0]['share']}% of all patents")

    st.markdown("---")

    st.subheader("📈 Patent Grants Over Time")
    yearly_filtered = yearly[yearly['year'] >= 1976]
    fig_trend = px.area(
        yearly_filtered, x='year', y='patent_count',
        labels={'year': 'Year', 'patent_count': 'Patents Granted'},
        color_discrete_sequence=['#0068c9']
    )
    fig_trend.update_layout(hovermode='x unified', showlegend=False,
                            margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("🏆 Top 20 Inventors")
        fig_inv = px.bar(
            inventors.sort_values('patent_count'),
            x='patent_count', y='name', orientation='h', color='country',
            labels={'patent_count': 'Patents', 'name': 'Inventor', 'country': 'Country'},
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_inv.update_layout(showlegend=True, margin=dict(l=0, r=0, t=10, b=0),
                              yaxis=dict(tickfont=dict(size=10)))
        st.plotly_chart(fig_inv, use_container_width=True)

    with col_right:
        st.subheader("🏢 Top 20 Companies")
        fig_comp = px.bar(
            companies.sort_values('patent_count'),
            x='patent_count', y='name', orientation='h',
            labels={'patent_count': 'Patents', 'name': 'Company'},
            color_discrete_sequence=['#ff7f0e']
        )
        fig_comp.update_layout(showlegend=False, margin=dict(l=0, r=0, t=10, b=0),
                               yaxis=dict(tickfont=dict(size=10)))
        st.plotly_chart(fig_comp, use_container_width=True)

    st.markdown("---")
    st.subheader("🌍 Patents by Country")

    col_map, col_bar = st.columns([3, 2])

    with col_map:
        map_data = countries.copy()
        map_data['iso3'] = map_data['country'].apply(iso2_to_iso3)
        map_data = map_data.dropna(subset=['iso3'])
        fig_map = px.choropleth(
            map_data, locations='iso3', locationmode='ISO-3',
            color='patent_count', hover_name='country',
            hover_data={'patent_count': ':,', 'share_pct': True, 'iso3': False},
            color_continuous_scale='Blues',
            labels={'patent_count': 'Patents', 'share_pct': 'Share (%)'}
        )
        fig_map.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_map, use_container_width=True)

    with col_bar:
        fig_country = px.bar(
            countries.sort_values('patent_count'),
            x='patent_count', y='country', orientation='h', color='share_pct',
            labels={'patent_count': 'Patents', 'country': 'Country', 'share_pct': 'Share (%)'},
            color_continuous_scale='Blues'
        )
        fig_country.update_layout(margin=dict(l=0, r=0, t=10, b=0),
                                  coloraxis_showscale=False,
                                  yaxis=dict(tickfont=dict(size=11)))
        st.plotly_chart(fig_country, use_container_width=True)

    st.markdown("---")
    st.subheader("🥧 Country Share of Global Patents")

    top10 = countries.head(10).copy()
    other_row = pd.DataFrame([{
        'country': 'Other',
        'patent_count': summary['total_patents'] - top10['patent_count'].sum(),
        'share_pct': round(100 - top10['share_pct'].sum(), 2)
    }])
    pie_data = pd.concat([top10, other_row], ignore_index=True)
    fig_pie = px.pie(pie_data, names='country', values='patent_count',
                     color_discrete_sequence=px.colors.qualitative.Set3)
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    fig_pie.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    st.subheader("📋 Raw Data Tables")
    with st.expander("Top Inventors"):
        st.dataframe(inventors, use_container_width=True)
    with st.expander("Top Companies"):
        st.dataframe(companies, use_container_width=True)
    with st.expander("Top Countries"):
        st.dataframe(countries, use_container_width=True)
    with st.expander("Yearly Trends"):
        st.dataframe(yearly, use_container_width=True)

    st.markdown("---")
    st.caption("Data source: USPTO PatentsView · Built with Python, SQLite, pandas, Plotly and Streamlit")


# =============================================================================
# TAB 2 — INSIGHTS & ANALYSIS
# =============================================================================

with tab2:

    st.markdown(
        "What does the data actually tell us? Below are five data-driven insights "
        "derived from the USPTO patent record — each with a chart, the numbers "
        "behind it, and an interpretation of what it means."
    )
    st.markdown("---")

    # -------------------------------------------------------------------------
    # INSIGHT 1 — THE 1970s INFLECTION POINT
    # -------------------------------------------------------------------------

    st.subheader("1. The 1970s Inflection Point — When Innovation Went Industrial")

    yearly_full = yearly[yearly['year'] >= 1960].copy()
    yearly_full['decade'] = (yearly_full['year'] // 10 * 10).astype(str) + 's'
    decade_avg = yearly_full.groupby('decade')['patent_count'].mean().reset_index()
    decade_avg.columns = ['decade', 'avg_patents']

    col_a, col_b = st.columns([2, 1])

    with col_a:
        fig1 = px.bar(
            decade_avg, x='decade', y='avg_patents',
            labels={'decade': 'Decade', 'avg_patents': 'Avg Patents per Year'},
            color='avg_patents', color_continuous_scale='Blues'
        )
        fig1.update_layout(showlegend=False, coloraxis_showscale=False,
                           margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        avg_60s = yearly_full[yearly_full['decade'] == '1960s']['patent_count'].mean()
        avg_70s = yearly_full[yearly_full['decade'] == '1970s']['patent_count'].mean()
        avg_2010s = yearly_full[yearly_full['decade'] == '2010s']['patent_count'].mean()
        growth_60_70 = ((avg_70s - avg_60s) / avg_60s * 100)

        st.metric("Avg patents/year 1960s", f"{avg_60s:,.0f}")
        st.metric("Avg patents/year 1970s", f"{avg_70s:,.0f}",
                  delta=f"+{growth_60_70:.0f}%")
        st.metric("Avg patents/year 2010s", f"{avg_2010s:,.0f}")

    st.markdown("""
    **What the data shows:** Patent grants jumped from an average of ~{avg_60s:,.0f}/year
    in the 1960s to ~{avg_70s:,.0f}/year in the 1970s — a **{growth:.0f}% increase in a
    single decade**.

    **Why this happened:** The 1970s saw the convergence of several forces — the rise of
    semiconductor and computer industries, increased corporate R&D spending following the
    post-war economic boom, and the USPTO's shift to electronic record keeping which made
    filing easier and tracking more complete. The data itself partly reflects a digitisation
    effect: pre-1976 records are sparse because USPTO digital archives only became
    comprehensive from that point.

    **Implication:** The 1970s was not just a technological inflection point — it was the
    moment corporations began treating intellectual property as a strategic asset rather than
    simply a legal protection mechanism. The patent system effectively became a competitive
    weapon rather than just a reward for invention.
    """.format(avg_60s=avg_60s, avg_70s=avg_70s, growth=growth_60_70))

    st.markdown("---")

    # -------------------------------------------------------------------------
    # INSIGHT 2 — US DOMINANCE AND ITS GRADUAL EROSION
    # -------------------------------------------------------------------------

    st.subheader("2. US Dominance — Commanding but Slowly Eroding")

    us_share = countries[countries['country'] == 'US']['share_pct'].values[0]
    us_patents = countries[countries['country'] == 'US']['patent_count'].values[0]
    asia_countries = ['JP', 'CN', 'KR', 'TW']
    asia_data = countries[countries['country'].isin(asia_countries)]
    asia_share = asia_data['share_pct'].sum()
    asia_patents = asia_data['patent_count'].sum()

    col_a, col_b = st.columns([1, 2])

    with col_a:
        st.metric("US share of global patents", f"{us_share}%",
                  f"{us_patents:,} patents")
        st.metric("Asia (JP+CN+KR+TW) combined", f"{asia_share:.2f}%",
                  f"{asia_patents:,} patents")
        st.metric("US vs Asia gap",
                  f"{us_share - asia_share:.1f} percentage points")

    with col_b:
        yearly_decade = yearly[yearly['year'] >= 1980].copy()
        yearly_decade['decade'] = (yearly_decade['year'] // 10 * 10)
        decade_total = yearly_decade.groupby('decade')['patent_count'].sum().reset_index()
        decade_total['decade_label'] = decade_total['decade'].astype(str) + 's'

        fig3 = px.bar(
            decade_total, x='decade_label', y='patent_count',
            labels={'decade_label': 'Decade', 'patent_count': 'Total Patents Granted'},
            color='patent_count', color_continuous_scale='RdYlGn'
        )
        fig3.update_layout(coloraxis_showscale=False,
                           margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("""
    **What the data shows:** The US holds **{us_share:.1f}%** of all patents — more than
    the next 19 countries combined. However Japan, China, South Korea and Taiwan together
    account for **{asia_share:.1f}%**, and China's share has been growing rapidly
    (our trend analysis showed China grew **1,896%** from the 1990s to the 2010s).

    **Why this is happening:** The US advantage is partly structural — the USPTO dataset
    covers US-granted patents, which naturally favours US filers. But the rise of Asian
    economies, particularly China's state-driven innovation policy and South Korea's
    chaebol R&D investment model (Samsung, LG, Hyundai), reflects a genuine shift in
    where the world's technological capacity is concentrated.

    **Implication:** If current trends continue, the gap between the US and Asia will
    narrow significantly over the next two decades. This has major implications for
    geopolitical technology competition — particularly in semiconductors, AI, and clean
    energy where patent portfolios directly translate to manufacturing leverage.
    """.format(us_share=us_share, asia_share=asia_share))

    st.markdown("---")

    # -------------------------------------------------------------------------
    # INSIGHT 3 — PEAK AND PLATEAU
    # -------------------------------------------------------------------------

    st.subheader("3. Peak Innovation? The Post-2019 Decline")

    peak_row = yearly[yearly['patent_count'] == yearly['patent_count'].max()].iloc[0]
    peak_year = int(peak_row['year'])
    peak_count = int(peak_row['patent_count'])
    count_2019 = int(yearly[yearly['year'] == 2019]['patent_count'].values[0])
    count_2022 = int(yearly[yearly['year'] == 2022]['patent_count'].values[0])
    count_2024 = int(yearly[yearly['year'] == 2024]['patent_count'].values[0])
    decline_pct = (count_2019 - count_2022) / count_2019 * 100

    recent = yearly[yearly['year'] >= 2015].copy()

    col_a, col_b = st.columns([2, 1])

    with col_a:
        fig4 = px.line(
            recent, x='year', y='patent_count', markers=True,
            labels={'year': 'Year', 'patent_count': 'Patents Granted'},
            color_discrete_sequence=['#e63946']
        )
        fig4.add_vline(x=peak_year, line_dash="dash", line_color="gray",
                       annotation_text=f"Peak: {peak_year}")
        fig4.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig4, use_container_width=True)

    with col_b:
        st.metric("Peak year", str(peak_year))
        st.metric("Peak count", f"{peak_count:,}")
        st.metric("2022 count", f"{count_2022:,}",
                  delta=f"-{decline_pct:.1f}% from peak")
        st.metric("2024 count", f"{count_2024:,}",
                  delta="Processing lag expected")

    st.markdown("""
    **What the data shows:** Patent grants peaked in **{peak_year}** at **{peak_count:,}**
    and have declined every year since. By 2022 grants had fallen **{decline_pct:.1f}%**
    from that peak. 2023 and 2024 show even sharper drops.

    **Two competing explanations:**

    *Explanation A — Processing lag:* Recent patents take 2–3 years to be examined, approved,
    and entered into the PatentsView database. The sharp drop in 2023–2024 is almost certainly
    a data completeness issue rather than a real decline — those patents are filed but not yet
    processed into this dataset.

    *Explanation B — A genuine slowdown:* The 2020 COVID-19 pandemic disrupted R&D cycles,
    slowed corporate investment, and reduced USPTO examiner capacity. Some researchers argue
    we are also hitting diminishing returns in certain technology areas — the "low-hanging
    fruit" of software patents that drove growth in the 2010s has been largely harvested.

    **Most likely:** Both are true simultaneously. The 2020–2021 dip is real pandemic effect.
    The 2022–2024 drop is predominantly data lag. A reassessment in 2026 with more complete
    records will tell a cleaner story.
    """.format(peak_year=peak_year, peak_count=peak_count, decline_pct=decline_pct))

    st.markdown("---")

    # -------------------------------------------------------------------------
    # INSIGHT 4 — THE PROLIFIC INVENTOR PHENOMENON
    # -------------------------------------------------------------------------

    st.subheader("4. The Prolific Inventor Phenomenon — Individual vs Institution")

    avg_patents = inventors['patent_count'].mean()
    max_patents = inventors['patent_count'].max()
    ratio = max_patents / avg_patents
    us_inventors = inventors[inventors['country'] == 'US']

    col_a, col_b = st.columns([2, 1])

    with col_a:
        fig5 = px.scatter(
            inventors,
            x=inventors.index,
            y='patent_count',
            color='country',
            hover_data=['name', 'country', 'patent_count'],
            labels={'x': 'Inventor Rank', 'patent_count': 'Patent Count'},
            color_discrete_sequence=px.colors.qualitative.Set1,
            size='patent_count',
            size_max=40
        )
        fig5.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig5, use_container_width=True)

    with col_b:
        st.metric("Top inventor patents", f"{max_patents:,}")
        st.metric("Average (top 20)", f"{avg_patents:,.0f}")
        st.metric("Top inventor vs average", f"{ratio:.1f}x more")
        st.metric("US-based in top 20",
                  f"{len(us_inventors)} of {len(inventors)}")

    st.markdown("""
    **What the data shows:** Shunpei Yamazaki (Japan) holds **{max_patents:,} patents** —
    **{ratio:.1f}x** the average of the top 20 inventors. This is not a statistical outlier
    in the normal sense — it reflects a deliberate, institutionally-backed filing strategy.

    **The institution behind the individual:** Yamazaki is the founder of Semiconductor
    Energy Laboratory (SEL), a private Japanese research company. His name appears on patents
    because Japanese patent culture and SEL's internal policy attributes inventions to the
    lead researcher. This means his count is as much a measure of SEL's output as his
    personal genius.

    **The Apple design team pattern:** Jonathan Ive (#4, 2,947 patents), Duncan Robert Kerr,
    Bartley Andre, and Christopher Stringer are all Apple industrial designers. Their high
    counts reflect Apple's aggressive design patent strategy in the 2000s and 2010s —
    filing patents on every physical and UI element of their products as a competitive moat.

    **Implication:** "Top inventor" rankings in patent data do not straightforwardly measure
    individual creativity. They measure the intersection of personal productivity, employer
    IP strategy, and national filing culture. A lone inventor with 50 patents and no
    institutional backing may represent more genuine individual innovation than a corporate
    designer with 2,000.
    """.format(max_patents=max_patents, ratio=ratio))

    st.markdown("---")

    # -------------------------------------------------------------------------
    # INSIGHT 5 — EAST ASIA'S STRATEGIC PATENT BUILDOUT
    # -------------------------------------------------------------------------

    st.subheader("5. East Asia's Strategic Patent Buildout — State Policy as Innovation Driver")

    east_asia = countries[countries['country'].isin(['JP', 'CN', 'KR', 'TW'])].copy()
    west = countries[countries['country'].isin(['US', 'DE', 'GB', 'FR'])].copy()
    ea_total = east_asia['patent_count'].sum()
    west_total = west['patent_count'].sum()
    ea_share = east_asia['share_pct'].sum()
    west_share = west['share_pct'].sum()

    col_a, col_b = st.columns([1, 2])

    with col_a:
        st.metric("East Asia (JP+CN+KR+TW)", f"{ea_total:,}",
                  f"{ea_share:.1f}% of all patents")
        st.metric("Western bloc (US+DE+GB+FR)", f"{west_total:,}",
                  f"{west_share:.1f}% of all patents")
        st.metric(
            "East Asia vs Western bloc",
            f"{abs(west_total - ea_total):,} patent gap",
            delta="West still leads" if west_total > ea_total else "East now leads"
        )

    with col_b:
        compare_df = pd.DataFrame([
            {'Region': 'East Asia',    'Country': 'JP', 'Patents': int(countries[countries['country'] == 'JP']['patent_count'].values[0])},
            {'Region': 'East Asia',    'Country': 'CN', 'Patents': int(countries[countries['country'] == 'CN']['patent_count'].values[0])},
            {'Region': 'East Asia',    'Country': 'KR', 'Patents': int(countries[countries['country'] == 'KR']['patent_count'].values[0])},
            {'Region': 'East Asia',    'Country': 'TW', 'Patents': int(countries[countries['country'] == 'TW']['patent_count'].values[0])},
            {'Region': 'Western Bloc', 'Country': 'US', 'Patents': int(countries[countries['country'] == 'US']['patent_count'].values[0])},
            {'Region': 'Western Bloc', 'Country': 'DE', 'Patents': int(countries[countries['country'] == 'DE']['patent_count'].values[0])},
            {'Region': 'Western Bloc', 'Country': 'GB', 'Patents': int(countries[countries['country'] == 'GB']['patent_count'].values[0])},
            {'Region': 'Western Bloc', 'Country': 'FR', 'Patents': int(countries[countries['country'] == 'FR']['patent_count'].values[0])},
        ])
        fig6 = px.bar(
            compare_df, x='Country', y='Patents', color='Region',
            color_discrete_map={'East Asia': '#e63946', 'Western Bloc': '#0068c9'},
            labels={'Patents': 'Patent Count', 'Country': 'Country'}
        )
        fig6.update_layout(margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig6, use_container_width=True)

    st.markdown("""
    **What the data shows:** Japan, China, South Korea and Taiwan combined hold
    **{ea_share:.1f}%** of all patents — comparable to the combined share of the US,
    Germany, UK and France at **{west_share:.1f}%**. Japan alone holds **16.9%**,
    second only to the US.

    **The state policy connection:** This is not accidental. South Korea's patent surge
    correlates directly with government-mandated R&D spending requirements for large
    corporations (chaebols) introduced in the 1980s. China's surge from the 2000s onwards
    mirrors the introduction of patent filing targets in state-owned enterprises and
    substantial government subsidies for patent applications. Taiwan's strength reflects
    TSMC and the broader semiconductor supply chain ecosystem built around Hsinchu Science Park.

    **Japan's position is particularly revealing:** Despite decades of economic stagnation
    since the 1990s, Japan maintains the world's second largest patent portfolio. This suggests
    Japanese corporations continued investing heavily in R&D even during difficult economic
    periods — a very different corporate behaviour from Western firms which typically cut
    R&D during downturns.

    **Implication:** Patent data is not just an innovation metric — it is a geopolitical
    signal. The East Asian patent buildout over the past 30 years represents a deliberate
    transfer of technological leverage from West to East, driven as much by state industrial
    policy as by market forces. Understanding this is essential context for current debates
    around technology decoupling, export controls, and supply chain sovereignty.
    """.format(ea_share=ea_share, west_share=west_share))

    st.markdown("---")
    st.caption("Data source: USPTO PatentsView Granted Patent Disambiguated Dataset · "
               "Built with Python, SQLite, pandas, Plotly and Streamlit")
