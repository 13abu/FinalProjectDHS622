from dash import dcc, html, Input, Output, State, dash_table, no_update
import dash
import dash_cytoscape as cyto
import plotly.express as px
import pandas as pd
from flask import session

from ...api.clients import (
    get_seed_list_names,
    post_seed_preview,
    post_top_statuses,
    post_time_series,
    post_repost_network,
)
from ...utilities.logic import make_cytoscape_stylesheet

SEED_LIST = "iran_israel_war"
DEFAULT_START = "2026-02-01"
DEFAULT_END = "2026-04-14"

layout = html.Div(
    style={"backgroundColor": "#0d0f0e", "minHeight": "100vh", "padding": "32px", "fontFamily": "sans-serif"},
    children=[
        html.H2("Analysis", style={"color": "#e8e6dc", "fontWeight": "500", "marginBottom": "24px"}),

        # Date range picker
        html.Div(style={"display": "flex", "gap": "16px", "alignItems": "center", "marginBottom": "24px"}, children=[
            html.Label("From:", style={"color": "#5F5E5A", "fontSize": "13px"}),
            dcc.Input(id="start-date", value=DEFAULT_START, type="text",
                      style={"backgroundColor": "#1a1a1a", "color": "#e8e6dc", "border": "1px solid #333",
                             "padding": "8px", "borderRadius": "4px", "width": "120px"}),
            html.Label("To:", style={"color": "#5F5E5A", "fontSize": "13px"}),
            dcc.Input(id="end-date", value=DEFAULT_END, type="text",
                      style={"backgroundColor": "#1a1a1a", "color": "#e8e6dc", "border": "1px solid #333",
                             "padding": "8px", "borderRadius": "4px", "width": "120px"}),
            html.Button("Analyze", id="analyze-btn", n_clicks=0,
                        style={"backgroundColor": "#1D9E75", "color": "#04342C", "border": "none",
                               "padding": "8px 20px", "borderRadius": "6px", "cursor": "pointer",
                               "fontWeight": "500"}),
        ]),

        # Containers
        html.Div(id="time-series-container"),
        html.Div(id="repost-network-container"),
        html.Div(id="top-posts-container"),
    ],
)


def get_token():
    bearer = session.get("Authorization", "")
    return bearer.replace("Bearer ", "") if bearer else ""


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
    df = pd.DataFrame(records)
    if df.empty:
        return html.P("No data for this date range.", style={"color": "#5F5E5A"})

    fig = px.bar(df, x="dt", y="count", title="Posting activity over time",
                 template="plotly_dark",
                 labels={"dt": "Date", "count": "Posts"})
    fig.update_layout(paper_bgcolor="#0d0f0e", plot_bgcolor="#0d0f0e")
    return dcc.Graph(figure=fig)


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
        return html.P("No repost network data found.", style={"color": "#5F5E5A"})

    nodes = data["nodes"]
    edges = data["edges"]
    stylesheet = make_cytoscape_stylesheet(nodes, edges)

    return html.Div([
        html.P(
            f"Repost network: {data['num_nodes']} nodes, {data['num_edges']} edges",
            style={"color": "#5F5E5A", "fontSize": "13px", "marginBottom": "8px"},
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
        html.H3("Top posts by engagement", style={"color": "#e8e6dc", "fontWeight": "500", "marginTop": "32px"}),
        dash_table.DataTable(
            data=display,
            columns=[{"name": k, "id": k} for k in display[0].keys()],
            style_table={"overflowX": "auto"},
            style_cell={"backgroundColor": "#111", "color": "#e8e6dc", "border": "1px solid #222",
                        "textAlign": "left", "fontSize": "12px", "padding": "8px"},
            style_header={"backgroundColor": "#1a1a1a", "color": "#1D9E75", "fontWeight": "500"},
            page_size=20,
            sort_action="native",
            export_format="csv",
        ),
    ])


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
    return html.Div(
        style={"backgroundColor": "#111", "border": "1px solid #1D9E75", "borderRadius": "6px",
               "padding": "16px", "marginTop": "12px"},
        children=[
            html.P(f"@{node_data['id']}", style={"color": "#1D9E75", "fontWeight": "500", "margin": "0 0 4px"}),
            html.P(f"Camp: {node_data.get('camp', 'unknown')}", style={"color": "#e8e6dc", "fontSize": "13px", "margin": "2px 0"}),
            html.P(f"Cluster: {node_data.get('cluster', '?')}", style={"color": "#e8e6dc", "fontSize": "13px", "margin": "2px 0"}),
            html.P(f"In-degree: {node_data.get('in_degree', 0)}", style={"color": "#e8e6dc", "fontSize": "13px", "margin": "2px 0"}),
            html.P(f"Out-degree: {node_data.get('out_degree', 0)}", style={"color": "#e8e6dc", "fontSize": "13px", "margin": "2px 0"}),
        ],
    )