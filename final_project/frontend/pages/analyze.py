from dash import dcc, html, Input, Output, State, dash_table, no_update
import dash
import dash_cytoscape as cyto
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from flask import session

from ...api.clients import (
    get_seed_list_names,
    post_seed_preview,
    post_top_statuses,
    post_time_series,
    post_repost_network,
    post_topic_model,
    post_keyword_timeline,
    post_sentiment,
    post_engagement_by_camp,
    post_volume_by_camp,
)
from ...utilities.logic import make_cytoscape_stylesheet

SEED_LIST = "iran_israel_war"
DEFAULT_START = "2026-02-01"
DEFAULT_END = "2026-04-14"

CAMP_COLORS = {
    "pro_war": "#e63946",
    "anti_war": "#457b9d",
    "bridge": "#2a9d8f",
    "unknown": "#888888",
}

layout = html.Div(
    style={"backgroundColor": "#0d0f0e", "minHeight": "100vh",
           "padding": "32px", "fontFamily": "sans-serif"},
    children=[
        html.H2("Analysis", style={"color": "#e8e6dc", "fontWeight": "500",
                                    "marginBottom": "24px"}),
        # Date range + analyze button
        html.Div(
            style={"display": "flex", "gap": "16px", "alignItems": "center",
                   "marginBottom": "32px"},
            children=[
                html.Label("From:", style={"color": "#5F5E5A", "fontSize": "13px"}),
                dcc.Input(id="start-date", value=DEFAULT_START, type="text",
                          style={"backgroundColor": "#1a1a1a", "color": "#e8e6dc",
                                 "border": "1px solid #333", "padding": "8px",
                                 "borderRadius": "4px", "width": "120px"}),
                html.Label("To:", style={"color": "#5F5E5A", "fontSize": "13px"}),
                dcc.Input(id="end-date", value=DEFAULT_END, type="text",
                          style={"backgroundColor": "#1a1a1a", "color": "#e8e6dc",
                                 "border": "1px solid #333", "padding": "8px",
                                 "borderRadius": "4px", "width": "120px"}),
                html.Button(
                    "Analyze", id="analyze-btn", n_clicks=0,
                    style={"backgroundColor": "#1D9E75", "color": "#04342C",
                           "border": "none", "padding": "8px 20px",
                           "borderRadius": "6px", "cursor": "pointer",
                           "fontWeight": "500"}
                ),
            ],
        ),
        html.Div(id="time-series-container"),
        html.Div(id="keyword-timeline-container"),
        html.Div(id="sentiment-container"),
        html.Div(id="engagement-container"),
        html.Div(id="volume-by-camp-container"),
        html.Div(id="repost-network-container"),
        html.Div(id="topic-model-container"),
        html.Div(id="top-posts-container"),
    ],
)


def get_token():
    bearer = session.get("Authorization", "")
    return bearer.replace("Bearer ", "") if bearer else ""


def section_header(title):
    return html.H3(title, style={"color": "#e8e6dc", "fontWeight": "500",
                                  "marginTop": "40px", "marginBottom": "12px",
                                  "borderLeft": "3px solid #1D9E75",
                                  "paddingLeft": "12px"})


# ── Time series ───────────────────────────────────────────────────────────────

@dash.callback(
    Output("time-series-container", "children"),
    Input("analyze-btn", "n_clicks"),
    State("start-date", "value"),
    State("end-date", "value"),
    prevent_initial_call=True,
)
def render_time_series(n_clicks, start_date, end_date):
    token = get_token()
    records = post_time_series(token, SEED_LIST, start_date, end_date, "day")
    if not records:
        return html.P("No data.", style={"color": "#5F5E5A"})
    df = pd.DataFrame(records)
    fig = px.bar(df, x="dt", y="count", title="Posting activity over time",
                 template="plotly_dark",
                 labels={"dt": "Date", "count": "Posts"})
    fig.update_layout(paper_bgcolor="#0d0f0e", plot_bgcolor="#111")
    return html.Div([section_header("Posting activity"), dcc.Graph(figure=fig)])


# ── Keyword timeline ──────────────────────────────────────────────────────────

@dash.callback(
    Output("keyword-timeline-container", "children"),
    Input("analyze-btn", "n_clicks"),
    State("start-date", "value"),
    State("end-date", "value"),
    prevent_initial_call=True,
)
def render_keyword_timeline(n_clicks, start_date, end_date):
    token = get_token()
    records = post_keyword_timeline(token, SEED_LIST, start_date, end_date)
    if not records:
        return html.P("No keyword data.", style={"color": "#5F5E5A"})
    df = pd.DataFrame(records)
    fig = px.line(df, x="date", y="count", color="keyword",
                  title="Keyword frequency over time",
                  template="plotly_dark",
                  labels={"date": "Date", "count": "Mentions", "keyword": "Keyword"})
    fig.update_layout(paper_bgcolor="#0d0f0e", plot_bgcolor="#111")
    return html.Div([section_header("Keyword timeline"), dcc.Graph(figure=fig)])


# ── Sentiment ─────────────────────────────────────────────────────────────────

@dash.callback(
    Output("sentiment-container", "children"),
    Input("analyze-btn", "n_clicks"),
    State("start-date", "value"),
    State("end-date", "value"),
    prevent_initial_call=True,
)
def render_sentiment(n_clicks, start_date, end_date):
    token = get_token()
    data = post_sentiment(token, SEED_LIST, start_date, end_date)

    by_camp = data.get("by_camp", [])
    timeline = data.get("timeline", [])

    if not by_camp:
        return html.P("No sentiment data.", style={"color": "#5F5E5A"})

    # Bar chart by camp
    df_camp = pd.DataFrame(by_camp)
    df_camp["color"] = df_camp["camp"].map(CAMP_COLORS).fillna("#888")

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=df_camp["camp"],
        y=df_camp["polarity"],
        marker_color=df_camp["color"].tolist(),
        name="Polarity",
    ))
    fig_bar.update_layout(
        title="Average sentiment polarity by camp",
        template="plotly_dark",
        paper_bgcolor="#0d0f0e",
        plot_bgcolor="#111",
        yaxis_title="Polarity (-1 = negative, +1 = positive)",
        xaxis_title="Camp",
    )

    children = [section_header("Sentiment analysis"), dcc.Graph(figure=fig_bar)]

    # Timeline if available
    if timeline:
        df_time = pd.DataFrame(timeline)
        df_time["color"] = df_time["camp"].map(CAMP_COLORS)
        fig_line = px.line(
            df_time, x="date", y="polarity", color="camp",
            title="Sentiment polarity over time by camp",
            template="plotly_dark",
            color_discrete_map=CAMP_COLORS,
            labels={"date": "Date", "polarity": "Avg polarity", "camp": "Camp"},
        )
        fig_line.update_layout(paper_bgcolor="#0d0f0e", plot_bgcolor="#111")
        children.append(dcc.Graph(figure=fig_line))

    return html.Div(children)


# ── Repost network ────────────────────────────────────────────────────────────

@dash.callback(
    Output("repost-network-container", "children"),
    Input("analyze-btn", "n_clicks"),
    State("start-date", "value"),
    State("end-date", "value"),
    prevent_initial_call=True,
)
def render_repost_network(n_clicks, start_date, end_date):
    token = get_token()
    data = post_repost_network(token, SEED_LIST, start_date, end_date, 200)

    if not data["nodes"]:
        return html.P("No repost network data.", style={"color": "#5F5E5A"})

    nodes = data["nodes"]
    edges = data["edges"]
    stylesheet = make_cytoscape_stylesheet(nodes, edges)

    return html.Div([
        section_header("Repost network"),
        html.P(
            f"{data['num_nodes']} nodes · {data['num_edges']} edges · "
            "node size = times reposted · color = community cluster · "
            "hover a node to highlight connections",
            style={"color": "#5F5E5A", "fontSize": "12px", "marginBottom": "8px"},
        ),
        cyto.Cytoscape(
            id="repost-network",
            layout={"name": "cose"},
            style={"width": "100%", "height": "700px", "backgroundColor": "#111"},
            elements=nodes + edges,
            stylesheet=stylesheet,
            responsive=True,
        ),
        html.Div(id="node-click-info"),
    ])


# ── Topic model ───────────────────────────────────────────────────────────────

@dash.callback(
    Output("topic-model-container", "children"),
    Input("analyze-btn", "n_clicks"),
    State("start-date", "value"),
    State("end-date", "value"),
    prevent_initial_call=True,
)
def render_topic_model(n_clicks, start_date, end_date):
    token = get_token()
    data = post_topic_model(token, SEED_LIST, start_date, end_date, 6)

    overall = data.get("overall", [])
    by_camp = data.get("by_camp", {})

    if not overall:
        return html.P("Not enough data for topic modeling.", style={"color": "#5F5E5A"})

    # Overall topics table
    overall_rows = [
        {"Topic": t["label"], "Top words": " · ".join(t["words"])}
        for t in overall
    ]

    # Per-camp topic cards
    camp_cards = []
    camp_order = ["pro_war", "anti_war", "bridge"]
    camp_labels = {"pro_war": "Pro-war camp", "anti_war": "Anti-war camp", "bridge": "Bridge accounts"}

    for camp in camp_order:
        topics = by_camp.get(camp, [])
        if not topics:
            continue
        camp_cards.append(html.Div(
            style={
                "backgroundColor": "#111", "border": f"1px solid {CAMP_COLORS.get(camp, '#333')}",
                "borderRadius": "8px", "padding": "16px", "flex": "1", "minWidth": "220px",
            },
            children=[
                html.P(camp_labels.get(camp, camp), style={
                    "color": CAMP_COLORS.get(camp, "#888"), "fontSize": "12px",
                    "textTransform": "uppercase", "letterSpacing": "0.08em",
                    "marginBottom": "12px",
                }),
            ] + [
                html.Div(style={"marginBottom": "10px"}, children=[
                    html.P(t["label"], style={"color": "#e8e6dc", "fontSize": "13px",
                                               "fontWeight": "500", "margin": "0 0 2px"}),
                    html.P(" · ".join(t["words"]), style={"color": "#5F5E5A", "fontSize": "12px", "margin": "0"}),
                ])
                for t in topics
            ],
        ))

    return html.Div([
        section_header("Topic modeling"),
        html.P("LDA topic model across all posts in date range.",
               style={"color": "#5F5E5A", "fontSize": "12px", "marginBottom": "16px"}),
        dash_table.DataTable(
            data=overall_rows,
            columns=[{"name": k, "id": k} for k in overall_rows[0].keys()],
            style_table={"marginBottom": "24px"},
            style_cell={"backgroundColor": "#111", "color": "#e8e6dc",
                        "border": "1px solid #222", "textAlign": "left",
                        "fontSize": "13px", "padding": "10px"},
            style_header={"backgroundColor": "#1a1a1a", "color": "#1D9E75",
                          "fontWeight": "500"},
        ),
        html.P("Topics by camp:", style={"color": "#e8e6dc", "fontSize": "13px",
                                          "marginBottom": "12px"}),
        html.Div(camp_cards, style={"display": "flex", "gap": "16px", "flexWrap": "wrap"}),
    ])


# ── Top posts ─────────────────────────────────────────────────────────────────

@dash.callback(
    Output("top-posts-container", "children"),
    Input("analyze-btn", "n_clicks"),
    State("start-date", "value"),
    State("end-date", "value"),
    prevent_initial_call=True,
)
def render_top_posts(n_clicks, start_date, end_date):
    token = get_token()
    records = post_top_statuses(token, SEED_LIST, start_date, end_date, 50)
    if not records:
        return html.P("No posts found.", style={"color": "#5F5E5A"})

    display = [
        {
            "Account": r["account_handle"],
            "Date": str(r["created_at"])[:10],
            "Content": (r.get("content") or "")[:120],
            "Reblogs": r.get("reblogs_count", 0),
            "Likes": r.get("favourites_count", 0),
            "Engagement": r.get("engagement", 0),
        }
        for r in records
    ]

    return html.Div([
        section_header("Top posts by engagement"),
        dash_table.DataTable(
            data=display,
            columns=[{"name": k, "id": k} for k in display[0].keys()],
            style_table={"overflowX": "auto"},
            style_cell={"backgroundColor": "#111", "color": "#e8e6dc",
                        "border": "1px solid #222", "textAlign": "left",
                        "fontSize": "12px", "padding": "8px"},
            style_header={"backgroundColor": "#1a1a1a", "color": "#1D9E75",
                          "fontWeight": "500"},
            page_size=20,
            sort_action="native",
            export_format="csv",
        ),
    ])


# ── Network hover + click ─────────────────────────────────────────────────────

@dash.callback(
    Output("repost-network", "stylesheet"),
    Input("repost-network", "mouseoverNodeData"),
    State("repost-network", "elements"),
    prevent_initial_call=True,
)
def highlight_on_hover(hovered_node, elements):
    if not hovered_node or not elements:
        return no_update
    nodes = [e for e in elements if "source" not in e["data"]]
    edges = [e for e in elements if "source" in e["data"]]
    return make_cytoscape_stylesheet(nodes, edges, hovered_node)


@dash.callback(
    Output("node-click-info", "children"),
    Input("repost-network", "tapNodeData"),
    prevent_initial_call=True,
)
def show_node_info(node_data):
    if not node_data:
        return no_update
    camp = node_data.get("camp", "unknown")
    camp_color = CAMP_COLORS.get(camp, "#888")
    return html.Div(
        style={
            "backgroundColor": "#111", "border": f"1px solid {camp_color}",
            "borderRadius": "6px", "padding": "16px", "marginTop": "12px",
            "maxWidth": "400px",
        },
        children=[
            html.P(f"@{node_data['id']}", style={"color": camp_color, "fontWeight": "500",
                                                   "margin": "0 0 8px", "fontSize": "15px"}),
            html.Div(style={"display": "flex", "gap": "24px", "flexWrap": "wrap"}, children=[
                html.Div([
                    html.P("Camp", style={"color": "#5F5E5A", "fontSize": "11px",
                                          "textTransform": "uppercase", "margin": "0"}),
                    html.P(camp, style={"color": "#e8e6dc", "fontSize": "13px", "margin": "2px 0 0"}),
                ]),
                html.Div([
                    html.P("Cluster", style={"color": "#5F5E5A", "fontSize": "11px",
                                              "textTransform": "uppercase", "margin": "0"}),
                    html.P(str(node_data.get("cluster", "?")),
                           style={"color": "#e8e6dc", "fontSize": "13px", "margin": "2px 0 0"}),
                ]),
                html.Div([
                    html.P("Times reposted", style={"color": "#5F5E5A", "fontSize": "11px",
                                                     "textTransform": "uppercase", "margin": "0"}),
                    html.P(str(node_data.get("in_degree", 0)),
                           style={"color": "#e8e6dc", "fontSize": "13px", "margin": "2px 0 0"}),
                ]),
                html.Div([
                    html.P("Reposts others", style={"color": "#5F5E5A", "fontSize": "11px",
                                                     "textTransform": "uppercase", "margin": "0"}),
                    html.P(str(node_data.get("out_degree", 0)),
                           style={"color": "#e8e6dc", "fontSize": "13px", "margin": "2px 0 0"}),
                ]),
            ]),
        ],
    )
@dash.callback(
    Output("engagement-container", "children"),
    Input("analyze-btn", "n_clicks"),
    State("start-date", "value"),
    State("end-date", "value"),
    prevent_initial_call=True,
)
def render_engagement(n_clicks, start_date, end_date):
    token = get_token()
    records = post_engagement_by_camp(token, SEED_LIST, start_date, end_date)
    if not records:
        return html.P("No engagement data.", style={"color": "#5F5E5A"})

    df = pd.DataFrame(records)
    fig = go.Figure()
    for metric, label in [("reblogs", "Avg reblogs"), ("likes", "Avg likes")]:
        fig.add_trace(go.Bar(
            name=label,
            x=df["camp"],
            y=df[metric],
            marker_color={"reblogs": "#1D9E75", "likes": "#457b9d"}[metric],
        ))
    fig.update_layout(
        barmode="group",
        title="Average engagement by camp",
        template="plotly_dark",
        paper_bgcolor="#0d0f0e",
        plot_bgcolor="#111",
        xaxis_title="Camp",
        yaxis_title="Average per post",
    )
    return html.Div([section_header("Engagement by camp"), dcc.Graph(figure=fig)])


@dash.callback(
    Output("volume-by-camp-container", "children"),
    Input("analyze-btn", "n_clicks"),
    State("start-date", "value"),
    State("end-date", "value"),
    prevent_initial_call=True,
)
def render_volume_by_camp(n_clicks, start_date, end_date):
    token = get_token()
    records = post_volume_by_camp(token, SEED_LIST, start_date, end_date)
    if not records:
        return html.P("No volume data.", style={"color": "#5F5E5A"})

    df = pd.DataFrame(records)
    fig = px.line(
        df, x="date", y="count", color="camp",
        title="Posting volume by camp over time",
        template="plotly_dark",
        color_discrete_map=CAMP_COLORS,
        labels={"date": "Date", "count": "Posts", "camp": "Camp"},
    )
    fig.update_layout(paper_bgcolor="#0d0f0e", plot_bgcolor="#111")
    return html.Div([section_header("Posting volume by camp"), dcc.Graph(figure=fig)])

# in imports
from ...api.clients import (
    ...
    post_aipac,
)

# in layout, add after engagement-container:
html.Div(id="aipac-container"),

# new callback
@dash.callback(
    Output("aipac-container", "children"),
    Input("analyze-btn", "n_clicks"),
    State("start-date", "value"),
    State("end-date", "value"),
    prevent_initial_call=True,
)
def render_aipac(n_clicks, start_date, end_date):
    token = get_token()
    records = post_aipac(token, SEED_LIST)
    if not records:
        return html.P("No AIPAC data.", style={"color": "#5F5E5A"})

    df = pd.DataFrame(records)
    df["color"] = df["camp"].map(CAMP_COLORS).fillna("#888")
    df["label"] = "@" + df["handle"]

    fig = go.Figure(go.Bar(
        x=df["label"],
        y=df["aipac_total"],
        marker_color=df["color"].tolist(),
        text=[f"${v:,.0f}" for v in df["aipac_total"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="AIPAC contributions to politicians in dataset (2024 cycle)",
        template="plotly_dark",
        paper_bgcolor="#0d0f0e",
        plot_bgcolor="#111",
        xaxis_title="Account",
        yaxis_title="Total AIPAC funding ($)",
        yaxis_tickformat="$,.0f",
        showlegend=False,
        margin={"t": 60, "b": 120},
    )

    return html.Div([
        section_header("AIPAC funding vs. camp alignment"),
        html.P(
            "Bar color = camp label (red = pro_war, blue = anti_war). "
            "Note: only politicians appear here — media accounts excluded.",
            style={"color": "#5F5E5A", "fontSize": "12px", "marginBottom": "8px"}
        ),
        dcc.Graph(figure=fig),
    ])