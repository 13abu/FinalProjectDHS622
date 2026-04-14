from fastapi import APIRouter, Body, HTTPException
from starlette.requests import Request

from ..utilities.logic import (
    get_seed_list_names,
    get_seed_preview,
    get_top_statuses,
    get_time_series_data,
    make_repost_network,
    make_cytoscape_elements,
)
from ..utilities.security_logic import (
    check_credentials,
    create_jwt,
    verify_token,
    parse_token_from_starlette,
)

router = APIRouter()


@router.post("/login")
async def login(
    request: Request,
    email: str = Body(embed=True),
    password: str = Body(embed=True),
):
    result = check_credentials(email)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if password != result["password"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_jwt(email)}


@router.get("/me")
async def me(request: Request):
    email = verify_token(parse_token_from_starlette(request))
    return {"data": email}


@router.get("/seed_list_names")
async def seed_list_names(request: Request):
    verify_token(parse_token_from_starlette(request))
    return {"data": get_seed_list_names()}


@router.post("/seed_preview")
async def seed_preview(
    request: Request,
    seed_list: str = Body(embed=True),
):
    verify_token(parse_token_from_starlette(request))
    return {"data": get_seed_preview(seed_list)}


@router.post("/top_statuses")
async def top_statuses(
    request: Request,
    seed_list: str = Body(embed=True),
    start_date: str = Body(embed=True),
    end_date: str = Body(embed=True),
    limit: int = Body(embed=True, default=100),
):
    verify_token(parse_token_from_starlette(request))
    records = get_top_statuses(seed_list, start_date, end_date, limit)
    for r in records:
        if hasattr(r.get("created_at"), "isoformat"):
            r["created_at"] = r["created_at"].isoformat()
        if hasattr(r.get("pulled_at"), "isoformat"):
            r["pulled_at"] = r["pulled_at"].isoformat()
    return {"data": records}


@router.post("/time_series")
async def time_series(
    request: Request,
    seed_list: str = Body(embed=True),
    start_date: str = Body(embed=True),
    end_date: str = Body(embed=True),
    unit: str = Body(embed=True, default="day"),
):
    verify_token(parse_token_from_starlette(request))
    records = get_time_series_data(seed_list, start_date, end_date, unit)
    return {
        "data": [
            {"dt": r["dt"].strftime("%Y-%m-%d %H:%M:%SZ"), "count": r["count"]}
            for r in records
        ]
    }


@router.post("/repost_network")
async def repost_network(
    request: Request,
    seed_list: str = Body(embed=True),
    start_date: str = Body(embed=True),
    end_date: str = Body(embed=True),
    network_max_size: int = Body(embed=True, default=200),
):
    verify_token(parse_token_from_starlette(request))
    G = make_repost_network(seed_list, start_date, end_date, network_max_size or None)
    nodes, edges = make_cytoscape_elements(G)
    return {
        "data": {
            "nodes": nodes,
            "edges": edges,
            "num_nodes": len(G.nodes()),
            "num_edges": len(G.edges()),
        }
    }