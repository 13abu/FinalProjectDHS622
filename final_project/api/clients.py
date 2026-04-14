import requests
from urllib.parse import urljoin
from datetime import datetime

from ..config import api_base


def format_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%SZ")


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def post_login(email: str, password: str) -> str | None:
    resp = requests.post(
        urljoin(api_base, "login"),
        json={"email": email, "password": password},
    )
    if resp.status_code != 200:
        return None
    return resp.json()["token"]


def get_seed_list_names(token: str) -> list[dict]:
    resp = requests.get(
        urljoin(api_base, "seed_list_names"),
        headers=_auth_headers(token),
    )
    resp.raise_for_status()
    return resp.json()["data"]


def post_seed_preview(token: str, seed_list: str) -> list[dict]:
    resp = requests.post(
        urljoin(api_base, "seed_preview"),
        json={"seed_list": seed_list},
        headers=_auth_headers(token),
    )
    resp.raise_for_status()
    return resp.json()["data"]


def post_top_statuses(
    token: str, seed_list: str, start_date: str, end_date: str, limit: int = 100
) -> list[dict]:
    resp = requests.post(
        urljoin(api_base, "top_statuses"),
        json={
            "seed_list": seed_list,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
        },
        headers=_auth_headers(token),
    )
    resp.raise_for_status()
    return resp.json()["data"]


def post_time_series(
    token: str, seed_list: str, start_date: str, end_date: str, unit: str = "day"
) -> list[dict]:
    resp = requests.post(
        urljoin(api_base, "time_series"),
        json={
            "seed_list": seed_list,
            "start_date": start_date,
            "end_date": end_date,
            "unit": unit,
        },
        headers=_auth_headers(token),
    )
    resp.raise_for_status()
    records = resp.json()["data"]
    for r in records:
        r["dt"] = format_date(r["dt"])
    return records


def post_repost_network(
    token: str,
    seed_list: str,
    start_date: str,
    end_date: str,
    network_max_size: int = 200,
) -> dict:
    resp = requests.post(
        urljoin(api_base, "repost_network"),
        json={
            "seed_list": seed_list,
            "start_date": start_date,
            "end_date": end_date,
            "network_max_size": network_max_size,
        },
        headers=_auth_headers(token),
    )
    resp.raise_for_status()
    return resp.json()["data"]