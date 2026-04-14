from dash import dcc, html

layout = html.Div(
    style={
        "backgroundColor": "#0d0f0e",
        "minHeight": "100vh",
        "padding": "48px 40px",
        "fontFamily": "monospace",
    },
    children=[
        html.P("// us-israel-iran war · truth social network analysis", style={
            "fontSize": "11px", "color": "#1D9E75",
            "letterSpacing": "0.12em", "textTransform": "uppercase",
            "marginBottom": "16px",
        }),
        html.H1(
            ["Signal", html.Span("Watch", style={"color": "#1D9E75"})],
            style={
                "fontSize": "36px", "fontWeight": "500", "color": "#e8e6dc",
                "lineHeight": "1.2", "margin": "0 0 8px", "fontFamily": "sans-serif",
            },
        ),
        html.P(
            "Mapping the pro-war vs anti-war split on the American right",
            style={"fontSize": "14px", "color": "#5F5E5A", "margin": "0 0 36px", "fontFamily": "sans-serif"},
        ),
        html.Div(
            style={"display": "flex", "gap": "24px", "marginBottom": "40px"},
            children=[
                html.Div(style={"borderLeft": "2px solid #1D9E75", "paddingLeft": "12px"}, children=[
                    html.Div("61", style={"fontSize": "20px", "color": "#e8e6dc", "fontWeight": "500"}),
                    html.Div("accounts tracked", style={"fontSize": "11px", "color": "#5F5E5A", "textTransform": "uppercase"}),
                ]),
                html.Div(style={"borderLeft": "2px solid #1D9E75", "paddingLeft": "12px"}, children=[
                    html.Div("Feb–Apr 2026", style={"fontSize": "20px", "color": "#e8e6dc", "fontWeight": "500"}),
                    html.Div("date range", style={"fontSize": "11px", "color": "#5F5E5A", "textTransform": "uppercase"}),
                ]),
                html.Div(style={"borderLeft": "2px solid #1D9E75", "paddingLeft": "12px"}, children=[
                    html.Div("Truth Social", style={"fontSize": "20px", "color": "#e8e6dc", "fontWeight": "500"}),
                    html.Div("platform", style={"fontSize": "11px", "color": "#5F5E5A", "textTransform": "uppercase"}),
                ]),
            ],
        ),
        dcc.Link(
            "Enter observatory →",
            href="/analyze",
            style={
                "backgroundColor": "#1D9E75", "color": "#04342C",
                "fontSize": "13px", "fontWeight": "500",
                "padding": "10px 24px", "borderRadius": "6px",
                "textDecoration": "none", "fontFamily": "sans-serif",
            },
        ),
        html.P("// analyzing iran_israel_war seed list", style={
            "fontSize": "12px", "color": "#3B6D11", "marginTop": "16px",
        }),
    ],
)