import dash
from dash import dcc, html, Input, Output
from flask import session
from final_project.frontend.pages import welcome, analyze, login
from final_project.utilities.security_logic import parse_token_from_flask, verify_token

server_secret = "replace_this_with_a_long_random_string_123456"

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
)

app.server.secret_key = server_secret
server = app.server

app.layout = html.Div([
    dcc.Location(id="url", refresh=True),
    html.Div(id="page-content"),
])


@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def display_page(pathname):
    token = parse_token_from_flask()
    is_authenticated = False
    if token:
        try:
            verify_token(token)
            is_authenticated = True
        except Exception:
            is_authenticated = False

    if not is_authenticated:
        return login.layout

    if pathname == "/analyze":
        return analyze.layout
    return welcome.layout