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