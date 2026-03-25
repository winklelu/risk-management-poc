"""
Clinical Trial Risk Management Dashboard
Shiny for Python application with three tabs:
    Tab 1: Summary (heatmap + stat cards)
    Tab 2: QTL Details
    Tab 3: KRI Details
"""

import os
import yaml
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from shiny import App, ui, render, reactive, session

# ── Paths ────────────────────────────────────────────────────────────────────
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
CONFIG_DIR = os.path.join(APP_DIR, "config")

# ── Colour palette ────────────────────────────────────────────────────────────
STATUS_COLORS = {
    "Green": "#2ecc71",
    "Yellow": "#f39c12",
    "Red": "#e74c3c",
}

STATUS_NUMERIC = {"Green": 0, "Yellow": 1, "Red": 2}

# ── Data loaders ─────────────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "risk_summary.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"risk_summary.csv not found at {path}.\n"
            "Run: cd python && python pipeline.py"
        )
    return pd.read_csv(path)


def load_config() -> dict:
    path = os.path.join(CONFIG_DIR, "indicators.yaml")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def build_indicator_meta(config: dict) -> dict:
    """Return dict keyed by indicator_id with description & justification."""
    meta = {}
    for group in ("qtl", "kri"):
        for item in config.get(group, []):
            meta[item["id"]] = {
                "name": item["name"],
                "description": item.get("description", ""),
                "justification": item.get("justification", ""),
                "category": item.get("category", ""),
                "formula": item.get("formula", ""),
                "unit": item.get("unit", "%"),
            }
    return meta


# ── Load once at module level ─────────────────────────────────────────────────
df_all = load_data()
config = load_config()
IND_META = build_indicator_meta(config)

ALL_SITES = sorted(df_all["SITEID"].unique().tolist())
ALL_INDICATORS = sorted(df_all["indicator_id"].unique().tolist())
QTL_INDICATORS = sorted(df_all[df_all["indicator_type"] == "QTL"]["indicator_id"].unique().tolist())
KRI_INDICATORS = sorted(df_all[df_all["indicator_type"] == "KRI"]["indicator_id"].unique().tolist())
QTL_CATEGORIES = sorted(df_all[df_all["indicator_type"] == "QTL"]["category"].unique().tolist())
KRI_CATEGORIES = sorted(df_all[df_all["indicator_type"] == "KRI"]["category"].unique().tolist())


# ── Helper: indicator label for selectize ────────────────────────────────────
def ind_choices(ids: list[str]) -> dict:
    return {i: f"{i} – {IND_META.get(i, {}).get('name', i)}" for i in ids}


# ── Heatmap builder ───────────────────────────────────────────────────────────

def build_heatmap(df: pd.DataFrame) -> go.Figure:
    pivot = df.pivot_table(
        index="indicator_id", columns="SITEID", values="status", aggfunc="first"
    ).fillna("Green")

    indicators = sorted(pivot.index.tolist())
    sites = sorted(pivot.columns.tolist())

    z_num = pivot.loc[indicators, sites].applymap(lambda s: STATUS_NUMERIC.get(s, 0)).values
    z_text = pivot.loc[indicators, sites].values

    colorscale = [
        [0.0, STATUS_COLORS["Green"]],
        [0.5, STATUS_COLORS["Yellow"]],
        [1.0, STATUS_COLORS["Red"]],
    ]

    hovertext = []
    for i, ind in enumerate(indicators):
        row_txt = []
        for j, site in enumerate(sites):
            val_row = df[(df["indicator_id"] == ind) & (df["SITEID"] == site)]
            if not val_row.empty:
                v = val_row["value"].iloc[0]
                status = val_row["status"].iloc[0]
                row_txt.append(f"Site: {site}<br>Indicator: {ind}<br>Value: {v:.1f}%<br>Status: {status}")
            else:
                row_txt.append(f"Site: {site}<br>Indicator: {ind}<br>No data")
        hovertext.append(row_txt)

    fig = go.Figure(
        go.Heatmap(
            z=z_num,
            x=sites,
            y=indicators,
            text=z_text,
            texttemplate="%{text}",
            colorscale=colorscale,
            zmin=0,
            zmax=2,
            showscale=False,
            hovertext=hovertext,
            hoverinfo="text",
            xgap=2,
            ygap=2,
        )
    )

    fig.update_layout(
        title=dict(text="Site × Indicator Risk Heatmap", font=dict(size=16, color="#ecf0f1")),
        paper_bgcolor="#1e2535",
        plot_bgcolor="#1e2535",
        font=dict(color="#ecf0f1"),
        xaxis=dict(title="Site", side="bottom", tickfont=dict(size=11)),
        yaxis=dict(title="Indicator", autorange="reversed"),
        margin=dict(l=120, r=20, t=60, b=60),
        height=420,
    )

    return fig


def build_bar_chart(df_ind: pd.DataFrame, indicator_id: str) -> go.Figure:
    """Bar chart of indicator values across sites with threshold lines."""
    if df_ind.empty:
        return go.Figure()

    row0 = df_ind.iloc[0]
    yellow_thresh = row0["threshold_yellow"]
    red_thresh = row0["threshold_red"]

    bar_colors = [STATUS_COLORS.get(s, "#aaa") for s in df_ind["status"]]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df_ind["SITEID"],
            y=df_ind["value"],
            marker_color=bar_colors,
            text=[f"{v:.1f}%" for v in df_ind["value"]],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Value: %{y:.1f}%<extra></extra>",
            name="Value",
        )
    )

    # Yellow threshold line
    fig.add_hline(
        y=yellow_thresh,
        line_dash="dash",
        line_color=STATUS_COLORS["Yellow"],
        annotation_text=f"Yellow ({yellow_thresh}%)",
        annotation_position="top right",
        annotation_font_color=STATUS_COLORS["Yellow"],
    )

    # Red threshold line
    fig.add_hline(
        y=red_thresh,
        line_dash="dash",
        line_color=STATUS_COLORS["Red"],
        annotation_text=f"Red ({red_thresh}%)",
        annotation_position="bottom right",
        annotation_font_color=STATUS_COLORS["Red"],
    )

    ind_name = IND_META.get(indicator_id, {}).get("name", indicator_id)

    fig.update_layout(
        title=dict(text=f"{indicator_id}: {ind_name}", font=dict(size=14, color="#ecf0f1")),
        paper_bgcolor="#1e2535",
        plot_bgcolor="#252e3f",
        font=dict(color="#ecf0f1"),
        xaxis=dict(title="Site", tickfont=dict(size=11), gridcolor="#3a4456"),
        yaxis=dict(title="Value (%)", gridcolor="#3a4456"),
        margin=dict(l=60, r=60, t=60, b=60),
        height=380,
        showlegend=False,
    )

    return fig


# ── Stat card helper ──────────────────────────────────────────────────────────

def stat_card(label: str, value, color: str = "#3498db") -> ui.Tag:
    return ui.div(
        ui.div(str(value), style=f"font-size:2rem; font-weight:700; color:{color};"),
        ui.div(label, style="font-size:0.85rem; color:#bdc3c7; margin-top:4px;"),
        style=(
            "background:#252e3f; border-radius:8px; padding:16px 24px;"
            "text-align:center; min-width:130px; flex:1;"
            f"border-top:3px solid {color};"
        ),
    )


# ── Indicator info panel ──────────────────────────────────────────────────────

def indicator_info_panel(indicator_id: str) -> ui.Tag:
    meta = IND_META.get(indicator_id, {})
    return ui.div(
        ui.h5(f"{indicator_id}: {meta.get('name', '')}",
              style="color:#3498db; margin-bottom:8px;"),
        ui.p(ui.strong("Description: "), meta.get("description", "—"),
             style="margin-bottom:6px;"),
        ui.p(ui.strong("Justification: "), meta.get("justification", "—"),
             style="margin-bottom:6px;"),
        ui.p(ui.strong("Formula: "), ui.code(meta.get("formula", "—")),
             style="margin-bottom:0;"),
        style=(
            "background:#1a2233; border-left:4px solid #3498db;"
            "padding:16px; border-radius:4px; color:#ecf0f1;"
            "font-size:0.9rem;"
        ),
    )


# ── UI ────────────────────────────────────────────────────────────────────────

app_ui = ui.page_fluid(
    ui.head_content(
        ui.tags.link(rel="stylesheet", href="styles.css"),
        ui.tags.script(src="https://cdn.plot.ly/plotly-2.27.0.min.js"),
    ),
    # Navbar
    ui.div(
        ui.div(
            ui.span("CLINICAL TRIAL", style="font-size:0.75rem; color:#7f8c8d; letter-spacing:2px; display:block;"),
            ui.span("Risk Management Dashboard", style="font-size:1.1rem; font-weight:700; color:#ecf0f1;"),
            style="flex:1;",
        ),
        ui.div(
            ui.span("STUDY001", style=(
                "background:#2c3e50; color:#3498db; padding:4px 12px;"
                "border-radius:4px; font-size:0.85rem; font-weight:600;"
            )),
            style="display:flex; align-items:center;",
        ),
        style=(
            "display:flex; align-items:center; justify-content:space-between;"
            "background:#141b2d; padding:12px 24px; margin-bottom:0;"
            "border-bottom:2px solid #3498db;"
        ),
    ),

    ui.navset_tab(
        # ── Tab 1: Summary ────────────────────────────────────────────────────
        ui.nav_panel(
            "Summary",
            ui.layout_sidebar(
                ui.sidebar(
                    ui.h6("FILTERS", style="color:#7f8c8d; letter-spacing:1px; margin-bottom:12px;"),
                    ui.input_select(
                        "sum_type", "Indicator Type",
                        choices={"All": "All", "QTL": "QTL", "KRI": "KRI"},
                        selected="All",
                    ),
                    ui.input_selectize(
                        "sum_indicators", "Indicators",
                        choices=ind_choices(ALL_INDICATORS),
                        selected=ALL_INDICATORS,
                        multiple=True,
                    ),
                    ui.input_selectize(
                        "sum_sites", "Sites",
                        choices=ALL_SITES,
                        selected=ALL_SITES,
                        multiple=True,
                    ),
                    bg="#1e2535",
                    width=260,
                ),
                ui.div(
                    # Stat cards row
                    ui.div(
                        ui.output_ui("card_total_sites"),
                        ui.output_ui("card_red_sites"),
                        ui.output_ui("card_yellow_sites"),
                        ui.output_ui("card_total_indicators"),
                        style="display:flex; gap:16px; flex-wrap:wrap; margin-bottom:24px;",
                    ),
                    # Heatmap
                    ui.output_ui("heatmap_plot"),
                    # Site risk table
                    ui.h5("Site Risk Overview", style="color:#ecf0f1; margin-top:24px; margin-bottom:12px;"),
                    ui.output_data_frame("site_risk_table"),
                    style="padding:20px; background:#16213e;",
                ),
            ),
        ),

        # ── Tab 2: QTL Details ────────────────────────────────────────────────
        ui.nav_panel(
            "QTL Details",
            ui.layout_sidebar(
                ui.sidebar(
                    ui.h6("FILTERS", style="color:#7f8c8d; letter-spacing:1px; margin-bottom:12px;"),
                    ui.input_select(
                        "qtl_cat", "Category",
                        choices={"All": "All", **{c: c for c in QTL_CATEGORIES}},
                        selected="All",
                    ),
                    ui.input_select(
                        "qtl_indicator", "Indicator",
                        choices=ind_choices(QTL_INDICATORS),
                        selected=QTL_INDICATORS[0] if QTL_INDICATORS else None,
                    ),
                    ui.input_selectize(
                        "qtl_sites", "Sites",
                        choices=ALL_SITES,
                        selected=ALL_SITES,
                        multiple=True,
                    ),
                    bg="#1e2535",
                    width=260,
                ),
                ui.div(
                    ui.output_ui("qtl_bar_chart"),
                    ui.h5("Indicator Detail", style="color:#ecf0f1; margin-top:24px; margin-bottom:12px;"),
                    ui.output_data_frame("qtl_detail_table"),
                    ui.div(ui.output_ui("qtl_info_panel"), style="margin-top:20px;"),
                    style="padding:20px; background:#16213e;",
                ),
            ),
        ),

        # ── Tab 3: KRI Details ────────────────────────────────────────────────
        ui.nav_panel(
            "KRI Details",
            ui.layout_sidebar(
                ui.sidebar(
                    ui.h6("FILTERS", style="color:#7f8c8d; letter-spacing:1px; margin-bottom:12px;"),
                    ui.input_select(
                        "kri_cat", "Category",
                        choices={"All": "All", **{c: c for c in KRI_CATEGORIES}},
                        selected="All",
                    ),
                    ui.input_select(
                        "kri_indicator", "Indicator",
                        choices=ind_choices(KRI_INDICATORS),
                        selected=KRI_INDICATORS[0] if KRI_INDICATORS else None,
                    ),
                    ui.input_selectize(
                        "kri_sites", "Sites",
                        choices=ALL_SITES,
                        selected=ALL_SITES,
                        multiple=True,
                    ),
                    bg="#1e2535",
                    width=260,
                ),
                ui.div(
                    ui.output_ui("kri_bar_chart"),
                    ui.h5("Indicator Detail", style="color:#ecf0f1; margin-top:24px; margin-bottom:12px;"),
                    ui.output_data_frame("kri_detail_table"),
                    ui.div(ui.output_ui("kri_info_panel"), style="margin-top:20px;"),
                    style="padding:20px; background:#16213e;",
                ),
            ),
        ),

        id="main_tabs",
        selected="Summary",
    ),

    style="background:#16213e; min-height:100vh; padding:0;",
)


# ── Server ────────────────────────────────────────────────────────────────────

def server(input, output, session):

    # ── Reactive data filters ─────────────────────────────────────────────────

    @reactive.calc
    def filtered_summary():
        df = df_all.copy()

        # Type filter
        type_sel = input.sum_type()
        if type_sel != "All":
            df = df[df["indicator_type"] == type_sel]

        # Indicator filter
        ind_sel = input.sum_indicators()
        if ind_sel:
            df = df[df["indicator_id"].isin(ind_sel)]

        # Site filter
        site_sel = input.sum_sites()
        if site_sel:
            df = df[df["SITEID"].isin(site_sel)]

        return df

    @reactive.calc
    def filtered_qtl():
        df = df_all[df_all["indicator_type"] == "QTL"].copy()

        cat_sel = input.qtl_cat()
        if cat_sel != "All":
            df = df[df["category"] == cat_sel]

        ind_sel = input.qtl_indicator()
        if ind_sel:
            df = df[df["indicator_id"] == ind_sel]

        site_sel = input.qtl_sites()
        if site_sel:
            df = df[df["SITEID"].isin(site_sel)]

        return df

    @reactive.calc
    def filtered_kri():
        df = df_all[df_all["indicator_type"] == "KRI"].copy()

        cat_sel = input.kri_cat()
        if cat_sel != "All":
            df = df[df["category"] == cat_sel]

        ind_sel = input.kri_indicator()
        if ind_sel:
            df = df[df["indicator_id"] == ind_sel]

        site_sel = input.kri_sites()
        if site_sel:
            df = df[df["SITEID"].isin(site_sel)]

        return df

    # ── Stat cards ────────────────────────────────────────────────────────────

    @output
    @render.ui
    def card_total_sites():
        n = filtered_summary()["SITEID"].nunique()
        return stat_card("Total Sites", n, "#3498db")

    @output
    @render.ui
    def card_red_sites():
        df = filtered_summary()
        n = df[df["status"] == "Red"]["SITEID"].nunique()
        return stat_card("Red Alert Sites", n, STATUS_COLORS["Red"])

    @output
    @render.ui
    def card_yellow_sites():
        df = filtered_summary()
        n = df[df["status"] == "Yellow"]["SITEID"].nunique()
        return stat_card("Yellow Alert Sites", n, STATUS_COLORS["Yellow"])

    @output
    @render.ui
    def card_total_indicators():
        n = filtered_summary()["indicator_id"].nunique()
        return stat_card("Indicators", n, "#9b59b6")

    # ── Heatmap ───────────────────────────────────────────────────────────────

    @output
    @render.ui
    def heatmap_plot():
        df = filtered_summary()
        fig = build_heatmap(df) if not df.empty else go.Figure()
        return ui.HTML(fig.to_html(full_html=False, include_plotlyjs=False))

    # ── Site risk table ───────────────────────────────────────────────────────

    @output
    @render.data_frame
    def site_risk_table():
        df = filtered_summary()
        if df.empty:
            return render.DataGrid(pd.DataFrame())

        site_risk = df.groupby("SITEID").agg(
            Red=("status", lambda x: (x == "Red").sum()),
            Yellow=("status", lambda x: (x == "Yellow").sum()),
            Green=("status", lambda x: (x == "Green").sum()),
        ).reset_index()

        site_risk["Overall Risk"] = site_risk.apply(
            lambda r: "Red" if r["Red"] > 0 else ("Yellow" if r["Yellow"] > 0 else "Green"),
            axis=1,
        )

        site_risk = site_risk.rename(columns={"SITEID": "Site"})
        return render.DataGrid(
            site_risk,
            filters=False,
            row_selection_mode="none",
            width="100%",
        )

    # ── QTL bar chart ─────────────────────────────────────────────────────────

    @output
    @render.ui
    def qtl_bar_chart():
        df = filtered_qtl()
        ind_sel = input.qtl_indicator()
        fig = build_bar_chart(df.sort_values("SITEID"), ind_sel) if not df.empty and ind_sel else go.Figure()
        return ui.HTML(fig.to_html(full_html=False, include_plotlyjs=False))

    # ── QTL detail table ──────────────────────────────────────────────────────

    @output
    @render.data_frame
    def qtl_detail_table():
        df = filtered_qtl()
        if df.empty:
            return render.DataGrid(pd.DataFrame())

        display = df[[
            "SITEID", "value", "status",
            "n_numerator", "n_denominator",
            "threshold_yellow", "threshold_red",
        ]].copy()

        display = display.rename(columns={
            "SITEID": "Site",
            "value": "Value (%)",
            "status": "Status",
            "n_numerator": "Numerator",
            "n_denominator": "Denominator",
            "threshold_yellow": "Yellow Threshold",
            "threshold_red": "Red Threshold",
        })

        display["Value (%)"] = display["Value (%)"].map("{:.2f}".format)
        return render.DataGrid(display, filters=False, width="100%")

    # ── QTL info panel ────────────────────────────────────────────────────────

    @output
    @render.ui
    def qtl_info_panel():
        ind_sel = input.qtl_indicator()
        if not ind_sel:
            return ui.div()
        return indicator_info_panel(ind_sel)

    # ── KRI bar chart ─────────────────────────────────────────────────────────

    @output
    @render.ui
    def kri_bar_chart():
        df = filtered_kri()
        ind_sel = input.kri_indicator()
        fig = build_bar_chart(df.sort_values("SITEID"), ind_sel) if not df.empty and ind_sel else go.Figure()
        return ui.HTML(fig.to_html(full_html=False, include_plotlyjs=False))

    # ── KRI detail table ──────────────────────────────────────────────────────

    @output
    @render.data_frame
    def kri_detail_table():
        df = filtered_kri()
        if df.empty:
            return render.DataGrid(pd.DataFrame())

        display = df[[
            "SITEID", "value", "status",
            "n_numerator", "n_denominator",
            "threshold_yellow", "threshold_red",
        ]].copy()

        display = display.rename(columns={
            "SITEID": "Site",
            "value": "Value (%)",
            "status": "Status",
            "n_numerator": "Numerator",
            "n_denominator": "Denominator",
            "threshold_yellow": "Yellow Threshold",
            "threshold_red": "Red Threshold",
        })

        display["Value (%)"] = display["Value (%)"].map("{:.2f}".format)
        return render.DataGrid(display, filters=False, width="100%")

    # ── KRI info panel ────────────────────────────────────────────────────────

    @output
    @render.ui
    def kri_info_panel():
        ind_sel = input.kri_indicator()
        if not ind_sel:
            return ui.div()
        return indicator_info_panel(ind_sel)


# ── App ───────────────────────────────────────────────────────────────────────
app = App(app_ui, server, static_assets=os.path.join(APP_DIR, "www"))
