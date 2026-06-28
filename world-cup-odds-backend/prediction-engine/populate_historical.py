import os
import sys
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from statsbombpy import sb
import warnings

# Suppress NoAuthWarning
warnings.filterwarnings("ignore")

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

if "?pgbouncer=true" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("?pgbouncer=true", "")
if "&pgbouncer=true" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("&pgbouncer=true", "")
if "6543" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("6543", "5432")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_or_create_team(session, team_name: str) -> int:
    result = session.execute(text("SELECT id FROM \"Team\" WHERE name = :name LIMIT 1"), {"name": team_name}).fetchone()
    if result:
        return result[0]
    
    # Create
    result = session.execute(
        text("INSERT INTO \"Team\" (name, \"shortName\", \"updatedAt\") VALUES (:name, :short, NOW()) RETURNING id"),
        {"name": team_name, "short": team_name[:3].upper()}
    )
    return result.fetchone()[0]

def populate_statsbomb():
    # Competitions available in StatsBomb open data
    target_comps = [
        (43, 106), # WC 2022
        (43, 3),   # WC 2018
        (55, 43),  # Euro 2020
        (1267, 107) # AFCON 2023
    ]
    
    session = SessionLocal()
    try:
        total_matches = 0
        for comp_id, season_id in target_comps:
            print(f"Fetching matches for Competition {comp_id}, Season {season_id}...")
            try:
                matches = sb.matches(competition_id=comp_id, season_id=season_id)
            except Exception as e:
                print(f"Error fetching matches: {e}")
                continue
                
            for _, match in matches.iterrows():
                try:
                    match_id = str(match['match_id'])
                    # Check if already exists
                    existing = session.execute(text("SELECT id FROM \"Match\" WHERE \"externalId\" = :eid"), {"eid": f"sb_{match_id}"}).fetchone()
                    if existing:
                        continue
                        
                    home_team = match['home_team']
                    away_team = match['away_team']
                    home_score = match['home_score']
                    away_score = match['away_score']
                    
                    home_team_id = get_or_create_team(session, home_team)
                    away_team_id = get_or_create_team(session, away_team)
                    
                    start_time = pd.to_datetime(f"{match['match_date']} {match['kick_off']}")
                    
                    # Create Match
                    db_match_id = session.execute(text("""
                        INSERT INTO "Match" ("homeTeamId", "awayTeamId", "homeScore", "awayScore", "startTime", "status", "externalId", "updatedAt")
                        VALUES (:home, :away, :hs, :as, :st, 'FT', :eid, NOW())
                        RETURNING id
                    """), {
                        "home": home_team_id, "away": away_team_id, "hs": home_score, "as": away_score, 
                        "st": start_time, "eid": f"sb_{match_id}"
                    }).fetchone()[0]
                    
                    # Extract Events
                    events = sb.events(match_id=match['match_id'])
                    
                    home_possession = 50.0 # Approximation if not found
                    away_possession = 50.0
                    home_shots = len(events[(events['type'] == 'Shot') & (events['team'] == home_team)])
                    away_shots = len(events[(events['type'] == 'Shot') & (events['team'] == away_team)])
                    
                    # Passes for possession estimation
                    home_passes = len(events[(events['type'] == 'Pass') & (events['team'] == home_team)])
                    away_passes = len(events[(events['type'] == 'Pass') & (events['team'] == away_team)])
                    if home_passes + away_passes > 0:
                        home_possession = (home_passes / (home_passes + away_passes)) * 100
                        away_possession = 100 - home_possession
                    
                    home_corners = len(events[(events['pass_type'] == 'Corner') & (events['team'] == home_team)]) if 'pass_type' in events.columns else 0
                    away_corners = len(events[(events['pass_type'] == 'Corner') & (events['team'] == away_team)]) if 'pass_type' in events.columns else 0
                    
                    home_fouls = len(events[(events['type'] == 'Foul Committed') & (events['team'] == home_team)])
                    away_fouls = len(events[(events['type'] == 'Foul Committed') & (events['team'] == away_team)])
                    
                    # Cards
                    home_yellow = 0
                    home_red = 0
                    away_yellow = 0
                    away_red = 0
                    
                    if 'foul_committed_card' in events.columns:
                        cards = events.dropna(subset=['foul_committed_card'])
                        home_yellow = len(cards[(cards['team'] == home_team) & (cards['foul_committed_card'].str.contains('Yellow', na=False))])
                        away_yellow = len(cards[(cards['team'] == away_team) & (cards['foul_committed_card'].str.contains('Yellow', na=False))])
                        home_red = len(cards[(cards['team'] == home_team) & (cards['foul_committed_card'].str.contains('Red', na=False))])
                        away_red = len(cards[(cards['team'] == away_team) & (cards['foul_committed_card'].str.contains('Red', na=False))])
                    
                    # Insert MatchStats
                    session.execute(text("""
                        INSERT INTO "MatchStats" ("matchId", "possessionHome", "possessionAway", "shotsOnTargetHome", "shotsOnTargetAway",
                        "cornersHome", "cornersAway", "foulsHome", "foulsAway", "yellowCardsHome", "yellowCardsAway", "redCardsHome", "redCardsAway", "updatedAt")
                        VALUES (:mid, :ph, :pa, :sh, :sa, :ch, :ca, :fh, :fa, :yh, :ya, :rh, :ra, NOW())
                    """), {
                        "mid": db_match_id, "ph": home_possession, "pa": away_possession, "sh": home_shots, "sa": away_shots,
                        "ch": home_corners, "ca": away_corners, "fh": home_fouls, "fa": away_fouls,
                        "yh": home_yellow, "ya": away_yellow, "rh": home_red, "ra": away_red
                    })
                    
                    session.commit()
                    total_matches += 1
                    print(f"Saved Match {total_matches}: {home_team} {home_score}-{away_score} {away_team}")
                except Exception as e:
                    session.rollback()
                    print(f"Error processing match {match['match_id']}: {e}")
                    
    finally:
        session.close()
        print(f"Done. Imported {total_matches} historical matches.")

if __name__ == "__main__":
    populate_statsbomb()
