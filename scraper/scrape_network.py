import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from datetime import datetime, timezone
from truthbrush.api import Api
from final_project.config import TRUTHSOCIAL_USERNAME, TRUTHSOCIAL_PASSWORD, TRUTHSOCIAL_TOKEN
from final_project.utilities.db import insert_accounts, fetch_seeds

SEED_LIST = "iran_israel_war"


def extract_account_record(account: dict) -> dict:
    return {
        "account_id": account["id"],
        "handle": account["acct"],
        "display_name": account.get("display_name"),
        "followers_count": account.get("followers_count"),
        "following_count": account.get("following_count"),
        "statuses_count": account.get("statuses_count"),
        "bio": account.get("note"),
        "verified": account.get("verified", False),
        "pulled_at": datetime.now(timezone.utc),
        "api_response": json.dumps(account),
    }


def run():
    api = Api(
        username=TRUTHSOCIAL_USERNAME,
        password=TRUTHSOCIAL_PASSWORD,
        token=TRUTHSOCIAL_TOKEN,
    )

    seeds = fetch_seeds(SEED_LIST)

    for seed in seeds:
        handle = seed["handle"]
        print(f"Pulling metadata for @{handle}...")
        try:
            account = api.lookup(handle)
            if account and "id" in account:
                record = extract_account_record(account)
                insert_accounts([record])
                print(f"  → followers: {record['followers_count']}")
            else:
                print(f"  → not found")
        except Exception as e:
            print(f"  ERROR: {e}")
            continue


if __name__ == "__main__":
    run()