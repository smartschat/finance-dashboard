import json
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from finance_dashboard.categorization import (
    apply_description_clusters,
    get_legacy_override_key,
    get_override_key,
)

# Import from modular structure
from finance_dashboard.config import (
    DEFAULT_CC_SETTLEMENT_PATTERNS,
    get_non_spend_categories,
    hashable_config,
    load_categories,
)
from finance_dashboard.config import (
    save_categories as _save_categories_base,
)
from finance_dashboard.data import (
    get_csv_file_manifest,
    load_all_data,
)

st.set_page_config(page_title="Finanz-Dashboard", page_icon="💰", layout="wide")

# Custom CSS
st.markdown(
    """
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .positive { color: #28a745; }
    .negative { color: #dc3545; }

    /* Fix date picker popover positioning - center on screen */
    [data-baseweb="popover"]:has([data-baseweb="calendar"]) {
        position: fixed !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        z-index: 9999 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


def save_categories(categories):
    """Save category rules to JSON file and clear caches."""
    _save_categories_base(categories)
    # Clear cached data to reflect changes
    load_all_data.clear()
    # Clear combined data cache (defined later, so use globals)
    if "prepare_combined_data" in globals():
        prepare_combined_data.clear()


@st.cache_data
def prepare_combined_data(_giro_dfs, _visa_dfs, overrides_hash, cluster_rules_hash, config_hash):
    """Prepare and process combined transaction data (cached)."""
    config = json.loads(config_hash)
    cc_settlement_patterns = config.get("cc_settlement_patterns", DEFAULT_CC_SETTLEMENT_PATTERNS)

    # Combine all data for overall analysis
    all_transactions = []

    for df in _giro_dfs:
        temp = df[["Datum", "Betrag", "Kategorie", "Konto", "Monat"]].copy()
        emp = df["Zahlungsempfaenger"].fillna("").astype(str).str.strip()
        zweck = df["Verwendungszweck"].fillna("").astype(str).str.strip()
        temp["Beschreibung"] = emp + zweck.apply(lambda x: f" - {x}" if x else "")
        all_transactions.append(temp)

    for df in _visa_dfs:
        temp = df[["Datum", "Betrag", "Kategorie", "Konto", "Monat"]].copy()
        temp["Beschreibung"] = df["Beschreibung"]
        all_transactions.append(temp)

    combined_df = pd.concat(all_transactions, ignore_index=True)
    combined_df = combined_df.sort_values("Datum", ascending=False)

    # Apply manual category overrides (supports both new hash-based and legacy truncated keys)
    cat_config_overrides = json.loads(overrides_hash)
    if cat_config_overrides:
        combined_df["_override_key"] = combined_df.apply(get_override_key, axis=1)
        combined_df["_legacy_key"] = combined_df.apply(get_legacy_override_key, axis=1)
        combined_df["Kategorie"] = combined_df.apply(
            lambda row: cat_config_overrides.get(
                row["_override_key"], cat_config_overrides.get(row["_legacy_key"], row["Kategorie"])
            ),
            axis=1,
        )
        combined_df = combined_df.drop(columns=["_override_key", "_legacy_key"])

    # Categorize internal credit card payments as "Kreditkarte" instead of dropping them
    # This keeps them visible in transaction tables while excluding from spending calculations
    # (via non_spend_categories filtering in views)
    cc_settlement_mask = (
        combined_df["Beschreibung"]
        .str.lower()
        .apply(lambda x: any(pattern in x for pattern in cc_settlement_patterns))
    )
    combined_df.loc[cc_settlement_mask, "Kategorie"] = "Kreditkarte"

    # Apply description clusters for reporting
    cluster_rules = json.loads(cluster_rules_hash)
    combined_df["Beschreibung_cluster"] = apply_description_clusters(
        combined_df["Beschreibung"], cluster_rules
    )

    # Add year column for year comparison
    combined_df["Jahr"] = combined_df["Datum"].dt.year
    combined_df["MonthNum"] = combined_df["Datum"].dt.month

    return combined_df


def initialize_session_state():
    """Initialize all session state variables with defaults.

    Centralizes session state initialization to avoid scattered if-checks.
    Dynamic keys (like per-category text areas) are still initialized where used.
    """
    defaults = {
        "editing_category": None,
        "active_tab": "Übersicht",
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# Initialize session state
initialize_session_state()

# Load data (with file manifest for cache invalidation)
data_dir = os.environ.get("DATA_DIR", ".")
giro_dfs, visa_dfs, parse_failures = load_all_data(
    get_csv_file_manifest(data_dir), data_dir=data_dir
)
categories_config = load_categories()

# Get configurable values
non_spend_categories = get_non_spend_categories(categories_config)

# Show warning if any rows failed to parse
if parse_failures > 0:
    st.warning(
        f"⚠️ {parse_failures} Transaktion(en) konnten nicht geladen werden "
        f"(ungültiges Datumsformat). Diese wurden übersprungen."
    )

# Prepare combined data with caching
combined_df = prepare_combined_data(
    giro_dfs,
    visa_dfs,
    hashable_config(categories_config.get("overrides", {})),
    hashable_config(categories_config.get("clusters", {})),
    hashable_config(categories_config.get("config", {})),
)

# Sidebar filters
st.sidebar.title("Filter")

# Year filter
available_years = sorted(combined_df["Jahr"].unique(), reverse=True)
selected_years = st.sidebar.multiselect("Jahre", available_years, default=available_years)

# Date range filter - updates based on selected years
if selected_years:
    year_filtered = combined_df[combined_df["Jahr"].isin(selected_years)]
    min_date = year_filtered["Datum"].min()
    max_date = year_filtered["Datum"].max()
else:
    min_date = combined_df["Datum"].min()
    max_date = combined_df["Datum"].max()
date_range = st.sidebar.date_input(
    "Zeitraum", value=(min_date, max_date), min_value=min_date, max_value=max_date
)

# Account filter
accounts = ["Alle"] + list(combined_df["Konto"].unique())
selected_account = st.sidebar.selectbox("Konto", accounts)

# Category filter
categories = ["Alle"] + sorted(combined_df["Kategorie"].unique().tolist())
selected_category = st.sidebar.selectbox("Kategorie", categories)

# Apply filters
filtered_df = combined_df.copy()
if selected_years:
    filtered_df = filtered_df[filtered_df["Jahr"].isin(selected_years)]
if len(date_range) == 2:
    filtered_df = filtered_df[
        (filtered_df["Datum"] >= pd.Timestamp(date_range[0]))
        & (filtered_df["Datum"] <= pd.Timestamp(date_range[1]))
    ]
if selected_account != "Alle":
    filtered_df = filtered_df[filtered_df["Konto"] == selected_account]
if selected_category != "Alle":
    filtered_df = filtered_df[filtered_df["Kategorie"] == selected_category]

# Main dashboard
st.title("Finanz-Dashboard")

# Stateful view selector to keep the active tab on reruns
tab_labels = [
    "Übersicht",
    "Ausgabentrends",
    "Investitionen",
    "Jahresvergleich",
    "Typischer Monat",
    "Einstellungen",
]
active_tab = st.radio(
    "Ansicht auswählen",
    tab_labels,
    key="active_tab",
    horizontal=True,
    label_visibility="collapsed",
)

if active_tab == "Übersicht":
    # Key metrics (exclude non-spending categories to avoid double-counting)
    col1, col2, col3, col4 = st.columns(4)

    real_transactions = filtered_df[~filtered_df["Kategorie"].isin(non_spend_categories)]
    total_income = real_transactions[real_transactions["Betrag"] > 0]["Betrag"].sum()
    total_expenses = real_transactions[real_transactions["Betrag"] < 0]["Betrag"].sum()
    net_flow = total_income + total_expenses
    transaction_count = len(real_transactions)

    with col1:
        st.metric("Einnahmen gesamt", f"€{total_income:,.2f}")
    with col2:
        st.metric("Ausgaben gesamt", f"€{abs(total_expenses):,.2f}")
    with col3:
        delta_color = "normal" if net_flow >= 0 else "inverse"
        st.metric("Netto", f"€{net_flow:,.2f}", delta_color=delta_color)
    with col4:
        st.metric("Transaktionen", transaction_count)

    st.divider()

    # Charts row 1
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Monatlicher Cashflow")
        cashflow_df = filtered_df[~filtered_df["Kategorie"].isin(non_spend_categories)]
        monthly = (
            cashflow_df.groupby("Monat")
            .agg({"Betrag": lambda x: (x[x > 0].sum(), x[x < 0].sum())})
            .reset_index()
        )
        monthly["Einnahmen"] = monthly["Betrag"].apply(lambda x: x[0])
        monthly["Ausgaben"] = monthly["Betrag"].apply(lambda x: abs(x[1]))
        monthly["Monat_str"] = monthly["Monat"].astype(str)

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                name="Einnahmen",
                x=monthly["Monat_str"],
                y=monthly["Einnahmen"],
                marker_color="#28a745",
            )
        )
        fig.add_trace(
            go.Bar(
                name="Ausgaben",
                x=monthly["Monat_str"],
                y=monthly["Ausgaben"],
                marker_color="#dc3545",
            )
        )
        fig.update_layout(barmode="group", xaxis_title="Monat", yaxis_title="Betrag (€)")
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.subheader("Ausgaben nach Kategorie")
        expenses_only = filtered_df[
            (filtered_df["Betrag"] < 0) & (~filtered_df["Kategorie"].isin(non_spend_categories))
        ].copy()
        expenses_only["Betrag_abs"] = expenses_only["Betrag"].abs()
        category_spending = (
            expenses_only.groupby("Kategorie")["Betrag_abs"].sum().sort_values(ascending=False)
        )

        # Filter out non-spending categories for cleaner view
        category_spending = category_spending[~category_spending.index.isin(non_spend_categories)]

        fig = px.pie(values=category_spending.values, names=category_spending.index, hole=0.4)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, width="stretch")

    # Charts row 2
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Tägliche Ausgaben")
        daily_expenses = filtered_df[
            (filtered_df["Betrag"] < 0) & (~filtered_df["Kategorie"].isin(non_spend_categories))
        ].copy()
        daily_expenses["Betrag_abs"] = daily_expenses["Betrag"].abs()
        daily_trend = daily_expenses.groupby("Datum")["Betrag_abs"].sum().reset_index()

        fig = px.line(
            daily_trend,
            x="Datum",
            y="Betrag_abs",
            labels={"Betrag_abs": "Ausgaben (€)"},
        )
        fig.update_traces(line_color="#dc3545")
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.subheader("Top-Kategorien (Monatsdurchschnitt)")
        # Calculate number of months from the actual date range
        if len(date_range) == 2:
            start_date = pd.Timestamp(date_range[0])
            end_date = pd.Timestamp(date_range[1])
            num_months = (
                (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
            )
        else:
            num_months = filtered_df["Monat"].nunique()
        if num_months == 0:
            num_months = 1  # Avoid division by zero

        # Total spending per category divided by number of months
        category_totals = expenses_only.groupby("Kategorie")["Betrag_abs"].sum()
        # Filter out non-spending categories
        category_totals = category_totals[~category_totals.index.isin(non_spend_categories)]
        monthly_avg = (category_totals / num_months).sort_values(ascending=True).tail(10)

        fig = px.bar(
            x=monthly_avg.values,
            y=monthly_avg.index,
            orientation="h",
            labels={"x": "Durchschn. Monatsausgaben (€)", "y": "Kategorie"},
        )
        fig.update_traces(marker_color="#6c757d")
        st.plotly_chart(fig, width="stretch")

    st.divider()

    # Subscription analysis
    st.subheader("Abonnements")
    subscriptions = filtered_df[filtered_df["Kategorie"] == "Abonnements"].copy()
    if not subscriptions.empty:
        subscriptions["Betrag_abs"] = subscriptions["Betrag"].abs()
        sub_summary = (
            subscriptions.groupby("Beschreibung_cluster")["Betrag_abs"]
            .agg(["sum", "count", "mean"])
            .reset_index()
        )
        sub_summary.columns = ["Dienst", "Gesamt", "Anzahl", "Durchschnitt"]
        sub_summary = sub_summary.sort_values("Gesamt", ascending=False)
        st.dataframe(
            sub_summary,
            width="stretch",
            column_config={
                "Gesamt": st.column_config.NumberColumn(format="€%.2f"),
                "Durchschnitt": st.column_config.NumberColumn(format="€%.2f"),
            },
        )
    else:
        st.info("Keine Abonnements im ausgewählten Zeitraum gefunden.")

    st.divider()

    # Transaction table
    st.subheader("Alle Transaktionen")

    # Search filter
    search = st.text_input("Transaktionen durchsuchen", "")
    display_df = filtered_df.copy()
    if search:
        display_df = display_df[
            display_df["Beschreibung"].str.contains(search, case=False, na=False)
        ]

    display_df["Datum_str"] = display_df["Datum"].dt.strftime("%d.%m.%Y")

    # Load categories for the dropdown
    cat_config = load_categories()
    all_cats = sorted(cat_config["rules"].keys()) + ["Umbuchungen", "Gehalt", "Sonstiges"]

    # Add override key for tracking changes (new format for saving)
    display_df["_key"] = display_df.apply(get_override_key, axis=1)
    display_df["_legacy_key"] = display_df.apply(get_legacy_override_key, axis=1)

    # Check which transactions have manual overrides (check both new and legacy formats)
    overrides = cat_config.get("overrides", {})
    display_df["_override"] = display_df.apply(
        lambda row: "📝" if row["_key"] in overrides or row["_legacy_key"] in overrides else "",
        axis=1,
    )

    # Prepare editable dataframe
    edit_df = display_df[
        ["Datum_str", "Beschreibung", "_override", "Kategorie", "Konto", "Betrag", "_key"]
    ].copy()
    edit_df = edit_df.rename(columns={"Datum_str": "Datum", "_override": " "})

    # Use data_editor for category editing
    edited_df = st.data_editor(
        edit_df,
        width="stretch",
        height=400,
        column_config={
            "Datum": st.column_config.TextColumn("Datum", disabled=True),
            "Beschreibung": st.column_config.TextColumn(
                "Beschreibung", disabled=True, width="large"
            ),
            " ": st.column_config.TextColumn(" ", disabled=True, width="small"),
            "Kategorie": st.column_config.SelectboxColumn(
                "Kategorie", options=all_cats, required=True
            ),
            "Konto": st.column_config.TextColumn("Konto", disabled=True),
            "Betrag": st.column_config.NumberColumn("Betrag", format="€%.2f", disabled=True),
            "_key": None,  # Hide the key column
        },
        hide_index=True,
        key="transaction_editor",
    )

    # Detect and save category changes
    if edited_df is not None:
        for idx, row in edited_df.iterrows():
            orig_cat = edit_df.loc[idx, "Kategorie"]
            new_cat = row["Kategorie"]
            if new_cat != orig_cat:
                key = row["_key"]
                cat_config["overrides"][key] = new_cat
                save_categories(cat_config)
                st.rerun()

elif active_tab == "Ausgabentrends":
    st.subheader("Ausgabentrends im Zeitverlauf")
    st.write("Verfolge, wie sich deine Ausgaben in verschiedenen Kategorien entwickeln.")

    # Get expense data only (exclude non-spending categories)
    trends_df = filtered_df[
        (filtered_df["Betrag"] < 0) & (~filtered_df["Kategorie"].isin(non_spend_categories))
    ].copy()
    trends_df["Betrag_abs"] = trends_df["Betrag"].abs()
    trends_df["Month"] = trends_df["Datum"].dt.to_period("M").astype(str)

    # Get available categories sorted by total spending
    category_totals = (
        trends_df.groupby("Kategorie")["Betrag_abs"].sum().sort_values(ascending=False)
    )
    available_categories = category_totals.index.tolist()

    # Category selector
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_categories = st.multiselect(
            "Kategorien zum Vergleichen auswählen",
            available_categories,
            default=(
                available_categories[:5] if len(available_categories) >= 5 else available_categories
            ),
            key="trend_categories",
        )
    with col2:
        show_rolling_avg = st.checkbox("3-Monats-Durchschnitt anzeigen", value=True)

    if selected_categories:
        # Aggregate monthly spending by category
        monthly_by_cat = (
            trends_df[trends_df["Kategorie"].isin(selected_categories)]
            .groupby(["Month", "Kategorie"])["Betrag_abs"]
            .sum()
            .unstack(fill_value=0)
        )

        # Apply rolling average if selected
        if show_rolling_avg:
            monthly_by_cat = monthly_by_cat.rolling(window=3, min_periods=1).mean()

        # Line chart
        fig = go.Figure()
        colors = px.colors.qualitative.Set2
        for i, cat in enumerate(selected_categories):
            if cat in monthly_by_cat.columns:
                fig.add_trace(
                    go.Scatter(
                        x=monthly_by_cat.index,
                        y=monthly_by_cat[cat],
                        name=cat,
                        mode="lines+markers",
                        line=dict(color=colors[i % len(colors)], width=2),
                        marker=dict(size=6),
                    )
                )

        title = "Monatliche Ausgaben nach Kategorie"
        if show_rolling_avg:
            title += " (3-Monats-Durchschnitt)"
        fig.update_layout(
            title=title,
            xaxis_title="Monat",
            yaxis_title="Ausgaben (€)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, width="stretch")

        st.divider()

        # Trend analysis table
        st.subheader("Trendanalyse")

        # Calculate trends for each category
        trend_data = []
        for cat in selected_categories:
            if cat not in monthly_by_cat.columns:
                continue

            cat_data = monthly_by_cat[cat]
            if len(cat_data) < 2:
                continue

            # Get values for comparison
            current_3m = cat_data.tail(3).mean()
            previous_3m = (
                cat_data.tail(6).head(3).mean() if len(cat_data) >= 6 else cat_data.head(3).mean()
            )
            overall_avg = cat_data.mean()
            total = category_totals.get(cat, 0)

            # Calculate change
            if previous_3m > 0:
                change_pct = ((current_3m - previous_3m) / previous_3m) * 100
            else:
                change_pct = 0

            # Determine trend direction
            if change_pct > 10:
                trend = "📈 Steigend"
            elif change_pct < -10:
                trend = "📉 Sinkend"
            else:
                trend = "➡️ Stabil"

            trend_data.append(
                {
                    "Kategorie": cat,
                    "Gesamt": total,
                    "Monatsdurchschnitt": overall_avg,
                    "Letzte 3 Mon.": current_3m,
                    "Vorherige 3 Mon.": previous_3m,
                    "Änderung %": change_pct,
                    "Trend": trend,
                }
            )

        if trend_data:
            trend_table = pd.DataFrame(trend_data)
            trend_table = trend_table.sort_values("Gesamt", ascending=False)

            st.dataframe(
                trend_table,
                width="stretch",
                hide_index=True,
                column_config={
                    "Gesamt": st.column_config.NumberColumn(format="€%.0f"),
                    "Monatsdurchschnitt": st.column_config.NumberColumn(format="€%.0f"),
                    "Letzte 3 Mon.": st.column_config.NumberColumn(format="€%.0f"),
                    "Vorherige 3 Mon.": st.column_config.NumberColumn(format="€%.0f"),
                    "Änderung %": st.column_config.NumberColumn(format="%.1f%%"),
                },
            )

        st.divider()

        # Individual category deep-dive
        st.subheader("Kategoriedetails")
        deep_dive_cat = st.selectbox(
            "Kategorie für Detailansicht auswählen",
            selected_categories,
            key="deep_dive_cat",
        )

        if deep_dive_cat:
            cat_transactions = trends_df[trends_df["Kategorie"] == deep_dive_cat].copy()

            col1, col2 = st.columns(2)

            with col1:
                # Monthly bar chart for this category
                cat_monthly = cat_transactions.groupby("Month")["Betrag_abs"].sum()
                fig = px.bar(
                    x=cat_monthly.index,
                    y=cat_monthly.values,
                    labels={"x": "Monat", "y": "Ausgaben (€)"},
                    title=f"{deep_dive_cat} - Monatliche Ausgaben",
                )
                fig.update_traces(marker_color="#1f77b4")

                # Add trend line
                if len(cat_monthly) >= 2:
                    x_numeric = np.arange(len(cat_monthly))
                    z = np.polyfit(x_numeric, cat_monthly.values, 1)
                    p = np.poly1d(z)
                    fig.add_trace(
                        go.Scatter(
                            x=cat_monthly.index,
                            y=p(x_numeric),
                            mode="lines",
                            name="Trend",
                            line=dict(color="red", dash="dash", width=2),
                        )
                    )

                st.plotly_chart(fig, width="stretch")

            with col2:
                # Top merchants/descriptions in this category
                st.write(f"**Top-Ausgaben in {deep_dive_cat}:**")
                top_merchants = (
                    cat_transactions.groupby("Beschreibung_cluster")["Betrag_abs"]
                    .agg(["sum", "count"])
                    .sort_values("sum", ascending=False)
                    .head(10)
                    .reset_index()
                )
                top_merchants.columns = ["Beschreibung", "Gesamt", "Anzahl"]
                st.dataframe(
                    top_merchants,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Gesamt": st.column_config.NumberColumn(format="€%.2f"),
                    },
                )
    else:
        st.info("Wähle mindestens eine Kategorie, um Trends anzuzeigen.")

elif active_tab == "Investitionen":
    st.subheader("Investitionen")
    st.write("Käufe und Verkäufe separat, damit Ausgaben sauber bleiben.")

    investment_df = filtered_df[filtered_df["Kategorie"] == "Investitionen"].copy()
    if investment_df.empty:
        st.info("Keine Investitionen im ausgewählten Zeitraum.")
    else:
        total_buys = abs(investment_df[investment_df["Betrag"] < 0]["Betrag"].sum())
        total_sells = investment_df[investment_df["Betrag"] > 0]["Betrag"].sum()
        net_invested = total_buys - total_sells
        tx_count = len(investment_df)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Käufe gesamt", f"€{total_buys:,.2f}")
        with col2:
            st.metric("Verkäufe gesamt", f"€{total_sells:,.2f}")
        with col3:
            st.metric("Netto investiert", f"€{net_invested:,.2f}")
        with col4:
            st.metric("Transaktionen", tx_count)

        st.divider()

        investment_monthly = (
            investment_df.groupby("Monat")
            .agg({"Betrag": lambda x: (x[x < 0].sum(), x[x > 0].sum())})
            .reset_index()
        )
        investment_monthly = investment_monthly.sort_values("Monat")
        investment_monthly["Käufe"] = investment_monthly["Betrag"].apply(lambda x: abs(x[0]))
        investment_monthly["Verkäufe"] = investment_monthly["Betrag"].apply(lambda x: x[1])
        investment_monthly["Netto investiert"] = (
            investment_monthly["Käufe"] - investment_monthly["Verkäufe"]
        )
        investment_monthly["Kumuliert"] = investment_monthly["Netto investiert"].cumsum()
        investment_monthly["Monat_str"] = investment_monthly["Monat"].astype(str)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Monatliche Käufe/Verkäufe")
            inv_fig = go.Figure()
            inv_fig.add_trace(
                go.Bar(
                    name="Käufe",
                    x=investment_monthly["Monat_str"],
                    y=investment_monthly["Käufe"],
                    marker_color="#ff7f0e",
                )
            )
            inv_fig.add_trace(
                go.Bar(
                    name="Verkäufe",
                    x=investment_monthly["Monat_str"],
                    y=investment_monthly["Verkäufe"],
                    marker_color="#1f77b4",
                )
            )
            inv_fig.update_layout(barmode="group", xaxis_title="Monat", yaxis_title="Betrag (€)")
            st.plotly_chart(inv_fig, width="stretch")

        with col2:
            st.subheader("Kumuliert netto investiert")
            cum_fig = px.line(
                investment_monthly,
                x="Monat_str",
                y="Kumuliert",
                markers=True,
                labels={"Monat_str": "Monat", "Kumuliert": "Betrag (€)"},
            )
            cum_fig.update_traces(line_color="#2ca02c")
            st.plotly_chart(cum_fig, width="stretch")

        st.divider()

        st.subheader("Transaktionen")
        investment_table = investment_df.copy()
        investment_table["Datum_str"] = investment_table["Datum"].dt.strftime("%d.%m.%Y")
        investment_table["Typ"] = np.where(investment_table["Betrag"] < 0, "Kauf", "Verkauf")
        investment_table["Betrag_abs"] = investment_table["Betrag"].abs()
        investment_table = investment_table.sort_values("Datum", ascending=False)

        st.dataframe(
            investment_table[["Datum_str", "Beschreibung", "Konto", "Typ", "Betrag_abs"]],
            width="stretch",
            hide_index=True,
            column_config={
                "Datum_str": st.column_config.TextColumn("Datum"),
                "Beschreibung": st.column_config.TextColumn("Beschreibung", width="large"),
                "Konto": st.column_config.TextColumn("Konto"),
                "Typ": st.column_config.TextColumn("Typ"),
                "Betrag_abs": st.column_config.NumberColumn("Betrag", format="€%.2f"),
            },
        )

        st.divider()

        st.subheader("Top-Gegenparteien")
        top_merchants = (
            investment_table.groupby("Beschreibung_cluster")["Betrag_abs"]
            .agg(["sum", "count"])
            .sort_values("sum", ascending=False)
            .head(10)
            .reset_index()
        )
        top_merchants.columns = ["Beschreibung", "Gesamt", "Anzahl"]
        st.dataframe(
            top_merchants,
            width="stretch",
            hide_index=True,
            column_config={
                "Gesamt": st.column_config.NumberColumn(format="€%.2f"),
            },
        )

elif active_tab == "Jahresvergleich":
    st.subheader("Jahresvergleich")

    if len(available_years) < 2:
        st.info("Mindestens 2 Jahre Daten für Vergleich erforderlich.")
    else:
        # Year selector for comparison
        col1, col2 = st.columns(2)
        with col1:
            year1 = st.selectbox("Jahr vergleichen", available_years, index=0, key="year1")
        with col2:
            year2 = st.selectbox(
                "mit Jahr",
                available_years,
                index=min(1, len(available_years) - 1),
                key="year2",
            )

        # Filter data for selected years (using combined_df to ignore date range filter)
        compare_df = combined_df.copy()
        if selected_account != "Alle":
            compare_df = compare_df[compare_df["Konto"] == selected_account]
        if selected_category != "Alle":
            compare_df = compare_df[compare_df["Kategorie"] == selected_category]

        year1_df = compare_df[compare_df["Jahr"] == year1]
        year2_df = compare_df[compare_df["Jahr"] == year2]

        # Exclude non-spending categories for accurate totals
        year1_real = year1_df[~year1_df["Kategorie"].isin(non_spend_categories)]
        year2_real = year2_df[~year2_df["Kategorie"].isin(non_spend_categories)]

        # Annual totals comparison
        st.subheader("Jahresübersicht")
        col1, col2, col3 = st.columns(3)

        year1_income = year1_real[year1_real["Betrag"] > 0]["Betrag"].sum()
        year1_expenses = abs(year1_real[year1_real["Betrag"] < 0]["Betrag"].sum())
        year2_income = year2_real[year2_real["Betrag"] > 0]["Betrag"].sum()
        year2_expenses = abs(year2_real[year2_real["Betrag"] < 0]["Betrag"].sum())

        # Calculate differences
        income_diff = year1_income - year2_income
        expenses_diff = year1_expenses - year2_expenses
        year1_net = year1_income - year1_expenses
        year2_net = year2_income - year2_expenses
        net_diff = year1_net - year2_net

        with col1:
            # More income is good (green up, red down)
            sign = "+" if income_diff >= 0 else ""
            st.metric(
                f"Einnahmen {year1}",
                f"€{year1_income:,.2f}",
                delta=f"{sign}{income_diff:,.0f} €",
                help=f"{year2}: €{year2_income:,.2f}",
            )
        with col2:
            # Less expenses is good (inverse: green down, red up)
            sign = "+" if expenses_diff >= 0 else ""
            st.metric(
                f"Ausgaben {year1}",
                f"€{year1_expenses:,.2f}",
                delta=f"{sign}{expenses_diff:,.0f} €",
                delta_color="inverse",
                help=f"{year2}: €{year2_expenses:,.2f}",
            )
        with col3:
            # Higher net is good (green up, red down)
            sign = "+" if net_diff >= 0 else ""
            st.metric(
                f"Netto {year1}",
                f"€{year1_net:,.2f}",
                delta=f"{sign}{net_diff:,.0f} €",
                help=f"{year2}: €{year2_net:,.2f}",
            )

        st.divider()

        # Monthly comparison chart
        st.subheader("Monatlicher Ausgabenvergleich")
        month_names = [
            "Jan",
            "Feb",
            "Mär",
            "Apr",
            "Mai",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Okt",
            "Nov",
            "Dez",
        ]

        year1_monthly = (
            year1_df[(year1_df["Betrag"] < 0) & (~year1_df["Kategorie"].isin(non_spend_categories))]
            .groupby("MonthNum")["Betrag"]
            .sum()
            .abs()
            .reindex(range(1, 13), fill_value=0)
        )
        year2_monthly = (
            year2_df[(year2_df["Betrag"] < 0) & (~year2_df["Kategorie"].isin(non_spend_categories))]
            .groupby("MonthNum")["Betrag"]
            .sum()
            .abs()
            .reindex(range(1, 13), fill_value=0)
        )

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                name=str(year1),
                x=month_names,
                y=year1_monthly.values,
                marker_color="#1f77b4",
            )
        )
        fig.add_trace(
            go.Bar(
                name=str(year2),
                x=month_names,
                y=year2_monthly.values,
                marker_color="#ff7f0e",
            )
        )
        fig.update_layout(barmode="group", xaxis_title="Monat", yaxis_title="Ausgaben (€)")
        st.plotly_chart(fig, width="stretch")

        st.divider()

        # Category comparison
        st.subheader("Ausgaben nach Kategorie im Vergleich")

        year1_cat = (
            year1_df[(year1_df["Betrag"] < 0) & (~year1_df["Kategorie"].isin(non_spend_categories))]
            .groupby("Kategorie")["Betrag"]
            .sum()
            .abs()
            .sort_values(ascending=False)
        )
        year2_cat = (
            year2_df[(year2_df["Betrag"] < 0) & (~year2_df["Kategorie"].isin(non_spend_categories))]
            .groupby("Kategorie")["Betrag"]
            .sum()
            .abs()
            .sort_values(ascending=False)
        )

        # Filter out non-spending categories
        year1_cat = year1_cat[~year1_cat.index.isin(non_spend_categories)]
        year2_cat = year2_cat[~year2_cat.index.isin(non_spend_categories)]

        # Combine categories from both years
        all_cats = sorted(set(year1_cat.index) | set(year2_cat.index))
        comparison_data = []
        for cat in all_cats:
            y1_val = year1_cat.get(cat, 0)
            y2_val = year2_cat.get(cat, 0)
            diff = y1_val - y2_val
            pct_change = ((y1_val - y2_val) / y2_val * 100) if y2_val > 0 else 0
            comparison_data.append(
                {
                    "Kategorie": cat,
                    f"{year1}": y1_val,
                    f"{year2}": y2_val,
                    "Differenz": diff,
                    "Änderung %": pct_change,
                }
            )

        comparison_df = pd.DataFrame(comparison_data)
        comparison_df = comparison_df.sort_values(f"{year1}", ascending=False)

        st.dataframe(
            comparison_df,
            width="stretch",
            height=400,
            column_config={
                f"{year1}": st.column_config.NumberColumn(format="€%.2f"),
                f"{year2}": st.column_config.NumberColumn(format="€%.2f"),
                "Differenz": st.column_config.NumberColumn(format="€%.2f"),
                "Änderung %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

        # Bar chart for top categories
        top_cats = comparison_df.head(10)
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                name=str(year1),
                x=top_cats["Kategorie"],
                y=top_cats[f"{year1}"],
                marker_color="#1f77b4",
            )
        )
        fig.add_trace(
            go.Bar(
                name=str(year2),
                x=top_cats["Kategorie"],
                y=top_cats[f"{year2}"],
                marker_color="#ff7f0e",
            )
        )
        fig.update_layout(barmode="group", xaxis_title="Kategorie", yaxis_title="Ausgaben (€)")
        st.plotly_chart(fig, width="stretch")

elif active_tab == "Typischer Monat":
    st.subheader("Typischer Monat")
    st.write("Durchschnittliche monatliche Einnahmen und Ausgaben im ausgewählten Zeitraum.")

    # Calculate number of months in the filtered period
    if len(date_range) == 2:
        start_date = pd.Timestamp(date_range[0])
        end_date = pd.Timestamp(date_range[1])
        num_months = (
            (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
        )
    else:
        num_months = filtered_df["Monat"].nunique()
    if num_months == 0:
        num_months = 1

    # Filter out non-spending categories for real calculations
    real_df = filtered_df[~filtered_df["Kategorie"].isin(non_spend_categories)]

    # Calculate averages
    avg_income = real_df[real_df["Betrag"] > 0]["Betrag"].sum() / num_months
    avg_expenses = abs(real_df[real_df["Betrag"] < 0]["Betrag"].sum()) / num_months
    avg_net = avg_income - avg_expenses

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ø Monatliche Einnahmen", f"€{avg_income:,.2f}")
    with col2:
        st.metric("Ø Monatliche Ausgaben", f"€{avg_expenses:,.2f}")
    with col3:
        st.metric(
            "Ø Monatliche Ersparnis",
            f"€{avg_net:,.2f}",
            delta_color="normal" if avg_net >= 0 else "inverse",
        )

    st.divider()

    # Income breakdown
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Monatliche Einnahmen")
        income_df = real_df[real_df["Betrag"] > 0].copy()
        income_by_cat = income_df.groupby("Kategorie")["Betrag"].sum().sort_values(ascending=False)
        income_monthly = (income_by_cat / num_months).round(2)

        income_table = pd.DataFrame(
            {"Kategorie": income_monthly.index, "Monatsdurchschnitt": income_monthly.values}
        )
        st.dataframe(
            income_table,
            width="stretch",
            hide_index=True,
            column_config={
                "Monatsdurchschnitt": st.column_config.NumberColumn(format="€%.2f"),
            },
        )

        # Pie chart for income
        if not income_monthly.empty:
            fig = px.pie(
                values=income_monthly.values,
                names=income_monthly.index,
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width="stretch")

    with col2:
        st.subheader("Monatliche Ausgaben")
        expenses_df = real_df[real_df["Betrag"] < 0].copy()
        expenses_df["Betrag_abs"] = expenses_df["Betrag"].abs()
        expenses_by_cat = (
            expenses_df.groupby("Kategorie")["Betrag_abs"].sum().sort_values(ascending=False)
        )
        expenses_monthly = (expenses_by_cat / num_months).round(2)

        expenses_table = pd.DataFrame(
            {"Kategorie": expenses_monthly.index, "Monatsdurchschnitt": expenses_monthly.values}
        )
        st.dataframe(
            expenses_table,
            width="stretch",
            hide_index=True,
            column_config={
                "Monatsdurchschnitt": st.column_config.NumberColumn(format="€%.2f"),
            },
        )

        # Pie chart for expenses
        if not expenses_monthly.empty:
            fig = px.pie(
                values=expenses_monthly.values,
                names=expenses_monthly.index,
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width="stretch")

    st.divider()

    # Waterfall chart showing budget flow
    st.subheader("Monatlicher Cashflow")

    # Create waterfall data
    waterfall_data = [{"Kategorie": "Einnahmen", "Betrag": avg_income, "Type": "income"}]

    # Add top expense categories
    top_expenses = expenses_monthly.head(10)
    for cat, amount in top_expenses.items():
        waterfall_data.append({"Kategorie": cat, "Betrag": -amount, "Type": "expense"})

    # Add remaining expenses
    other_expenses = expenses_monthly.tail(-10).sum() if len(expenses_monthly) > 10 else 0
    if other_expenses > 0:
        waterfall_data.append(
            {"Kategorie": "Sonstige", "Betrag": -other_expenses, "Type": "expense"}
        )

    waterfall_data.append({"Kategorie": "Ersparnis", "Betrag": avg_net, "Type": "total"})

    # Create waterfall chart
    fig = go.Figure(
        go.Waterfall(
            name="Monatsbudget",
            orientation="v",
            measure=["absolute"] + ["relative"] * (len(waterfall_data) - 2) + ["total"],
            x=[d["Kategorie"] for d in waterfall_data],
            y=[d["Betrag"] for d in waterfall_data],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "#28a745"}},
            decreasing={"marker": {"color": "#dc3545"}},
            totals={"marker": {"color": "#1f77b4"}},
        )
    )
    fig.update_layout(
        title="Wohin fließt dein Einkommen?",
        yaxis_title="Betrag (€)",
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")

elif active_tab == "Einstellungen":
    st.subheader("Kategorien verwalten")

    # Placeholder for success messages
    settings_message = st.empty()

    # Show success message if flag is set (from previous save)
    if "save_success_msg" in st.session_state:
        msg = st.session_state.save_success_msg
        settings_message.success(msg)
        st.toast(msg, icon="✅")
        del st.session_state.save_success_msg

    # Load current categories
    categories_config = load_categories()

    # Add new category section
    st.write("**Neue Kategorie hinzufügen**")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_category = st.text_input(
            "Kategoriename",
            key="new_cat_name",
            label_visibility="collapsed",
            placeholder="Neue Kategorie...",
        )
    with col2:
        if st.button("Hinzufügen", key="add_cat_btn"):
            if new_category and new_category not in categories_config["rules"]:
                categories_config["rules"][new_category] = []
                save_categories(categories_config)
                st.session_state.save_success_msg = f"Kategorie '{new_category}' hinzugefügt."
                st.rerun()
            elif new_category in categories_config["rules"]:
                st.error("Kategorie existiert bereits")

    st.divider()

    # Edit existing categories
    st.write("**Kategorien bearbeiten**")

    for category, keywords in sorted(categories_config["rules"].items()):
        # Show current keywords - only set initial value if not in session state
        text_key = f"keywords_{category}"

        # Initialize session state with file value only on first load
        if text_key not in st.session_state:
            st.session_state[text_key] = "\n".join(keywords)

        # Count from session state for accurate display
        current_count = len([k for k in st.session_state[text_key].split("\n") if k.strip()])

        with st.expander(f"**{category}** ({current_count} Schlüsselwörter)"):
            keywords_text = st.text_area(
                "Schlüsselwörter (eins pro Zeile)",
                key=text_key,
                height=150,
            )

            # Count keywords from current text (not file) to show accurate count
            current_keywords = [k.strip() for k in keywords_text.split("\n") if k.strip()]

            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                if st.button("Speichern", key=f"save_{category}"):
                    # Reload categories to get fresh state and save
                    fresh_config = load_categories()
                    fresh_config["rules"][category] = current_keywords
                    save_categories(fresh_config)

                    msg = f"'{category}' gespeichert mit {len(current_keywords)} Schlüsselwörtern!"
                    settings_message.success(msg)
                    st.toast(msg, icon="✅")
            with col2:
                new_name = st.text_input(
                    "Umbenennen",
                    value=category,
                    key=f"rename_{category}",
                    label_visibility="collapsed",
                )
            with col3:
                if st.button("Umbenennen", key=f"rename_btn_{category}"):
                    if new_name and new_name != category:
                        fresh_config = load_categories()
                        if new_name not in fresh_config["rules"]:
                            fresh_config["rules"][new_name] = fresh_config["rules"].pop(category)
                            save_categories(fresh_config)
                            st.session_state.save_success_msg = (
                                f"Kategorie '{category}' umbenannt zu '{new_name}'."
                            )
                            st.rerun()

            if st.button("Löschen", key=f"delete_{category}", type="secondary"):
                fresh_config = load_categories()
                del fresh_config["rules"][category]
                save_categories(fresh_config)
                st.session_state.save_success_msg = f"Kategorie '{category}' gelöscht."
                st.rerun()

    st.divider()

    # Transaction clustering section
    st.write("**Transaktionen clustern**")
    st.caption("Muster sind nicht case-sensitiv. '*' funktioniert als Platzhalter.")

    clusters = categories_config.get("clusters", {})

    st.write("Neues Cluster hinzufügen")
    new_cluster_name = st.text_input(
        "Cluster-Name",
        key="new_cluster_name",
        label_visibility="collapsed",
        placeholder="z.B. ChatGPT Subscription",
    )
    new_cluster_patterns = st.text_area(
        "Muster (eins pro Zeile)",
        key="new_cluster_patterns",
        height=80,
        label_visibility="collapsed",
        placeholder="OPENAI *CHATGPT SUBSCR\nCHATGPT SUBSCRIPTION",
    )
    if st.button("Cluster hinzufügen", key="add_cluster_btn"):
        patterns = [p.strip() for p in new_cluster_patterns.split("\n") if p.strip()]
        if not new_cluster_name.strip():
            st.error("Bitte einen Cluster-Namen angeben.")
        elif not patterns:
            st.error("Bitte mindestens ein Muster angeben.")
        else:
            fresh_config = load_categories()
            fresh_config.setdefault("clusters", {})
            if new_cluster_name in fresh_config["clusters"]:
                st.error("Cluster existiert bereits.")
            else:
                fresh_config["clusters"][new_cluster_name] = patterns
                save_categories(fresh_config)
                st.session_state.save_success_msg = f"Cluster '{new_cluster_name}' hinzugefügt."
                st.rerun()

    if clusters:
        for cluster_name, patterns in sorted(clusters.items()):
            pattern_key = f"cluster_patterns_{cluster_name}"
            if pattern_key not in st.session_state:
                st.session_state[pattern_key] = "\n".join(patterns)

            current_count = len([p for p in st.session_state[pattern_key].split("\n") if p.strip()])
            with st.expander(f"**{cluster_name}** ({current_count} Muster)"):
                patterns_text = st.text_area(
                    "Muster (eins pro Zeile)",
                    key=pattern_key,
                    height=120,
                )
                current_patterns = [p.strip() for p in patterns_text.split("\n") if p.strip()]

                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    if st.button("Speichern", key=f"save_cluster_{cluster_name}"):
                        if not current_patterns:
                            st.error("Bitte mindestens ein Muster angeben.")
                        else:
                            fresh_config = load_categories()
                            fresh_config.setdefault("clusters", {})
                            if cluster_name in fresh_config["clusters"]:
                                fresh_config["clusters"][cluster_name] = current_patterns
                                save_categories(fresh_config)
                                msg = f"Cluster '{cluster_name}' gespeichert."
                                settings_message.success(msg)
                                st.toast(msg, icon="✅")
                with col2:
                    new_name = st.text_input(
                        "Umbenennen",
                        value=cluster_name,
                        key=f"rename_cluster_{cluster_name}",
                        label_visibility="collapsed",
                    )
                with col3:
                    if st.button("Umbenennen", key=f"rename_cluster_btn_{cluster_name}"):
                        if new_name and new_name != cluster_name:
                            fresh_config = load_categories()
                            fresh_config.setdefault("clusters", {})
                            if new_name not in fresh_config["clusters"]:
                                fresh_config["clusters"][new_name] = fresh_config["clusters"].pop(
                                    cluster_name
                                )
                                save_categories(fresh_config)
                                st.session_state.save_success_msg = (
                                    f"Cluster '{cluster_name}' umbenannt zu '{new_name}'."
                                )
                                st.rerun()

                if st.button(
                    "Löschen",
                    key=f"delete_cluster_{cluster_name}",
                    type="secondary",
                ):
                    fresh_config = load_categories()
                    fresh_config.setdefault("clusters", {})
                    if cluster_name in fresh_config["clusters"]:
                        del fresh_config["clusters"][cluster_name]
                        save_categories(fresh_config)
                        st.session_state.save_success_msg = f"Cluster '{cluster_name}' gelöscht."
                        st.rerun()

                # Show transactions matching this cluster
                st.divider()
                st.write("**Zugehörige Transaktionen:**")
                cluster_transactions = filtered_df[
                    filtered_df["Beschreibung_cluster"] == cluster_name
                ].copy()
                if not cluster_transactions.empty:
                    cluster_transactions["Datum_str"] = cluster_transactions["Datum"].dt.strftime(
                        "%d.%m.%Y"
                    )
                    cluster_transactions = cluster_transactions.sort_values(
                        "Datum", ascending=False
                    )
                    st.dataframe(
                        cluster_transactions[
                            ["Datum_str", "Beschreibung", "Kategorie", "Konto", "Betrag"]
                        ],
                        width="stretch",
                        height=min(300, 35 * len(cluster_transactions) + 38),
                        hide_index=True,
                        column_config={
                            "Datum_str": st.column_config.TextColumn("Datum"),
                            "Beschreibung": st.column_config.TextColumn(
                                "Beschreibung", width="large"
                            ),
                            "Betrag": st.column_config.NumberColumn("Betrag", format="€%.2f"),
                        },
                    )
                    total = cluster_transactions["Betrag"].sum()
                    count = len(cluster_transactions)
                    st.caption(f"{count} Transaktionen, Summe: €{total:,.2f}")
                else:
                    st.caption("Keine Transaktionen im gewählten Zeitraum.")
    else:
        st.caption("Noch keine Cluster definiert.")

    st.divider()

    # IBAN rules section
    st.write("**IBAN-Regeln**")
    st.caption("Spezielle Kategorisierung basierend auf IBAN (z.B. eigene Konten, Gehalt)")

    iban_rules = categories_config.get("iban_rules", {})
    all_categories = ["Umbuchungen", "Gehalt"] + sorted(categories_config["rules"].keys())

    for iban, cat in list(iban_rules.items()):
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.text(iban)
        with col2:
            new_cat = st.selectbox(
                "Kategorie",
                all_categories,
                index=all_categories.index(cat) if cat in all_categories else 0,
                key=f"iban_cat_{iban}",
                label_visibility="collapsed",
            )
            if new_cat != cat:
                categories_config["iban_rules"][iban] = new_cat
                save_categories(categories_config)
                st.session_state.save_success_msg = f"IBAN-Regel für {iban} aktualisiert."
                st.rerun()
        with col3:
            if st.button("X", key=f"del_iban_{iban}"):
                del categories_config["iban_rules"][iban]
                save_categories(categories_config)
                st.session_state.save_success_msg = f"IBAN-Regel für {iban} gelöscht."
                st.rerun()

    # Add new IBAN rule
    st.write("Neue IBAN-Regel:")
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        new_iban = st.text_input(
            "IBAN", key="new_iban", label_visibility="collapsed", placeholder="DE..."
        )
    with col2:
        new_iban_cat = st.selectbox(
            "Kategorie", all_categories, key="new_iban_cat", label_visibility="collapsed"
        )
    with col3:
        if st.button("Hinzufügen", key="add_iban_btn"):
            if new_iban and new_iban.upper() not in iban_rules:
                categories_config["iban_rules"][new_iban.upper()] = new_iban_cat
                save_categories(categories_config)
                st.session_state.save_success_msg = (
                    f"IBAN-Regel für {new_iban.upper()} hinzugefügt."
                )
                st.rerun()

    st.divider()

    # Manual overrides section
    st.write("**Manuelle Zuordnungen**")
    overrides = categories_config.get("overrides", {})
    if overrides:
        st.caption(f"{len(overrides)} Transaktionen manuell zugeordnet")
        if st.button("Alle manuellen Zuordnungen löschen"):
            categories_config["overrides"] = {}
            save_categories(categories_config)
            st.session_state.save_success_msg = "Manuelle Zuordnungen gelöscht."
            st.rerun()
    else:
        st.caption(
            "Keine manuellen Zuordnungen. Klicke auf eine Transaktion in der Übersicht, um sie manuell zuzuordnen."  # noqa: E501
        )
