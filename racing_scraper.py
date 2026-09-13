"""
=============================================================================
FACTS SMASHERS RACING - BLOODHORSE LIVE SCRAPER & AGGREGATOR
=============================================================================
Sources:
1. Stakes Entries (Upcoming Races):
   - https://www.bloodhorse.com/horse-racing/race/stakes-entries
2. Race Results (Recent Results):
   - https://www.bloodhorse.com/horse-racing/race/race-results
3. Top Leading Horses (Dynamic Year):
   - https://www.bloodhorse.com/horse-racing/thoroughbred-racing/leaders/horses/{year}
4. Top Leading Jockeys (Dynamic Year):
   - https://www.bloodhorse.com/horse-racing/thoroughbred-racing/leaders/jockeys/{year}

Features:
- Dynamically auto-updates year (2026 -> 2027 -> 2028...) without manual intervention
- Outputs clean racing_data.json and syncs racing-hub-widget.html
=============================================================================
"""

import os
import sys
import json
import re
import subprocess
from datetime import datetime

# Configure UTF-8 encoding for console outputs safely across all operating systems
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("[!] Missing dependencies. Please run: pip install requests beautifulsoup4")
    sys.exit(1)


# Global track classification dictionary
TRACK_COUNTRY_MAP = {
    # Canada
    "woodbine": {"country": "Canada", "flag": "🇨🇦"},
    "hastings": {"country": "Canada", "flag": "🇨🇦"},
    "fort erie": {"country": "Canada", "flag": "🇨🇦"},
    "century mile": {"country": "Canada", "flag": "🇨🇦"},
    "century downs": {"country": "Canada", "flag": "🇨🇦"},
    "assiniboia": {"country": "Canada", "flag": "🇨🇦"},

    # Puerto Rico
    "camarero": {"country": "Puerto Rico", "flag": "🇵🇷"},

    # UK & Ireland
    "ascot": {"country": "UK", "flag": "🇬🇧"},
    "newmarket": {"country": "UK", "flag": "🇬🇧"},
    "york": {"country": "UK", "flag": "🇬🇧"},
    "epsom": {"country": "UK", "flag": "🇬🇧"},
    "goodwood": {"country": "UK", "flag": "🇬🇧"},
    "curragh": {"country": "Ireland", "flag": "🇮🇪"},
    "leopardstown": {"country": "Ireland", "flag": "🇮🇪"},

    # France
    "longchamp": {"country": "France", "flag": "🇫🇷"},
    "parislongchamp": {"country": "France", "flag": "🇫🇷"},
    "chantilly": {"country": "France", "flag": "🇫🇷"},
    "deauville": {"country": "France", "flag": "🇫🇷"},

    # UAE & Middle East
    "meydan": {"country": "UAE", "flag": "🇦🇪"},
    "king abdulaziz": {"country": "Saudi Arabia", "flag": "🇸🇦"},

    # Australia & Asia
    "flemington": {"country": "Australia", "flag": "🇦🇺"},
    "randwick": {"country": "Australia", "flag": "🇦🇺"},
    "sha tin": {"country": "Hong Kong", "flag": "🇭🇰"},
    "happy valley": {"country": "Hong Kong", "flag": "🇭🇰"},
    "tokyo": {"country": "Japan", "flag": "🇯🇵"},
    "hanshin": {"country": "Japan", "flag": "🇯🇵"},
    "nakayama": {"country": "Japan", "flag": "🇯🇵"},
    "kyoto": {"country": "Japan", "flag": "🇯🇵"}
}


def fetch_url(url):
    """
    Fetches HTML content with curl for high-reliability TLS fingerprinting,
    falling back to requests.
    """
    # 1. Try curl (Bypasses Incapsula challenge reliably in cloud environments)
    cmd = [
        'curl', '-s', '-L',
        '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        '-H', 'Accept-Language: en-US,en;q=0.9',
        url
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=25, encoding='utf-8', errors='ignore')
        if res.stdout and len(res.stdout) > 2000 and ("table" in res.stdout.lower() or "article" in res.stdout.lower()):
            return res.stdout
    except Exception:
        pass

    # 2. Fallback to requests
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print(f"[!] Error fetching {url}: {e}")

    return ""


def clean_text(text):
    """Safely cleans up emojis, excess whitespace, and non-ascii characters."""
    if not text:
        return ""
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s\-\.\'\(\)\,\/\$\:\#\%\+]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def scrape_bloodhorse_horses(year):
    """
    Scrapes leading horses from BloodHorse for the specified year.
    URL: https://www.bloodhorse.com/horse-racing/thoroughbred-racing/leaders/horses/{year}
    """
    url = f"https://www.bloodhorse.com/horse-racing/thoroughbred-racing/leaders/horses/{year}"
    print(f"[*] Fetching Leading Horses from BloodHorse ({year})...")
    html = fetch_url(url)
    horses = []
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')[1:16] # Top 15 horses
            for row in rows:
                cols = [clean_text(td.get_text(strip=True)) for td in row.find_all('td')]
                if len(cols) >= 7:
                    rank = int(cols[0]) if cols[0].isdigit() else len(horses) + 1
                    name = cols[1]
                    starts = cols[2]
                    wins = cols[3]
                    places = cols[4] if len(cols) > 4 else "0"
                    shows = cols[5] if len(cols) > 5 else "0"
                    earnings = cols[6] if len(cols) > 6 else "$0"
                    
                    horses.append({
                        "rank": rank,
                        "name": name,
                        "sub": f"Starts: {starts} • Wins: {wins} • Places: {places} • Shows: {shows}",
                        "cash": earnings,
                        "flag": "🏇"
                    })
            print(f"[OK] Successfully retrieved {len(horses)} top horses from BloodHorse ({year}).")

    # Fallback to prior year if current year has no data yet (e.g. early January)
    if not horses and year == datetime.now().year:
        print(f"[*] Retrying with prior year ({year - 1})...")
        return scrape_bloodhorse_horses(year - 1)

    return horses


def scrape_bloodhorse_jockeys(year):
    """
    Scrapes leading jockeys from BloodHorse for the specified year.
    URL: https://www.bloodhorse.com/horse-racing/thoroughbred-racing/leaders/jockeys/{year}
    """
    url = f"https://www.bloodhorse.com/horse-racing/thoroughbred-racing/leaders/jockeys/{year}"
    print(f"[*] Fetching Leading Jockeys from BloodHorse ({year})...")
    html = fetch_url(url)
    jockeys = []
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')[1:16] # Top 15 jockeys
            for row in rows:
                cols = [clean_text(td.get_text(strip=True)) for td in row.find_all('td')]
                if len(cols) >= 7:
                    rank = int(cols[0]) if cols[0].isdigit() else len(jockeys) + 1
                    name = cols[1]
                    starts = cols[2]
                    wins = cols[3]
                    earnings = cols[6] if len(cols) > 6 else "$0"
                    win_pct = cols[7] if len(cols) > 7 else ""
                    
                    sub_text = f"Starts: {starts} • Wins: {wins}"
                    if win_pct:
                        sub_text += f" ({win_pct})"
                        
                    jockeys.append({
                        "rank": rank,
                        "name": name,
                        "sub": sub_text,
                        "cash": earnings,
                        "flag": "👤"
                    })
            print(f"[OK] Successfully retrieved {len(jockeys)} top jockeys from BloodHorse ({year}).")

    # Fallback to prior year if current year has no data yet
    if not jockeys and year == datetime.now().year:
        print(f"[*] Retrying with prior year ({year - 1})...")
        return scrape_bloodhorse_jockeys(year - 1)

    return jockeys


def scrape_bloodhorse_stakes_entries():
    """
    Scrapes upcoming stakes races from BloodHorse.
    URL: https://www.bloodhorse.com/horse-racing/race/stakes-entries
    """
    url = "https://www.bloodhorse.com/horse-racing/race/stakes-entries"
    print("[*] Fetching Stakes Entries (Upcoming Races) from BloodHorse...")
    html = fetch_url(url)
    races = []
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')[1:] # Skip header
            for row in rows:
                cols = [clean_text(td.get_text(strip=True)) for td in row.find_all('td')]
                if len(cols) >= 7:
                    date_val = cols[0]
                    race_name = cols[1]
                    track_val = cols[2]
                    grade_val = cols[3]
                    dist_val = cols[4]
                    sf_val = cols[5]
                    purse_val = cols[6]

                    # Determine Grade
                    grade_label = f"Grade {grade_val}" if grade_val in ['1', '2', '3'] else "Stakes"
                    if "G1" in race_name or "(G1)" in race_name or "-G1" in race_name:
                        grade_label = "Grade 1"
                    elif "G2" in race_name or "(G2)" in race_name or "-G2" in race_name:
                        grade_label = "Grade 2"
                    elif "G3" in race_name or "(G3)" in race_name or "-G3" in race_name:
                        grade_label = "Grade 3"

                    # Determine Country & Flag
                    track_lower = track_val.lower()
                    country = "USA"
                    flag = "🇺🇸"
                    is_usa = True

                    for key, meta in TRACK_COUNTRY_MAP.items():
                        if key in track_lower:
                            country = meta["country"]
                            flag = meta["flag"]
                            is_usa = (country == "USA")
                            break

                    races.append({
                        "name": race_name,
                        "raw_name": race_name,
                        "track": track_val,
                        "grade": grade_label,
                        "dist": f"{dist_val} ({sf_val})",
                        "purse": f"Purse: {purse_val}",
                        "date": date_val,
                        "country": country,
                        "flag": flag,
                        "isUsa": is_usa
                    })
            print(f"[OK] Successfully retrieved {len(races)} upcoming stakes races from BloodHorse.")

    return races


def scrape_bloodhorse_race_results():
    """
    Scrapes recent race results from BloodHorse.
    URL: https://www.bloodhorse.com/horse-racing/race/race-results
    """
    url = "https://www.bloodhorse.com/horse-racing/race/race-results"
    print("[*] Fetching Recent Race Results from BloodHorse...")
    html = fetch_url(url)
    results = []
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        articles = soup.find_all('article')
        for art in articles[:15]:
            title_el = art.find(['h2', 'h3', 'h4', 'a'])
            title = clean_text(title_el.get_text(strip=True)) if title_el else ""
            full_text = clean_text(art.get_text(" | ", strip=True))
            if title:
                results.append({
                    "title": title,
                    "details": full_text
                })
        print(f"[OK] Successfully retrieved {len(results)} recent race results from BloodHorse.")

    return results


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

        js_data_obj = {
            "last_updated": data.get("last_updated"),
            "year": data.get("year"),
            "races": data.get("races", [])[:20],
            "horses": data.get("horses", [])[:10],
            "jockeys": data.get("jockeys", [])[:10],
            "recent_results": data.get("recent_results", [])[:10]
        }
        json_str = json.dumps(js_data_obj, indent=6, ensure_ascii=False)

        # Replace RACING_DATA object in script
        pattern = r'(const RACING_DATA\s*=\s*)\{[\s\S]*?\};'
        replacement = f"const RACING_DATA = {json_str};"

        if re.search(pattern, content):
            new_content = re.sub(pattern, replacement, content)
            with open(widget_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"[OK] Successfully injected live BloodHorse data into {widget_file}")
    except Exception as e:
        print(f"[!] Error updating widget HTML: {e}")


def main():
    print("=================================================================")
    print("FACTS SMASHERS RACING - BLOODHORSE LIVE SCRAPER & AGGREGATOR")
    print("=================================================================")

    # 1. Dynamically calculate the active year (e.g., 2026, 2027, etc.)
    current_year = datetime.now().year
    print(f"[*] Active Scraping Year: {current_year}")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "racing_data.json")

    # 2. Scrape Horses & Jockeys from BloodHorse for active year
    horses = scrape_bloodhorse_horses(current_year)
    jockeys = scrape_bloodhorse_jockeys(current_year)

    # 3. Scrape Stakes Entries from BloodHorse
    races = scrape_bloodhorse_stakes_entries()

    # 4. Scrape Recent Race Results from BloodHorse
    recent_results = scrape_bloodhorse_race_results()

    # 5. Compile Master Dataset
    master_data = {
        "last_updated": datetime.now().strftime("%B %d, %Y - %I:%M %p"),
        "year": current_year,
        "races": races,
        "horses": horses,
        "jockeys": jockeys,
        "recent_results": recent_results
    }

    # 6. Export to racing_data.json
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, indent=2, ensure_ascii=False)
    print(f"[OK] Exported live JSON data to: {json_path}")

    # 7. Update racing-hub-widget.html
    widget_path = os.path.join(script_dir, "racing-hub-widget.html")
    update_widget_html(master_data, widget_path)

    print("\nBloodHorse Scraping and Widget Sync Completed Successfully!")


if __name__ == "__main__":
    main()
