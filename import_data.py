import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from final_project.utilities.db import engine, meta

# Create all tables
meta.create_all(engine)

# Load CSV
df = pd.read_csv("final_project/data/statuses.csv", parse_dates=["date"])
df.rename(columns={"date": "created_at"}, inplace=True)

# Insert
df.to_sql("ts_statuses", engine, if_exists="append", index=False)
print(f"Imported {len(df)} rows into ts_statuses")