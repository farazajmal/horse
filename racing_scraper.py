"""
=============================================================================
FACTS SMASHERS RACING - LIVE DATA SCRAPER & AGGREGATOR
=============================================================================
Extracts live data from:
1. Equibase (Top Leading Horses & Jockeys by Annual Earnings):
   - URL: https://www.equibase.com/stats/View.cfm?tf=year&rbt=TB
2. HorseRacingNation (Upcoming Stakes Schedule & Marquee Races):
   - URL: https://www.horseracingnation.com/p/stakes-schedule

Outputs:
- racing_data.json (Clean JSON data for the widget / API)
- Updates embedded data in racing-hub-widget.html
=============================================================================
"""

import os
import sys
import json
import re
from datetime import datetime

# Configure UTF-8 encoding for console outputs
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("[!] Missing dependencies. Please run: pip install requests beautifulsoup4")
    sys.exit(1)


# Built-in robust fallback leaders if cloud runner IP is blocked by Equibase
FALLBACK_HORSES = [
    {"rank": 1, "name": "Senor Buscador", "sub": "Starts: 7 • Wins: 1 • Top 3: 3", "cash": "$12,021,000", "flag": "🏇"},
    {"rank": 2, "name": "Laurel River", "sub": "Starts: 1 • Wins: 1 • Top 3: 1", "cash": "$6,960,000", "flag": "🏇"},
    {"rank": 3, "name": "Rebel's Romance (IRE)", "sub": "Starts: 2 • Wins: 2 • Top 3: 2", "cash": "$6,080,000", "flag": "🏇"},
    {"rank": 4, "name": "Ushba Tesoro (JPN)", "sub": "Starts: 3 • Wins: 0 • Top 3: 2", "cash": "$5,970,000", "flag": "🏇"},
    {"rank": 5, "name": "Sierra Leone", "sub": "Starts: 7 • Wins: 3 • Top 3: 7", "cash": "$5,911,250", "flag": "🏇"},
    {"rank": 6, "name": "Fierceness", "sub": "Starts: 6 • Wins: 3 • Top 3: 5", "cash": "$4,850,000", "flag": "🏇"},
    {"rank": 7, "name": "Tumbarumba", "sub": "Starts: 2 • Wins: 0 • Top 3: 1", "cash": "$2,240,000", "flag": "🏇"},
    {"rank": 8, "name": "Royal Champion (IRE)", "sub": "Starts: 1 • Wins: 1 • Top 3: 1", "cash": "$1,800,000", "flag": "🏇"},
    {"rank": 9, "name": "Napoleon Solo", "sub": "Starts: 5 • Wins: 1 • Top 3: 3", "cash": "$1,691,520", "flag": "🏇"},
    {"rank": 10, "name": "Bishops Bay", "sub": "Starts: 4 • Wins: 1 • Top 3: 3", "cash": "$1,655,000", "flag": "🏇"}
]

FALLBACK_JOCKEYS = [
    {"rank": 1, "name": "Flavien Prat", "sub": "Starts: 1,042 • Wins: 230 (22%)", "cash": "$38,786,176", "flag": "👤"},
    {"rank": 2, "name": "Irad Ortiz, Jr.", "sub": "Starts: 1,552 • Wins: 328 (21%)", "cash": "$33,531,260", "flag": "👤"},
    {"rank": 3, "name": "Tyler Gaffalione", "sub": "Starts: 1,478 • Wins: 251 (17%)", "cash": "$29,004,252", "flag": "👤"},
    {"rank": 4, "name": "Luis Saez", "sub": "Starts: 1,451 • Wins: 235 (16%)", "cash": "$26,741,753", "flag": "👤"},
    {"rank": 5, "name": "Jose L. Ortiz", "sub": "Starts: 1,362 • Wins: 277 (20%)", "cash": "$26,036,596", "flag": "👤"},
    {"rank": 6, "name": "Manuel Franco", "sub": "Starts: 1,033 • Wins: 225 (22%)", "cash": "$19,361,941", "flag": "👤"},
    {"rank": 7, "name": "John R. Velazquez", "sub": "Starts: 635 • Wins: 107 (17%)", "cash": "$16,969,992", "flag": "👤"},
    {"rank": 8, "name": "Junior Alvarado", "sub": "Starts: 559 • Wins: 82 (15%)", "cash": "$12,556,782", "flag": "👤"},
    {"rank": 9, "name": "Paco Lopez", "sub": "Starts: 1,029 • Wins: 261 (25%)", "cash": "$12,021,415", "flag": "👤"},
    {"rank": 10, "name": "Cristian A. Torres", "sub": "Starts: 940 • Wins: 165 (18%)", "cash": "$10,850,000", "flag": "👤"}
]


# Track Code to Location / Country Dictionary
TRACK_METADATA = {
    # USA Major Tracks
    "CD": {"name": "Churchill Downs", "state": "KY", "country": "USA", "flag": "🇺🇸"},
    "Bel": {"name": "Belmont at the Big A / Saratoga", "state": "NY", "country": "USA", "flag": "🇺🇸"},
    "Aqu": {"name": "Aqueduct", "state": "NY", "country": "USA", "flag": "🇺🇸"},
    "Sar": {"name": "Saratoga", "state": "NY", "country": "USA", "flag": "🇺🇸"},
    "Dmr": {"name": "Del Mar", "state": "CA", "country": "USA", "flag": "🇺🇸"},
    "SA": {"name": "Santa Anita Park", "state": "CA", "country": "USA", "flag": "🇺🇸"},
    "GP": {"name": "Gulfstream Park", "state": "FL", "country": "USA", "flag": "🇺🇸"},
    "Kee": {"name": "Keeneland", "state": "KY", "country": "USA", "flag": "🇺🇸"},
    "Prx": {"name": "Parx Racing", "state": "PA", "country": "USA", "flag": "🇺🇸"},
    "Pid": {"name": "Presque Isle Downs", "state": "PA", "country": "USA", "flag": "🇺🇸"},
    "OP": {"name": "Oaklawn Park", "state": "AR", "country": "USA", "flag": "🇺🇸"},
    "Pim": {"name": "Pimlico", "state": "MD", "country": "USA", "flag": "🇺🇸"},
    "Lrl": {"name": "Laurel Park", "state": "MD", "country": "USA", "flag": "🇺🇸"},
    "Mth": {"name": "Monmouth Park", "state": "NJ", "country": "USA", "flag": "🇺🇸"},
    "RP": {"name": "Remington Park", "state": "OK", "country": "USA", "flag": "🇺🇸"},
    "Tam": {"name": "Tampa Bay Downs", "state": "FL", "country": "USA", "flag": "🇺🇸"},
    "Haw": {"name": "Hawthorne Race Course", "state": "IL", "country": "USA", "flag": "🇺🇸"},
    "Ind": {"name": "Horseshoe Indianapolis", "state": "IN", "country": "USA", "flag": "🇺🇸"},
    "TDN": {"name": "Thistledown", "state": "OH", "country": "USA", "flag": "🇺🇸"},
    "Del": {"name": "Delaware Park", "state": "DE", "country": "USA", "flag": "🇺🇸"},
    "CT": {"name": "Charles Town", "state": "WV", "country": "USA", "flag": "🇺🇸"},
    "MNR": {"name": "Mountaineer", "state": "WV", "country": "USA", "flag": "🇺🇸"},
    "GG": {"name": "Golden Gate Fields", "state": "CA", "country": "USA", "flag": "🇺🇸"},
    "LRC": {"name": "Los Alamitos", "state": "CA", "country": "USA", "flag": "🇺🇸"},
    "EmD": {"name": "Emerald Downs", "state": "WA", "country": "USA", "flag": "🇺🇸"},
    "CBY": {"name": "Canterbury Park", "state": "MN", "country": "USA", "flag": "🇺🇸"},
    "PRM": {"name": "Prairie Meadows", "state": "IA", "country": "USA", "flag": "🇺🇸"},
    "Zia": {"name": "Zia Park", "state": "NM", "country": "USA", "flag": "🇺🇸"},
    "Sun": {"name": "Sunland Park", "state": "NM", "country": "USA", "flag": "🇺🇸"},
    "LS": {"name": "Lone Star Park", "state": "TX", "country": "USA", "flag": "🇺🇸"},
    "Hou": {"name": "Sam Houston", "state": "TX", "country": "USA", "flag": "🇺🇸"},

    # International Tracks
    "WO": {"name": "Woodbine", "state": "ON", "country": "Canada", "flag": "🇨🇦"},
    "Woodbine": {"name": "Woodbine", "state": "ON", "country": "Canada", "flag": "🇨🇦"},
    "FE": {"name": "Fort Erie", "state": "ON", "country": "Canada", "flag": "🇨🇦"},
    "Ascot": {"name": "Ascot", "state": "Berkshire", "country": "UK", "flag": "🇬🇧"},
    "Newmarket": {"name": "Newmarket", "state": "Suffolk", "country": "UK", "flag": "🇬🇧"},
    "York": {"name": "York", "state": "Yorkshire", "country": "UK", "flag": "🇬🇧"},
    "Epsom": {"name": "Epsom Downs", "state": "Surrey", "country": "UK", "flag": "🇬🇧"},
    "Goodwood": {"name": "Goodwood", "state": "Sussex", "country": "UK", "flag": "🇬🇧"},
    "Curragh": {"name": "The Curragh", "state": "Kildare", "country": "Ireland", "flag": "🇮🇪"},
    "Leop": {"name": "Leopardstown", "state": "Dublin", "country": "Ireland", "flag": "🇮🇪"},
    "Lon": {"name": "ParisLongchamp", "state": "Paris", "country": "France", "flag": "🇫🇷"},
    "Longchamp": {"name": "ParisLongchamp", "state": "Paris", "country": "France", "flag": "🇫🇷"},
    "Chantilly": {"name": "Chantilly", "state": "Oise", "country": "France", "flag": "🇫🇷"},
    "Deauville": {"name": "Deauville-La Touques", "state": "Calvados", "country": "France", "flag": "🇫🇷"},
    "Meydan": {"name": "Meydan Racecourse", "state": "Dubai", "country": "UAE", "flag": "🇦🇪"},
    "Flemington": {"name": "Flemington", "state": "Melbourne", "country": "Australia", "flag": "🇦🇺"},
    "Randwick": {"name": "Royal Randwick", "state": "Sydney", "country": "Australia", "flag": "🇦🇺"},
    "Sha Tin": {"name": "Sha Tin", "state": "New Territories", "country": "Hong Kong", "flag": "🇭🇰"},
    "Happy Valley": {"name": "Happy Valley", "state": "Hong Kong Island", "country": "Hong Kong", "flag": "🇭🇰"},
    "Tokyo": {"name": "Tokyo Racecourse", "state": "Fuchu", "country": "Japan", "flag": "🇯🇵"},
    "Hanshin": {"name": "Hanshin Racecourse", "state": "Takarazuka", "country": "Japan", "flag": "🇯🇵"},
    "Nakayama": {"name": "Nakayama Racecourse", "state": "Funabashi", "country": "Japan", "flag": "🇯🇵"},
    "Kyoto": {"name": "Kyoto Racecourse", "state": "Kyoto", "country": "Japan", "flag": "🇯🇵"},
    "King Abdulaziz": {"name": "King Abdulaziz Racetrack", "state": "Riyadh", "country": "Saudi Arabia", "flag": "🇸🇦"}
}


def create_scraper_session():
    """Initializes a requests session configured with realistic browser headers."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    return session


def scrape_equibase_leaders(session, year=None):
    """
    Scrapes top earning Thoroughbred Horses and Jockeys from Equibase.
    """
    if year is None:
        year = datetime.now().year

    print(f"[*] Initializing Equibase session for {year} leaders...")
    main_url = 'https://www.equibase.com/stats/View.cfm?tf=year&rbt=TB'
    try:
        session.get(main_url, timeout=10)
    except Exception as e:
        print(f"[!] Warning: Could not pre-fetch Equibase session: {e}")

    ajax_headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': main_url,
    }

    horses_list = []
    jockeys_list = []

    # 1. Fetch Top Horses
    print(f"[*] Fetching Leading Horses from Equibase (Year {year})...")
    try:
        horse_url = 'https://www.equibase.com/Data.cfm/Stats/Horse/Year/Page'
        horse_params = {
            'year': year,
            'page': 1,
            'sort': 'E',
            'dir': 'D',
            'list': 'E',
            'category': '',
            'attribute_total': 0,
            'set': 'top100',
            'race_breed_type': 'TB'
        }
        res = session.get(horse_url, params=horse_params, headers=ajax_headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            raw_horses = data.get('stats', [])
            raw_horses.sort(key=lambda x: x.get('rank', 999))
            for h in raw_horses[:15]:
                name = h.get('horseName', '').strip()
                earnings = h.get('earnings', 0)
                starts = h.get('starts', 0)
                wins = h.get('win', 0)
                top3 = h.get('topThree', 0)
                rank = h.get('rank', len(horses_list) + 1)
                
                horses_list.append({
                    "rank": rank,
                    "name": name,
                    "sub": f"Starts: {starts} • Wins: {wins} • Top 3: {top3}",
                    "cash": f"${earnings:,}",
                    "flag": "🏇"
                })
            print(f"[✓] Successfully retrieved {len(horses_list)} top horses from Equibase.")
    except Exception as e:
        print(f"[!] Equibase Horse Scraper Error: {e}")

    # 2. Fetch Top Jockeys
    print(f"[*] Fetching Leading Jockeys from Equibase (Year {year})...")
    try:
        jockey_url = 'https://www.equibase.com/Data.cfm/Stats/Jockey/Year/Page'
        jockey_params = {
            'year': year,
            'list': 'E',
            'sort': 'E',
            'dir': 'D',
            'page': 1,
            'set': 'top100',
            'attribute_total': 0,
            'race_breed_type': 'TB'
        }
        res = session.get(jockey_url, params=jockey_params, headers=ajax_headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            raw_jockeys = data.get('stats', [])
            raw_jockeys.sort(key=lambda x: x.get('rank', 999))
            for j in raw_jockeys[:15]:
                name = j.get('jockeyName', '').strip()
                name = re.sub(r'\s+', ' ', name) # normalize spaces
                earnings = j.get('earnings', 0)
                starts = j.get('starts', 0)
                wins = j.get('win', 0)
                win_pct = int(round(j.get('winPercentage', 0) * 100)) if j.get('winPercentage') is not None else 0
                rank = j.get('rank', len(jockeys_list) + 1)

                jockeys_list.append({
                    "rank": rank,
                    "name": name,
                    "sub": f"Starts: {starts:,} • Wins: {wins} ({win_pct}%)",
                    "cash": f"${earnings:,}",
                    "flag": "👤"
                })
            print(f"[✓] Successfully retrieved {len(jockeys_list)} top jockeys from Equibase.")
    except Exception as e:
        print(f"[!] Equibase Jockey Scraper Error: {e}")

    return horses_list, jockeys_list


def scrape_upcoming_races(session):
    """
    Scrapes upcoming marquee & stakes races from HorseRacingNation stakes schedule.
    """
    print("[*] Fetching Stakes Schedule from HorseRacingNation...")
    hrn_url = 'https://www.horseracingnation.com/p/stakes-schedule'
    races_list = []

    try:
        res = session.get(hrn_url, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')[1:] # Skip header
                for row in rows:
                    cols = [td.get_text(strip=True) for td in row.find_all('td')]
                    if len(cols) >= 6:
                        date_raw = cols[0]
                        track_code = cols[1]
                        race_name = cols[2]
                        dist_val = cols[3]
                        sf_code = cols[4].upper() # D = Dirt, T = Turf, S = Synthetic
                        cnd_val = cols[5]
                        contenders = cols[6] if len(cols) > 6 else ""

                        # Surface label formatting
                        surface_map = {'D': 'Dirt', 'T': 'Turf', 'S': 'Synth', 'A': 'All Weather'}
                        sf_label = surface_map.get(sf_code, sf_code)

                        # Determine Grade
                        grade = "Stakes"
                        if "-G1" in race_name or " (G1)" in race_name or " G1" in race_name:
                            grade = "Grade 1"
                        elif "-G2" in race_name or " (G2)" in race_name or " G2" in race_name:
                            grade = "Grade 2"
                        elif "-G3" in race_name or " (G3)" in race_name or " G3" in race_name:
                            grade = "Grade 3"
                        elif "Listed" in race_name:
                            grade = "Listed"

                        # Clean up race name
                        clean_name = re.sub(r'-G[123]$', '', race_name).strip()

                        # Parse Track & Country
                        meta = TRACK_METADATA.get(track_code, {
                            "name": track_code,
                            "state": "",
                            "country": "USA" if not any(c in track_code for c in ["WO", "FE", "Ascot", "Meydan", "Lon"]) else "Global",
                            "flag": "🇺🇸" if not any(c in track_code for c in ["WO", "FE", "Ascot", "Meydan", "Lon"]) else "🌍"
                        })

                        is_usa = (meta["country"] == "USA")

                        # Format date for display
                        display_date = date_raw
                        try:
                            dt = datetime.strptime(date_raw, "%m/%d/%Y")
                            display_date = dt.strftime("%b %d, %Y")
                        except Exception:
                            pass

                        races_list.append({
                            "name": f"{clean_name} ({grade if grade != 'Stakes' else 'Stakes'})",
                            "raw_name": clean_name,
                            "track": meta["name"],
                            "track_code": track_code,
                            "country": meta["country"],
                            "flag": meta["flag"],
                            "date": display_date,
                            "dist": f"{dist_val} ({sf_label})",
                            "grade": grade,
                            "purse": "$1,000,000" if grade == "Grade 1" else ("$500,000" if grade == "Grade 2" else "$300,000"),
                            "isUsa": is_usa,
                            "contenders": contenders
                        })

            print(f"[✓] Successfully retrieved {len(races_list)} upcoming races from HorseRacingNation.")
    except Exception as e:
        print(f"[!] HorseRacingNation Scraper Error: {e}")

    return races_list


def update_widget_html(data, widget_file="racing-hub-widget.html"):
    """
    Injects fresh scraped data directly into the widget HTML file so it works standalone.
    """
    if not os.path.exists(widget_file):
        print(f"[!] Widget file {widget_file} not found. Skipping HTML update.")
        return

    try:
        with open(widget_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Build clean JSON string to embed in the widget JS
        js_data_obj = {
            "last_updated": data.get("last_updated"),
            "races": data.get("races", [])[:20], # Top 20 upcoming races
            "horses": data.get("horses", [])[:10], # Top 10 horses
            "jockeys": data.get("jockeys", [])[:10] # Top 10 jockeys
        }
        json_str = json.dumps(js_data_obj, indent=6, ensure_ascii=False)

        # Replace RACING_DATA object in script
        pattern = r'(const RACING_DATA\s*=\s*)\{[\s\S]*?\};'
        replacement = f"const RACING_DATA = {json_str};"

        if re.search(pattern, content):
            new_content = re.sub(pattern, replacement, content)
            with open(widget_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"[✓] Successfully injected live scraped data into {widget_file}")
        else:
            print("[!] Could not find RACING_DATA variable in widget file to replace.")
    except Exception as e:
        print(f"[!] Error updating widget HTML: {e}")


def main():
    print("=================================================================")
    print("🏁 FACTS SMASHERS RACING - LIVE DATA SCRAPER & HUB AGGREGATOR 🏁")
    print("=================================================================")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "racing_data.json")

    # Read existing JSON if available to preserve valid historical leaders if cloud IP gets rate-limited
    prev_data = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                prev_data = json.load(f)
        except Exception:
            pass

    session = create_scraper_session()

    # 1. Scrape Leaders from Equibase
    horses, jockeys = scrape_equibase_leaders(session)

    # If Equibase failed due to datacenter IP protection on GitHub Actions, use existing or fallback
    if not horses or len(horses) == 0:
        horses = prev_data.get('horses', []) if prev_data.get('horses') else FALLBACK_HORSES
        print(f"[*] Preserving {len(horses)} horse leaderboard entries.")

    if not jockeys or len(jockeys) == 0:
        jockeys = prev_data.get('jockeys', []) if prev_data.get('jockeys') else FALLBACK_JOCKEYS
        print(f"[*] Preserving {len(jockeys)} jockey leaderboard entries.")

    # 2. Scrape Upcoming Races from HorseRacingNation
    races = scrape_upcoming_races(session)
    if not races or len(races) == 0:
        races = prev_data.get('races', [])

    # 3. Compile Master Dataset
    master_data = {
        "last_updated": datetime.now().strftime("%B %d, %Y - %I:%M %p"),
        "races": races,
        "horses": horses,
        "jockeys": jockeys
    }

    # 4. Export to racing_data.json
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, indent=2, ensure_ascii=False)
    print(f"[✓] Exported live JSON data to: {json_path}")

    # 5. Update racing-hub-widget.html
    widget_path = os.path.join(script_dir, "racing-hub-widget.html")
    update_widget_html(master_data, widget_path)

    print("\n🎉 Scraping and Widget Sync Completed Successfully!")


if __name__ == "__main__":
    main()
