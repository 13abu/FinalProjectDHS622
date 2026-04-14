import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from truthbrush.api import Api
from final_project.config import TRUTHSOCIAL_USERNAME, TRUTHSOCIAL_PASSWORD, TRUTHSOCIAL_TOKEN
from final_project.utilities.db import insert_statuses, insert_accounts, fetch_seeds

SEED_LIST = "iran_israel_war"

KEYWORDS = [
    "iran", "israel", "gaza", "strike", "hamas", "hezbollah",
    "netanyahu", "aipac", "war", "missile", "tehran", "idf"
]

def extract_status_record(status: dict, account_handle: str) -> dict:
    reblog = status.get("reblog")
    content_raw = status.get("content", "") or ""
    content_clean = BeautifulSoup(content_raw, "html.parser").get_text()

    return {
        "account_handle": account_handle,
        "status_id": status["id"],
        "created_at": datetime.fromisoformat(status["created_at"].replace("Z", "+00:00")),
        "content": content_clean,
        "reblogs_count": status.get("reblogs_count", 0),
        "favourites_count": status.get("favourites_count", 0),
        "replies_count": status.get("replies_count", 0),
        "is_reblog": reblog is not None,
        "reblogged_from_handle": reblog["account"]["acct"] if reblog else None,
        "reblogged_from_id": reblog["id"] if reblog else None,
        "language": status.get("language"),
        "url": status.get("url"),
        "pulled_at": datetime.now(timezone.utc),
        "api_response": json.dumps(status),
    }


def status_matches_keywords(record: dict) -> bool:
    text = (record.get("content") or "").lower()
    return any(kw in text for kw in KEYWORDS)


def run():
    api = Api(
        username=TRUTHSOCIAL_USERNAME,
        password=TRUTHSOCIAL_PASSWORD,
        token=TRUTHSOCIAL_TOKEN,
    )

    seeds = fetch_seeds(SEED_LIST)
    tier1_handles = [s["handle"] for s in seeds if s["tier"] == 1]

    for handle in tier1_handles:
        print(f"Scraping @{handle}...")
        records = []

        try:
            for status in api.pull_statuses(handle, replies=False):
                record = extract_status_record(status, handle)
                if status_matches_keywords(record):
                    records.append(record)

            print(f"  → {len(records)} keyword-matched posts")
            insert_statuses(records)

        except Exception as e:
            print(f"  ERROR scraping @{handle}: {e}")
            continue


if __name__ == "__main__":
    run()