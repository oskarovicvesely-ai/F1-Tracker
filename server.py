#!/usr/bin/env python3
import base64
import html
import json
import os
import re
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
ICS_URL = 'https://ics.ecal.com/ecal-sub/6955b7c2c71b490002731b8a/Formula%201.ics'
DRIVERS_URL = 'https://www.formula1.com/en/results.html/2026/drivers.html'
CONSTRUCTORS_URL = 'https://www.formula1.com/en/results.html/2026/team.html'


def clean_text(value: str) -> str:
    text = html.unescape(value)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def fetch_text(url: str) -> str:
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req, timeout=25) as response:
        return response.read().decode('utf-8', 'replace')


def parse_formula1_calendar() -> list:
    page = fetch_text('https://www.formula1.com/en/racing/2026.html')
    month_map = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
        'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12,
    }
    date_pattern = re.compile(r'(\d{1,2})\s*-\s*(\d{1,2})\s*([A-Z]{3,4})', re.I)
    race_pattern = re.compile(
        r'href="/en/racing/2026/([^"]+)".*?<span[^>]*>ROUND\s+(\d+)\s*</span>.*?<span[^>]*>(.*?)</span>.*?<span[^>]*>(.*?)</span>',
        re.S,
    )

    races = []
    seen = set()

    for slug, round_text, first_value, second_value in race_pattern.findall(page):
        if slug in seen:
            continue
        seen.add(slug)

        values = [clean_text(first_value), clean_text(second_value)]
        date_text = next((value for value in values if date_pattern.search(value)), None)
        if not date_text:
            continue

        date_match = date_pattern.search(date_text)
        if not date_match:
            continue

        start_day, _, month_text = date_match.groups()
        month = month_map.get(month_text.upper())
        if month is None:
            continue

        location = next(
            (
                value for value in values
                if value
                and 'FORMULA 1' not in value.upper()
                and 'CHEQUERED FLAG' not in value.upper()
                and 'FLAG OF ' not in value.upper()
                and not date_pattern.search(value)
            ),
            None,
        )
        if not location:
            location = slug.replace('-', ' ').title()

        race_name = slug.replace('-', ' ').title()
        if 'next race' in slug.lower() or 'testing' in slug.lower():
            continue

        races.append({
            'round': int(round_text or 1),
            'date': datetime(2026, month, int(start_day)).date().isoformat(),
            'name': race_name,
            'location': location,
            'time': '12:00:00Z',
            'slug': slug,
        })

    if not races:
        return parse_ics_races()

    races.sort(key=lambda item: item['date'])
    for index, race in enumerate(races, start=1):
        race['round'] = index
    return races


def parse_ics_races() -> list:
    text = fetch_text(ICS_URL)
    events = []
    current = {}

    for line in text.splitlines():
        if line == 'BEGIN:VEVENT':
            current = {}
        elif line.startswith('DTSTART'):
            current['date'] = line.split(':', 1)[1]
        elif line.startswith('SUMMARY:'):
            current['summary'] = line.split(':', 1)[1]
        elif line.startswith('LOCATION:'):
            current['location'] = line.split(':', 1)[1]
        elif line == 'END:VEVENT':
            if current:
                events.append(current)

    races = []
    for event in events:
        summary = event.get('summary', '')
        if 'GRAND PRIX' not in summary or ' - Race' not in summary:
            continue

        date_value = event.get('date', '')
        try:
            if len(date_value) == 8:
                race_date = datetime.strptime(date_value, '%Y%m%d').date()
            else:
                race_date = datetime.strptime(date_value, '%Y%m%dT%H%M%SZ').date()
        except ValueError:
            continue

        if race_date.year != 2026:
            continue

        clean_summary = summary
        clean_summary = clean_summary.replace('🏁 ', '').replace('🏎 ', '').replace('⏱️ ', '')
        clean_summary = clean_summary.replace('FORMULA 1 ', '')
        clean_summary = re.sub(r'\s*-\s*Race.*$', '', clean_summary)
        clean_summary = re.sub(r'\s+\d{4}$', '', clean_summary)
        clean_summary = clean_summary.strip()

        races.append({
            'round': len(races) + 1,
            'date': race_date.isoformat(),
            'name': clean_summary,
            'location': event.get('location', '').strip(),
            'time': '12:00:00Z'
        })

    races.sort(key=lambda item: item['date'])
    for index, race in enumerate(races, start=1):
        race['round'] = index
    return races


def parse_standings(html_text: str, type_name: str) -> list:
    rows = re.findall(r'<tr[^>]*class="[^"]*Table-module_body-row[^"]*"[^>]*>(.*?)</tr>', html_text, re.S)
    result = []

    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)
        if type_name == 'driver' and len(cells) < 5:
            continue
        if type_name == 'constructor' and len(cells) < 3:
            continue

        values = [clean_text(cell) for cell in cells]
        if not values or not values[0].isdigit():
            continue

        if type_name == 'driver':
            name_parts = values[1].split()
            if len(name_parts) > 1 and len(name_parts[-1]) <= 3 and name_parts[-1].isalpha():
                name_parts = name_parts[:-1]
            result.append({
                'position': int(values[0]),
                'givenName': name_parts[0] if name_parts else '',
                'familyName': ' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
                'team': values[3],
                'points': int(values[4])
            })
        else:
            result.append({
                'position': int(values[0]),
                'name': values[1],
                'points': int(values[2])
            })

    if type_name == 'driver':
        return result[:22]
    return result[:11]


def build_payload() -> dict:
    races = parse_formula1_calendar()
    drivers_html = fetch_text(DRIVERS_URL)
    constructors_html = fetch_text(CONSTRUCTORS_URL)

    driverStandings = parse_standings(drivers_html, 'driver')
    constructorStandings = parse_standings(constructors_html, 'constructor')

    now = datetime.utcnow()
    next_race = next((race for race in races if datetime.strptime(race['date'], '%Y-%m-%d').date() >= now.date()), races[-1])
    current_round = next(
        (race['round'] for race in races if datetime.strptime(race['date'], '%Y-%m-%d').date() <= now.date()),
        1,
    )

    if not driverStandings:
        raise RuntimeError('No driver standings data received')

    return {
        'season': 2026,
        'currentRound': current_round,
        'nextRace': next_race['name'],
        'leader': f"{driverStandings[0]['givenName']} {driverStandings[0]['familyName']}".strip(),
        'races': races,
        'driverStandings': driverStandings,
        'constructorStandings': constructorStandings,
        'calendarSubscribeUrl': ICS_URL
    }


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/f1-data':
            payload = build_payload()
            body = json.dumps(payload).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path in ('/', ''):
            self.path = '/index.html'
        else:
            self.path = parsed.path

        try:
            return super().do_GET()
        except FileNotFoundError:
            self.send_error(404, 'File not found')

    def log_message(self, format, *args):
        return


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    httpd = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    print(f'Serving F1 Tracker on http://localhost:{port}')
    httpd.serve_forever()

