import pandas as pd
from pandas.core.frame import DataFrame
import networkx as nx
from networkx.classes.digraph import DiGraph
import community
from urllib.parse import urlparse

from .db import (
    fetch_seeds,
    fetch_statuses_for_handles,
    fetch_repost_edges,
    fetch_credentials_if_exist,
)


# ─── Seed / metadata helpers ────────────────────────────────────────────────

def get_seed_list_names() -> list[dict]:
    from .db import engine
    import sqlalchemy as sa
    from .db import seeds_table
    with engine.connect() as conn:
        rp = conn.execute(sa.select(seeds_table.c.seed_list).distinct())
    return [{"seed_list": row[0]} for row in rp.fetchall()]


def get_seed_preview(seed_list: str) -> list[dict]:
    return fetch_seeds(seed_list)


def get_top_statuses(
    seed_list: str, start_date: str, end_date: str, limit: int = 100
) -> list[dict]:
    seeds = fetch_seeds(seed_list)
    handles = [s["handle"] for s in seeds]
    records = fetch_statuses_for_handles(handles, start_date, end_date)

    # sort by reblogs + favourites combined
    for r in records:
        r["engagement"] = (r.get("reblogs_count") or 0) + (r.get("favourites_count") or 0)
        # strip api_response — too large for frontend
        r.pop("api_response", None)

    records.sort(key=lambda x: x["engagement"], reverse=True)
    return records[:limit]


def get_time_series_data(
    seed_list: str, start_date: str, end_date: str, unit: str = "day"
) -> list[dict]:
    from .db import engine
    import sqlalchemy as sa
    from .db import statuses_table, seeds_table

    seeds = fetch_seeds(seed_list)
    handles = [s["handle"] for s in seeds]

    with engine.connect() as conn:
        rp = conn.execute(
            sa.select(
                sa.func.date_trunc(unit, statuses_table.c.created_at).label("dt"),
                sa.func.count().label("count"),
            )
            .where(
                statuses_table.c.account_handle.in_(handles),
                statuses_table.c.created_at >= pd.Timestamp(start_date),
                statuses_table.c.created_at <= pd.Timestamp(end_date),
            )
            .group_by(sa.func.date_trunc(unit, statuses_table.c.created_at))
            .order_by(sa.func.date_trunc(unit, statuses_table.c.created_at))
        )
    return [{"dt": row[0], "count": row[1]} for row in rp.fetchall()]


# ─── Network helpers ─────────────────────────────────────────────────────────

def map_communities_to_colors(G: DiGraph) -> dict:
    unique_communities = list(set([G.nodes()[n]["cluster"] for n in G.nodes()]))
    rows = []
    for c in unique_communities:
        num_nodes = len([n for n in G.nodes() if G.nodes()[n]["cluster"] == c])
        rows.append((c, num_nodes))
    df = pd.DataFrame(rows, columns=["cluster", "num_nodes"])
    df.sort_values("num_nodes", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)

    colors = ["#e63946", "#457b9d", "#2a9d8f", "#e9c46a", "#f4a261", "#a8dadc", "#6d6875"]
    return {
        df.loc[i, "cluster"]: colors[i] if i < len(colors) else "#aaaaaa"
        for i in range(df.shape[0])
    }


def filter_network_by_weight(
    records: list[dict],
    source_var: str,
    target_var: str,
    weight_var: str,
    network_max_size: int = None,
) -> DiGraph:
    df = pd.DataFrame.from_records(records)

    if df.empty:
        return nx.DiGraph()

    threshold = 0

    def count_nodes(d: DataFrame) -> int:
        return len(set(list(d[source_var]) + list(d[target_var])))

    if network_max_size is not None:
        while True:
            df = df.loc[df[weight_var] > threshold]
            if count_nodes(df) <= network_max_size:
                break
            threshold = df[weight_var].min()

    G = nx.DiGraph()
    G.add_weighted_edges_from(
        df[[source_var, target_var, weight_var]].values,
        weight=weight_var,
    )
    print(f"Graph: {len(G.nodes())} nodes, {len(G.edges())} edges")
    return G


def make_repost_network(
    seed_list: str,
    start_date: str,
    end_date: str,
    network_max_size: int = None,
) -> DiGraph:
    seeds = fetch_seeds(seed_list)
    handles = [s["handle"] for s in seeds]
    handle_to_camp = {s["handle"]: s["camp"] for s in seeds}

    edges = fetch_repost_edges(handles, start_date, end_date)

    if not edges:
        print("No repost edges found for this date range.")
        return nx.DiGraph()

    G = filter_network_by_weight(
        edges,
        source_var="account_handle",
        target_var="reblogged_from_handle",
        weight_var="count",
        network_max_size=network_max_size,
    )

    # attach camp label to nodes that are in our seed list
    nx.set_node_attributes(G, handle_to_camp, "camp")

    # degree metrics
    nx.set_node_attributes(G, dict(G.in_degree()), "in_degree")
    nx.set_node_attributes(G, dict(G.out_degree()), "out_degree")
    nx.set_node_attributes(G, dict(G.in_degree(weight="count")), "in_strength")
    nx.set_node_attributes(G, dict(G.out_degree(weight="count")), "out_strength")

    # community detection
    nx.set_node_attributes(
        G, community.best_partition(G.to_undirected()), "cluster"
    )

    return G


def make_cytoscape_elements(
    G: DiGraph,
) -> tuple[list[dict], list[dict]]:
    if len(G.nodes()) == 0:
        return [], []

    color_map = map_communities_to_colors(G)

    nodes = [
        {
            "data": {
                "id": str(node),
                "label": str(node),
                "size": G.nodes()[node].get("in_strength", 1),
                "color": color_map.get(G.nodes()[node].get("cluster"), "#aaaaaa"),
                "camp": G.nodes()[node].get("camp", "unknown"),
                "cluster": G.nodes()[node].get("cluster", -1),
                "in_degree": G.nodes()[node].get("in_degree", 0),
                "out_degree": G.nodes()[node].get("out_degree", 0),
            }
        }
        for node in G.nodes()
    ]

    edges = [
        {
            "data": {
                "id": f"{s}-{t}",
                "source": str(s),
                "target": str(t),
                "weight": G.edges()[(s, t)].get("count", 1),
                "color": color_map.get(G.nodes()[s].get("cluster"), "#aaaaaa"),
            }
        }
        for (s, t) in G.edges()
    ]

    return nodes, edges


def make_cytoscape_stylesheet(
    nodes: list[dict], edges: list[dict], hovered_node: dict = None
) -> list[dict]:
    if not nodes:
        return []

    sizes = [n["data"]["size"] for n in nodes]
    weights = [e["data"]["weight"] for e in edges] if edges else [1]

    min_size, max_size = min(sizes), max(sizes)
    min_weight, max_weight = min(weights), max(weights)

    stylesheet = [
        {
            "selector": "node",
            "style": {
                "content": "data(label)",
                "color": "white",
                "text-valign": "center",
                "text-halign": "center",
                "font-size": f"mapData(size, {min_size}, {max_size}, 8, 20)",
                "width": f"mapData(size, {min_size}, {max_size}, 10, 80)",
                "height": f"mapData(size, {min_size}, {max_size}, 10, 80)",
            },
        },
        {
            "selector": "edge",
            "style": {
                "width": f"mapData(weight, {min_weight}, {max_weight}, 0.5, 6)",
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "target-arrow-color": "#888",
                "arrow-scale": 0.8,
            },
        },
    ]

    if hovered_node:
        edges_of_interest = [
            e for e in edges
            if e["data"]["source"] == hovered_node["id"]
            or e["data"]["target"] == hovered_node["id"]
        ]
        nodes_of_interest = set(
            [e["data"]["source"] for e in edges_of_interest]
            + [e["data"]["target"] for e in edges_of_interest]
        )
    else:
        edges_of_interest = edges
        nodes_of_interest = {n["data"]["id"] for n in nodes}

    stylesheet += [
        {
            "selector": f'node[id = "{n["data"]["id"]}"]',
            "style": {
                "opacity": 1.0 if n["data"]["id"] in nodes_of_interest else 0.15,
                "background-color": n["data"]["color"],
            },
        }
        for n in nodes
    ]

    stylesheet += [
        {
            "selector": f'edge[id = "{e["data"]["id"]}"]',
            "style": {
                "opacity": 1.0 if e in edges_of_interest else 0.05,
                "line-color": e["data"]["color"],
            },
        }
        for e in edges
    ]

    return stylesheet

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