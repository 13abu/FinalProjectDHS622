from dash import dcc, html, Input, Output, State, no_update
import dash
from ...api.clients import post_login
from flask import session

layout = html.Div(
    style={
        "backgroundColor": "#0d0f0e",
        "minHeight": "100vh",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "fontFamily": "monospace",
    },
    children=[
        html.Div(
            style={
                "backgroundColor": "#111",
                "border": "1px solid #1D9E75",
                "borderRadius": "8px",
                "padding": "40px",
                "width": "360px",
            },
            children=[
                html.P("// truth social observatory", style={
                    "color": "#1D9E75", "fontSize": "11px",
                    "letterSpacing": "0.12em", "textTransform": "uppercase",
                    "marginBottom": "8px",
                }),
                html.H2("Sign in", style={
                    "color": "#e8e6dc", "fontFamily": "sans-serif",
                    "fontWeight": "500", "marginBottom": "24px",
                }),
                dcc.Input(
                    id="login-email",
                    placeholder="Email",
                    type="text",
                    style={
                        "width": "100%", "padding": "10px",
                        "marginBottom": "12px", "backgroundColor": "#1a1a1a",
                        "border": "1px solid #333", "color": "#e8e6dc",
                        "borderRadius": "4px", "boxSizing": "border-box",
                    },
                ),
                dcc.Input(
                    id="login-password",
                    placeholder="Password",
                    type="password",
                    style={
                        "width": "100%", "padding": "10px",
                        "marginBottom": "20px", "backgroundColor": "#1a1a1a",
                        "border": "1px solid #333", "color": "#e8e6dc",
                        "borderRadius": "4px", "boxSizing": "border-box",
                    },
                ),
                html.Button(
                    "Enter →",
                    id="login-button",
                    n_clicks=0,
                    style={
                        "backgroundColor": "#1D9E75", "color": "#04342C",
                        "border": "none", "padding": "10px 24px",
                        "borderRadius": "6px", "cursor": "pointer",
                        "fontWeight": "500", "fontSize": "13px",
                        "fontFamily": "sans-serif",
                    },
                ),
                html.Div(id="login-message", style={"marginTop": "12px"}),
            ],
        )
    ],
)


@dash.callback(
    Output("login-button", "n_clicks"),
    Output("login-message", "children"),
    Output("url", "href"),
    Input("login-button", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
)
def handle_login(n_clicks, email, password):
    if not n_clicks:
        return no_update, no_update, no_update

    token = post_login(email, password)

    if token is None:
        return 0, html.P("Incorrect email or password.", style={"color": "#e63946", "fontSize": "13px"}), no_update

    session["Authorization"] = f"Bearer {token}"
    return 0, html.P("Success!", style={"color": "#1D9E75", "fontSize": "13px"}), "/"