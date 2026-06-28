import json
import pandas as pd
from statsbombpy import sb
import warnings

# Suppress NoAuthWarning
warnings.filterwarnings("ignore")

def fetch_statsbomb():
    target_comps = [
        (43, 106), # WC 2022
        (43, 3),   # WC 2018
        (55, 43),  # Euro 2020
        (1267, 107) # AFCON 2023
    ]
    
    all_matches_data = []
    
    for comp_id, season_id in target_comps:
        print(f"Fetching matches for Competition {comp_id}, Season {season_id}...")
        try:
            matches = sb.matches(competition_id=comp_id, season_id=season_id)
        except Exception as e:
            print(f"Error fetching matches: {e}")
            continue
            
        for _, match in matches.iterrows():
            try:
                home_team = match['home_team']
                away_team = match['away_team']
                
                # Fetch events
                events = sb.events(match_id=match['match_id'])
                
                home_possession = 50.0 
                away_possession = 50.0
                home_shots = len(events[(events['type'] == 'Shot') & (events['team'] == home_team)])
                away_shots = len(events[(events['type'] == 'Shot') & (events['team'] == away_team)])
                
                home_passes = len(events[(events['type'] == 'Pass') & (events['team'] == home_team)])
                away_passes = len(events[(events['type'] == 'Pass') & (events['team'] == away_team)])
                if home_passes + away_passes > 0:
                    home_possession = round((home_passes / (home_passes + away_passes)) * 100, 2)
                    away_possession = round(100 - home_possession, 2)
                
                home_corners = len(events[(events['pass_type'] == 'Corner') & (events['team'] == home_team)]) if 'pass_type' in events.columns else 0
                away_corners = len(events[(events['pass_type'] == 'Corner') & (events['team'] == away_team)]) if 'pass_type' in events.columns else 0
                
                home_fouls = len(events[(events['type'] == 'Foul Committed') & (events['team'] == home_team)])
                away_fouls = len(events[(events['type'] == 'Foul Committed') & (events['team'] == away_team)])
                
                home_yellow, home_red, away_yellow, away_red = 0, 0, 0, 0
                if 'foul_committed_card' in events.columns:
                    cards = events.dropna(subset=['foul_committed_card'])
                    home_yellow = len(cards[(cards['team'] == home_team) & (cards['foul_committed_card'].str.contains('Yellow', na=False))])
                    away_yellow = len(cards[(cards['team'] == away_team) & (cards['foul_committed_card'].str.contains('Yellow', na=False))])
                    home_red = len(cards[(cards['team'] == home_team) & (cards['foul_committed_card'].str.contains('Red', na=False))])
                    away_red = len(cards[(cards['team'] == away_team) & (cards['foul_committed_card'].str.contains('Red', na=False))])
                
                match_obj = {
                    "externalId": f"sb_{match['match_id']}",
                    "homeTeam": home_team,
                    "awayTeam": away_team,
                    "homeScore": int(match['home_score']),
                    "awayScore": int(match['away_score']),
                    "startTime": f"{match['match_date']}T{match.get('kick_off', '00:00:00')}.000Z",
                    "stats": {
                        "possessionHome": float(home_possession),
                        "possessionAway": float(away_possession),
                        "shotsOnTargetHome": home_shots,
                        "shotsOnTargetAway": away_shots,
                        "cornersHome": home_corners,
                        "cornersAway": away_corners,
                        "foulsHome": home_fouls,
                        "foulsAway": away_fouls,
                        "yellowCardsHome": home_yellow,
                        "yellowCardsAway": away_yellow,
                        "redCardsHome": home_red,
                        "redCardsAway": away_red
                    }
                }
                all_matches_data.append(match_obj)
                print(f"Processed Match: {home_team} vs {away_team}")
            except Exception as e:
                print(f"Error processing match {match['match_id']}: {e}")
                
    with open('historical_matches.json', 'w', encoding='utf-8') as f:
        json.dump(all_matches_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully saved {len(all_matches_data)} matches to historical_matches.json")

if __name__ == "__main__":
    fetch_statsbomb()
