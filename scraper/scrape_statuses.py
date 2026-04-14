import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import time
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from truthbrush.api import Api
from final_project.config import TRUTHSOCIAL_USERNAME, TRUTHSOCIAL_PASSWORD, TRUTHSOCIAL_TOKEN
from final_project.utilities.db import insert_statuses, insert_accounts, fetch_seeds

SEED_LIST = "iran_israel_war"
START_DATE = datetime(2025, 2, 1, tzinfo=timezone.utc)
END_DATE = datetime(2026, 4, 14, tzinfo=timezone.utc)
TIER2_LIMIT = 40  # max posts for tier 2 accounts


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


def scrape_tier1(api: Api, handle: str) -> None:
    """Full scrape between START_DATE and END_DATE."""
    records = []
    count = 0

    try:
        for status in api.pull_statuses(handle, replies=False, created_after=START_DATE):
            record = extract_status_record(status, handle)

            # stop if we've gone past END_DATE
            if record["created_at"] > END_DATE:
                continue

            records.append(record)
            count += 1

            if count % 100 == 0:
                print(f"  → {count} posts collected so far...")
                insert_statuses(records)
                records = []
                time.sleep(2)

        if records:
            insert_statuses(records)

        print(f"  → done. {count} total posts saved.")

    except Exception as e:
        print(f"  ERROR: {e}")
        if records:
            insert_statuses(records)


def scrape_tier2(api: Api, handle: str) -> None:
    """Just pull the last TIER2_LIMIT posts — one API page."""
    records = []

    try:
        for status in api.pull_statuses(handle, replies=False):
            record = extract_status_record(status, handle)
            records.append(record)
            if len(records) >= TIER2_LIMIT:
                break

        insert_statuses(records)
        print(f"  → {len(records)} posts saved.")

    except Exception as e:
        print(f"  ERROR: {e}")


def run():
    api = Api(
        username=TRUTHSOCIAL_USERNAME,
        password=TRUTHSOCIAL_PASSWORD,
        token=TRUTHSOCIAL_TOKEN,
    )

    seeds = fetch_seeds(SEED_LIST)
    tier1 = [s for s in seeds if s["tier"] == 1]
    tier2 = [s for s in seeds if s["tier"] == 2]

    print(f"Starting scrape: {len(tier1)} Tier 1 accounts, {len(tier2)} Tier 2 accounts")
    print(f"Date range: {START_DATE.date()} to {END_DATE.date()}")
    print("=" * 50)

    print("\n--- TIER 1 (full scrape) ---")
    for seed in tier1:
        handle = seed["handle"]
        print(f"\nScraping @{handle} [{seed['camp']}]...")
        scrape_tier1(api, handle)
        time.sleep(15)  # 15 second pause between tier 1 accounts

    print("\n--- TIER 2 (last 40 posts) ---")
    for seed in tier2:
        handle = seed["handle"]
        print(f"Scraping @{handle}...", end=" ")
        scrape_tier2(api, handle)
        time.sleep(5)  # 5 second pause between tier 2 accounts

    print("\nDone!")


if __name__ == "__main__":
    run()