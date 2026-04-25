                                         -                                                                             
 _____   ______           _____                  ____    ____   ____  _____   ______         _____             ______  
|\    \ |\     \     ____|\    \                |    |  |    | |    ||\    \ |\     \    ___|\    \        ___|\     \ 
 \\    \| \     \   /     /\    \               |    |  |    | |    | \\    \| \     \  /    /\    \      |    |\     \
  \|    \  \     | /     /  \    \              |    | /    // |    |  \|    \  \     ||    |  |____|     |    |/____/|
   |     \  |    ||     |    |    |             |    |/ _ _//  |    |   |     \  |    ||    |    ____  ___|    \|   | |
   |      \ |    ||     |    |    |             |    |\    \'  |    |   |      \ |    ||    |   |    ||    \    \___|/ 
   |    |\ \|    ||\     \  /    /|             |    | \    \  |    |   |    |\ \|    ||    |   |_,  ||    |\     \    
   |____||\_____/|| \_____\/____/ |             |____|  \____\ |____|   |____||\_____/||\ ___\___/  /||\ ___\|_____|   
   |    |/ \|   || \ |    ||    | /             |    |   |    ||    |   |    |/ \|   ||| |   /____ / || |    |     |   
   |____|   |___|/  \|____||____|/              |____|   |____||____|   |____|   |___|/ \|___|    | /  \|____|_____|   
     \(       )/       \(    )/                   \(       )/    \(       \(       )/     \( |____|/      \(    )/     
      '       '         '    '                     '       '      '        '       '       '   )/          '    '      
                                                                                               '                       

# SignalWatch: Truth Social Network Analysis
### DHS 622 Final Project | Muhammad Suhail Zeerak | April 2026

This project maps pro-war and anti-war discourse on Truth Social during the 
US-Iran conflict of 2026. It scrapes, stores, and analyzes posts from 186 
accounts across the period February 1 – April 14, 2026, producing a full 
interactive dashboard with network analysis, topic modeling, sentiment 
analysis, keyword tracking, engagement metrics, and AIPAC funding comparisons.

The full writeup is in `Platform_as_Power_War_as_Spectacle.pdf`.  
The raw dataset is in `final_project/data/statuses.csv` (22,780 posts).

---

## Requirements

- Python 3.11+
- PostgreSQL 14+

---

## Installation

**1. Clone the repo**
```bash
git clone https://github.com/13abu/FinalProjectDHS622.git
cd FinalProjectDHS622
```

**2. Create a virtual environment and install dependencies**
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python setup.py                  # downloads required NLTK data
```

**3. Create the database**
```bash
psql -U postgres -c "CREATE DATABASE truthsocial_db;"
```

**4. Add database credentials to `~/dhs622.cfg`**
```
[truthsocial-db]
user = postgres
password = your_postgres_password
host = localhost
port = 5432
dbname = truthsocial_db
```

**5. Import the dataset**

No scraping required — the full dataset is included in the repo.
```bash
python import_data.py
```

**6. Create a dashboard login**
```bash
python add_credentials.py
```
Enter any email and password when prompted. You will use these to log into the dashboard.

---

## Running the app

Open two terminal windows from the project root:

**Terminal 1**
```bash
python run_api.py
```

**Terminal 2**
```bash
python run_frontend.py
```

Then open `http://127.0.0.1:8050` in your browser, log in, and click **Analyze**.

---

## Project structure

```
FinalProjectDHS622/
├── final_project/
│   ├── api/
│   │   ├── routes.py           # FastAPI endpoints
│   │   └── clients.py          # Client functions for the frontend
│   ├── data/
│   │   ├── statuses.csv        # Full dataset (22,780 posts)
│   │   └── aipac.csv           # AIPAC contribution data (OpenSecrets, 2024)
│   ├── frontend/
│   │   ├── app.py              # Dash application
│   │   └── pages/
│   │       ├── login.py        # Login page
│   │       ├── welcome.py      # Landing page
│   │       └── analyze.py      # Analysis dashboard
│   └── utilities/
│       ├── db.py               # Database schema and queries
│       ├── logic.py            # Analysis functions
│       └── security_logic.py   # JWT authentication
├── scraper/
│   ├── scrape_statuses.py      # Truth Social scraper (truthbrush)
│   └── scrape_network.py       # Account metadata scraper
├── add_credentials.py          # Create dashboard login
├── export_network.py           # Export repost network to GEXF (for Gephi)
├── import_data.py              # Load CSV dataset into PostgreSQL
├── run_api.py                  # Start the FastAPI backend
├── run_frontend.py             # Start the Dash frontend
├── requirements.txt
└── setup.py
```

---

## Notes

- The scraper (`scraper/scrape_statuses.py`) requires a Truth Social account 
  and a valid bearer token. It is included for transparency but does not need 
  to be run — the full dataset is already included.
- AIPAC funding data is sourced from OpenSecrets (2024 election cycle).
- Network community detection uses the Louvain algorithm (python-louvain).
- The dashboard requires both servers running simultaneously.
```
