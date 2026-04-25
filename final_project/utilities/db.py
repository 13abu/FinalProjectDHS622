import sqlalchemy as sa
from sqlalchemy.sql.schema import Table as SQLAlchemyTable
from datetime import datetime
from ..config import config


def instantiate_statuses_table(my_table_name: str) -> SQLAlchemyTable:
    return sa.Table(
        my_table_name, meta,
        sa.Column("account_handle", sa.types.TEXT, primary_key=True),
        sa.Column("status_id", sa.types.TEXT, primary_key=True),
        sa.Column("created_at", sa.types.DateTime(timezone=True)),
        sa.Column("content", sa.types.TEXT, default=None),
        sa.Column("reblogs_count", sa.types.INTEGER, default=0),
        sa.Column("favourites_count", sa.types.INTEGER, default=0),
        sa.Column("replies_count", sa.types.INTEGER, default=0),
        sa.Column("is_reblog", sa.types.BOOLEAN, default=False),
        sa.Column("reblogged_from_handle", sa.types.TEXT, default=None),
        sa.Column("reblogged_from_id", sa.types.TEXT, default=None),
        sa.Column("language", sa.types.TEXT, default=None),
        sa.Column("url", sa.types.TEXT, default=None),
        sa.Column("pulled_at", sa.types.DateTime(timezone=True), default=datetime.utcnow),
        sa.Column("api_response", sa.types.JSON, nullable=False),
    )


def instantiate_accounts_table(my_table_name: str) -> SQLAlchemyTable:
    return sa.Table(
        my_table_name, meta,
        sa.Column("account_id", sa.types.TEXT, primary_key=True),
        sa.Column("handle", sa.types.TEXT, nullable=False),
        sa.Column("display_name", sa.types.TEXT, default=None),
        sa.Column("followers_count", sa.types.INTEGER, default=None),
        sa.Column("following_count", sa.types.INTEGER, default=None),
        sa.Column("statuses_count", sa.types.INTEGER, default=None),
        sa.Column("bio", sa.types.TEXT, default=None),
        sa.Column("verified", sa.types.BOOLEAN, default=False),
        sa.Column("pulled_at", sa.types.DateTime(timezone=True), default=datetime.utcnow),
        sa.Column("api_response", sa.types.JSON, nullable=False),
    )


def instantiate_seeds_table(my_table_name: str) -> SQLAlchemyTable:
    return sa.Table(
        my_table_name, meta,
        sa.Column("handle", sa.types.TEXT, primary_key=True),
        sa.Column("seed_list", sa.types.TEXT, primary_key=True),
        sa.Column("tier", sa.types.INTEGER, default=1),
        sa.Column("camp", sa.types.TEXT, default=None),
    )


def instantiate_credentials_table(my_table_name: str) -> SQLAlchemyTable:
    return sa.Table(
        my_table_name, meta,
        sa.Column("email", sa.types.TEXT, primary_key=True),
        sa.Column("password", sa.types.TEXT, nullable=False),
    )


def insert_statuses(records: list[dict]) -> None:
    if not records:
        return
    existing = sa.select(
        statuses_table.c.account_handle,
        statuses_table.c.status_id,
    ).where(
        statuses_table.c.status_id.in_([r["status_id"] for r in records])
    )
    with engine.connect() as conn:
        existing_ids = {row[1] for row in conn.execute(existing).fetchall()}

    new_records = [r for r in records if r["status_id"] not in existing_ids]
    if new_records:
        with engine.connect() as conn:
            conn.execute(sa.insert(statuses_table).values(new_records))
            conn.commit()


def insert_accounts(records: list[dict]) -> None:
    if not records:
        return
    for record in records:
        stmt = sa.dialects.postgresql.insert(accounts_table).values(record)
        stmt = stmt.on_conflict_do_update(
            index_elements=["account_id"],
            set_={"followers_count": record["followers_count"],
                  "following_count": record["following_count"],
                  "statuses_count": record["statuses_count"],
                  "pulled_at": datetime.utcnow()}
        )
        with engine.connect() as conn:
            conn.execute(stmt)
            conn.commit()


def insert_seeds(records: list[dict]) -> None:
    if not records:
        return
    with engine.connect() as conn:
        for record in records:
            try:
                conn.execute(sa.insert(seeds_table).values(record))
                conn.commit()
            except Exception:
                conn.rollback()


def insert_credentials(records: list[dict]) -> None:
    with engine.connect() as conn:
        conn.execute(sa.insert(credentials_table).values(records))
        conn.commit()


def fetch_credentials_if_exist(email: str) -> dict | None:
    with engine.connect() as conn:
        rp = conn.execute(
            sa.select(credentials_table).where(credentials_table.c.email == email)
        )
    records = [dict(r._mapping) for r in rp.fetchall()]
    return records[0] if records else None


def fetch_seeds(seed_list: str) -> list[dict]:
    with engine.connect() as conn:
        rp = conn.execute(
            sa.select(seeds_table).where(seeds_table.c.seed_list == seed_list)
        )
    return [dict(r._mapping) for r in rp.fetchall()]


def fetch_statuses_for_handles(handles: list[str], start_date: str, end_date: str) -> list[dict]:
    with engine.connect() as conn:
        rp = conn.execute(
            sa.select(statuses_table).where(
                statuses_table.c.account_handle.in_(handles),
                statuses_table.c.created_at >= datetime.strptime(start_date, "%Y-%m-%d"),
                statuses_table.c.created_at <= datetime.strptime(end_date, "%Y-%m-%d"),
            )
        )
    return [dict(r._mapping) for r in rp.fetchall()]


def fetch_repost_edges(handles: list[str], start_date: str, end_date: str) -> list[dict]:
    with engine.connect() as conn:
        rp = conn.execute(
            sa.select(
                statuses_table.c.account_handle,
                statuses_table.c.reblogged_from_handle,
                sa.func.count().label("count"),
            ).where(
                statuses_table.c.account_handle.in_(handles),
                statuses_table.c.is_reblog == True,
                statuses_table.c.reblogged_from_handle.isnot(None),
                statuses_table.c.created_at >= datetime.strptime(start_date, "%Y-%m-%d"),
                statuses_table.c.created_at <= datetime.strptime(end_date, "%Y-%m-%d"),
            ).group_by(
                statuses_table.c.account_handle,
                statuses_table.c.reblogged_from_handle,
            )
        )
    return [dict(r._mapping) for r in rp.fetchall()]


engine = sa.create_engine(
    f"postgresql://"
    f"{config['truthsocial-db']['user']}:"
    f"{config['truthsocial-db']['password']}"
    f"@{config['truthsocial-db']['host']}:"
    f"{config['truthsocial-db']['port']}/"
    f"{config['truthsocial-db']['dbname']}",
    echo=False,
    pool_size=10,
    max_overflow=0,
)

meta = sa.MetaData()
statuses_table = instantiate_statuses_table("ts_statuses")
accounts_table = instantiate_accounts_table("ts_accounts")
seeds_table = instantiate_seeds_table("ts_seeds")
credentials_table = instantiate_credentials_table("ts_credentials")
meta.create_all(engine)

SEEDS = [
    # TIER 1 — Pro-war/Pro-Israel
    {"handle": "realDonaldTrump", "seed_list": "iran_israel_war", "tier": 1, "camp": "pro_war"},
    {"handle": "DonaldJTrumpJr", "seed_list": "iran_israel_war", "tier": 1, "camp": "pro_war"},
    {"handle": "DanScavino", "seed_list": "iran_israel_war", "tier": 1, "camp": "pro_war"},
    {"handle": "TrumpWarRoom", "seed_list": "iran_israel_war", "tier": 1, "camp": "pro_war"},
    {"handle": "SecRubio", "seed_list": "iran_israel_war", "tier": 1, "camp": "pro_war"},
    {"handle": "SpeakerJohnson", "seed_list": "iran_israel_war", "tier": 1, "camp": "pro_war"},
    {"handle": "seanhannity", "seed_list": "iran_israel_war", "tier": 1, "camp": "pro_war"},
    {"handle": "TheDailyWire", "seed_list": "iran_israel_war", "tier": 1, "camp": "pro_war"},
    {"handle": "SteveBannonsWarRoom", "seed_list": "iran_israel_war", "tier": 1, "camp": "pro_war"},
    {"handle": "karolineleavitt", "seed_list": "iran_israel_war", "tier": 1, "camp": "pro_war"},
    # TIER 1 — Anti-war/Tucker
    {"handle": "TuckerCarlson", "seed_list": "iran_israel_war", "tier": 1, "camp": "anti_war"},
    {"handle": "RepMattGaetz", "seed_list": "iran_israel_war", "tier": 1, "camp": "anti_war"},
    {"handle": "RevolverNews", "seed_list": "iran_israel_war", "tier": 1, "camp": "anti_war"},
    {"handle": "RandPaul", "seed_list": "iran_israel_war", "tier": 1, "camp": "anti_war"},
    {"handle": "TulsiGabbard", "seed_list": "iran_israel_war", "tier": 1, "camp": "anti_war"},
    {"handle": "russellbrand", "seed_list": "iran_israel_war", "tier": 1, "camp": "anti_war"},
    {"handle": "RWMaloneMD", "seed_list": "iran_israel_war", "tier": 1, "camp": "anti_war"},
    {"handle": "DaveRubin", "seed_list": "iran_israel_war", "tier": 1, "camp": "anti_war"},
    {"handle": "KristiNoem", "seed_list": "iran_israel_war", "tier": 1, "camp": "anti_war"},
    # TIER 1 — Bridge
    {"handle": "JDVance1", "seed_list": "iran_israel_war", "tier": 1, "camp": "bridge"},
    {"handle": "Charliekirk", "seed_list": "iran_israel_war", "tier": 1, "camp": "bridge"},
    # TIER 2 — Politicians
    {"handle": "SteveScalise", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "GOPMajorityWhip", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "replisamcclain", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "RepMikeCollins", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "repgregsteube", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "repandybiggsaz", "seed_list": "iran_israel_war", "tier": 2, "camp": "anti_war"},
    {"handle": "BurgessOwens", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "MikeGarcia", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "KariLake", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "DevinNunes", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "TomFitton", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "JohnRatcliffe", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "DNITulsiGabbard", "seed_list": "iran_israel_war", "tier": 2, "camp": "bridge"},
    {"handle": "RepBrianJack", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    # TIER 2 — Media
    {"handle": "FoxNews", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "breitbartnews", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "epochtimes", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "OAN", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "NewsMax", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "RealClearPolitics", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "gatewaypundit", "seed_list": "iran_israel_war", "tier": 2, "camp": "anti_war"},
    {"handle": "DailySignal", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "washtimes", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "humanevents", "seed_list": "iran_israel_war", "tier": 2, "camp": "anti_war"},
    {"handle": "CitizenFreePress", "seed_list": "iran_israel_war", "tier": 2, "camp": "anti_war"},
    {"handle": "disclosetv", "seed_list": "iran_israel_war", "tier": 2, "camp": "anti_war"},
    # TIER 2 — Commentators
    {"handle": "mariabartiromo", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "greggjarrett", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "seanspicer", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "TrishRegan", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "OfficialBillOReilly", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "jordansekulow", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "mirandadevine", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "ScottPresler", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "BrandonStraka", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "JordanSchachtel", "seed_list": "iran_israel_war", "tier": 2, "camp": "anti_war"},
    {"handle": "jsolomonreports", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "Breaking911", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "rapidresponse47", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},

# ── New Tier 2 additions ──────────────────────────────────────────────────
    {"handle": "GovLarryRhoden", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "DOGEcommittee", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "bolsonarojair", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "DAGToddBlanche", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "HouseCommerce", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "WarrenZeiders", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "repjasonsmith", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "lindamcmahon", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "realwayneroot", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "OkDeptOfEd", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "larryeldersage", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "jmclghln", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "fivetimesaugust", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "kevinolearytv", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "rogerlsimon", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "davidbernhardt", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "Woodsish", "seed_list": "iran_israel_war", "tier": 2, "camp": "anti_war"},
    {"handle": "oldrowoutdoors", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "tomemmer", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "TheLeeGreenwood", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "ThaddeusMcCotter", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "VDH", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "RealSKeshel", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "AGAndrewBaileyMO", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "conceptualjames", "seed_list": "iran_israel_war", "tier": 2, "camp": "anti_war"},
    {"handle": "SteakforBreakfast", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "Grandoldmemes", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "AmazingPeople", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "bkilmeade", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "afbranco", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "RTMnews", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "jaysekulow", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "Dogsoftruth", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "NRCC", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "StephenM", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "rogerkimball1", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "TheTravelersDust", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "cpac", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "TruthSoccer", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "WendellHusebo", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "marymargaretolohan", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "AlinaHabba", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "hayleycaronia", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "RepAdrianSmith", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "realgovnewsom40", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "MSchlapp", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "sharylattkisson", "seed_list": "iran_israel_war", "tier": 2, "camp": "anti_war"},
    {"handle": "WhatleyforNC", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "JessAnderson", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "archaeologyart", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "HouseAdmin", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "ilpresidento", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "RealPJW", "seed_list": "iran_israel_war", "tier": 2, "camp": "anti_war"},
    {"handle": "epaleezeldin", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "L3HarrisTech", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "GovBraun", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "AGPamBondi", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "michaelbschwab", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "TruthSocialFunds", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "jeanmars", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "realamericasvoice", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "ICEgov", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "dailycaller", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "Tommy_Robinson", "seed_list": "iran_israel_war", "tier": 2, "camp": "anti_war"},
    {"handle": "SenTedBuddNC", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "USAmbassadorGR", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "SECgov", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "SECPaulSAtkins", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "bearingarms", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "WatcherGuru", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "armedforcespress", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "western_journal", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "newyorksun", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "PJMedia", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "hotair", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "unusual_whales", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "ResisttheMainstream", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "ThePostMillennial", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "mxmnews", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "ConservativeBrief", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "newsbusters", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "Townhall", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "RedState", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "DCEnquirer", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "justthenews", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "reclaimthenet", "seed_list": "iran_israel_war", "tier": 2, "camp": "anti_war"},
    {"handle": "WashingtonExaminer", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "FDRLST", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "RSBN", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "americangreatness", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "GBNews", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "WhiteHouse", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "USAmbJapan", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "sba_kelly", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "TSAgov", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "SecDuffy", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "seckennedy", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "SecNoem", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "jasonrantz", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "USAmbUK", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "EDSecMcMahon", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "USAmbMex", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "roscarborough", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "RobertCahaly", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "Realmattboyle", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "Raheem", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "shaunkraisman", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "biancadelagarzaofficial", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "danball", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "Bachman", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "ericbolling", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "robcarsonshow", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "CarlHigbie", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "RobFinnerty", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "SecWar", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "ChrisSalcedoShow", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "JohnnyTabacco", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "stinchfield1776", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "benny", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "edhenry", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "truthsupport", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "ClaremontInstitute", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "IAPolls2022", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "Trafalgar_Group", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "Rasmussen_Poll", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "JudicialWatch", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "Electionwiz", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "USAmbNATO", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},
    {"handle": "PressSec", "seed_list": "iran_israel_war", "tier": 2, "camp": "pro_war"},

]

insert_seeds(SEEDS)