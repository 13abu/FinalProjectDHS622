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

# ─── Topic Modeling ──────────────────────────────────────────────────────────

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import re


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"[^a-zA-Z\s]", "", text)
    return text.lower().strip()


def get_topic_model(
    seed_list: str,
    start_date: str,
    end_date: str,
    n_topics: int = 6,
    n_words: int = 8,
) -> list[dict]:
    seeds = fetch_seeds(seed_list)
    handles = [s["handle"] for s in seeds]
    records = fetch_statuses_for_handles(handles, start_date, end_date)

    texts = [clean_text(r.get("content") or "") for r in records]
    texts = [t for t in texts if len(t.split()) >= 5]

    if len(texts) < 20:
        return []

    vectorizer = CountVectorizer(
        max_df=0.9,
        min_df=5,
        stop_words="english",
        max_features=1000,
    )

    try:
        dtm = vectorizer.fit_transform(texts)
    except ValueError:
        return []

    lda = LatentDirichletAllocation(
        n_components=n_topics,
        random_state=42,
        max_iter=20,
    )
    lda.fit(dtm)

    vocab = vectorizer.get_feature_names_out()
    topics = []
    for i, component in enumerate(lda.components_):
        top_words = [vocab[j] for j in component.argsort()[-n_words:][::-1]]
        topics.append({
            "topic_id": i,
            "label": f"Topic {i + 1}",
            "words": top_words,
            "weight": float(component.sum()),
        })

    topics.sort(key=lambda x: x["weight"], reverse=True)
    return topics


def get_topic_model_by_camp(
    seed_list: str,
    start_date: str,
    end_date: str,
    n_topics: int = 4,
    n_words: int = 8,
) -> dict:
    seeds = fetch_seeds(seed_list)
    camp_handles = {}
    for s in seeds:
        camp = s.get("camp") or "unknown"
        camp_handles.setdefault(camp, []).append(s["handle"])

    results = {}
    for camp, handles in camp_handles.items():
        records = fetch_statuses_for_handles(handles, start_date, end_date)
        texts = [clean_text(r.get("content") or "") for r in records]
        texts = [t for t in texts if len(t.split()) >= 5]

        if len(texts) < 20:
            results[camp] = []
            continue

        vectorizer = CountVectorizer(
            max_df=0.9, min_df=3,
            stop_words="english", max_features=500,
        )
        try:
            dtm = vectorizer.fit_transform(texts)
            lda = LatentDirichletAllocation(
                n_components=n_topics, random_state=42, max_iter=20
            )
            lda.fit(dtm)
            vocab = vectorizer.get_feature_names_out()
            topics = []
            for i, component in enumerate(lda.components_):
                top_words = [vocab[j] for j in component.argsort()[-n_words:][::-1]]
                topics.append({
                    "topic_id": i,
                    "label": f"Topic {i + 1}",
                    "words": top_words,
                })
            results[camp] = topics
        except Exception:
            results[camp] = []

    return results


# ─── Keyword Timeline ─────────────────────────────────────────────────────────

def get_keyword_timeline(
    seed_list: str,
    start_date: str,
    end_date: str,
    keywords: list[str] = None,
) -> list[dict]:
    from .db import engine, statuses_table
    import sqlalchemy as sa

    if keywords is None:
        keywords = ["iran", "israel", "gaza", "war", "aipac", "hamas",
                    "netanyahu", "hezbollah", "strike", "peace"]

    seeds = fetch_seeds(seed_list)
    handles = [s["handle"] for s in seeds]

    with engine.connect() as conn:
        rp = conn.execute(
            sa.select(
                statuses_table.c.created_at,
                statuses_table.c.content,
                statuses_table.c.account_handle,
            ).where(
                statuses_table.c.account_handle.in_(handles),
                statuses_table.c.created_at >= pd.Timestamp(start_date),
                statuses_table.c.created_at <= pd.Timestamp(end_date),
                statuses_table.c.content.isnot(None),
            )
        )
    records = [dict(r._mapping) for r in rp.fetchall()]

    df = pd.DataFrame(records)
    if df.empty:
        return []

    df["date"] = pd.to_datetime(df["created_at"]).dt.date
    df["content_lower"] = df["content"].str.lower()

    rows = []
    for kw in keywords:
        daily = df[df["content_lower"].str.contains(kw, na=False)].groupby("date").size()
        for date, count in daily.items():
            rows.append({"keyword": kw, "date": str(date), "count": int(count)})

    return rows


# ─── Sentiment Analysis ───────────────────────────────────────────────────────

from textblob import TextBlob


def get_sentiment_by_camp(
    seed_list: str,
    start_date: str,
    end_date: str,
) -> list[dict]:
    seeds = fetch_seeds(seed_list)
    handle_to_camp = {s["handle"]: s.get("camp", "unknown") for s in seeds}
    handles = list(handle_to_camp.keys())

    records = fetch_statuses_for_handles(handles, start_date, end_date)

    rows = []
    for r in records:
        text = r.get("content") or ""
        if len(text.strip()) < 10:
            continue
        blob = TextBlob(text)
        rows.append({
            "account_handle": r["account_handle"],
            "camp": handle_to_camp.get(r["account_handle"], "unknown"),
            "polarity": blob.sentiment.polarity,
            "subjectivity": blob.sentiment.subjectivity,
            "date": str(r["created_at"])[:10],
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return []

    summary = (
        df.groupby("camp")[["polarity", "subjectivity"]]
        .mean()
        .reset_index()
        .round(4)
    )
    return summary.to_dict("records")


def get_sentiment_timeline(
    seed_list: str,
    start_date: str,
    end_date: str,
) -> list[dict]:
    seeds = fetch_seeds(seed_list)
    handle_to_camp = {s["handle"]: s.get("camp", "unknown") for s in seeds}
    handles = list(handle_to_camp.keys())

    records = fetch_statuses_for_handles(handles, start_date, end_date)

    rows = []
    for r in records:
        text = r.get("content") or ""
        if len(text.strip()) < 10:
            continue
        blob = TextBlob(text)
        rows.append({
            "camp": handle_to_camp.get(r["account_handle"], "unknown"),
            "polarity": blob.sentiment.polarity,
            "date": str(r["created_at"])[:10],
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return []

    timeline = (
        df.groupby(["date", "camp"])["polarity"]
        .mean()
        .reset_index()
        .round(4)
        .sort_values("date")
    )
    return timeline.to_dict("records")