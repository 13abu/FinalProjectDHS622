import dash
from dash import dcc, html, Input, Output
from flask import session

server_secret = "replace_this_with_a_long_random_string_123456"

app = dash.Dash(
    __name__,
    use_pages=False,
    suppress_callback_exceptions=True,
    server_kwargs={"secret_key": server_secret},
)

server = app.server

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="page-content"),
])


@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def display_page(pathname):
    from final_project.utilities.security_logic import parse_token_from_flask, verify_token
    from final_project.frontend.pages import welcome, analyze, login

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