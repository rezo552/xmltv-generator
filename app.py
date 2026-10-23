
import html
from threading import Lock
import os
import json
from dotenv import load_dotenv

load_dotenv()
xmltv_cache = {'date': None, 'lang': None, 'xmltv': None}
xmltv_cache_lock = Lock()

from flask import Flask, jsonify, request, Response, send_from_directory
import requests
import random
import urllib.parse
from datetime import datetime, timedelta


app = Flask(__name__)

# MDB and TMDb API keys from environment variables
MDB_API_KEY = os.environ.get('MDB_API_KEY')
TMDB_API_KEY = os.environ.get('TMDB_API_KEY')

# Movie covers: TMDb poster as the programme <icon>
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p'
TMDB_POSTER_SIZE = os.environ.get('TMDB_POSTER_SIZE', 'w500')  # w92 w154 w185 w342 w500 w780 original

# Channel logos: logos/<channel id>.png (or the file/URL in the 3rd column of mdb_lists.cfg)
LOGO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logos')
# Public base URL for logo links, e.g. http://192.168.1.10:8765 (default: the request host)
LOGO_BASE_URL = os.environ.get('LOGO_BASE_URL', '').rstrip('/')
# The cached XMLTV contains this placeholder, replaced per request, so every client gets
# the same (randomly shuffled) schedule no matter which host name it used
LOGO_BASE_PLACEHOLDER = '__LOGO_BASE_URL__'


def read_mdb_lists_config():
    import csv
    lists = []
    try:
        with open('mdb_lists.cfg', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].startswith('#'):
                    continue
                if len(row) < 2:
                    continue
                username_list = row[0].strip()
                display_name = row[1].strip()
                logo = row[2].strip() if len(row) > 2 else ''
                if username_list and display_name:
                    lists.append((username_list, display_name, logo))
    except Exception:
        pass
    return lists

def channel_logo_url(channel_id, logo):
    if logo.startswith(('http://', 'https://')):
        return logo
    filename = logo or f'{channel_id}.png'
    if not os.path.isfile(os.path.join(LOGO_DIR, filename)):
        return None
    return f'{LOGO_BASE_PLACEHOLDER}/logos/{urllib.parse.quote(filename)}'

def xmltv_response(xmltv_str):
    logo_base = LOGO_BASE_URL or request.host_url.rstrip('/')
    return Response(xmltv_str.replace(LOGO_BASE_PLACEHOLDER, html.escape(logo_base)), mimetype='application/xml')


@app.route('/logos/<path:filename>', methods=['GET'])
def get_logo(filename):
    return send_from_directory(LOGO_DIR, filename)

def fetch_mdb_list_movies(username, listname):
    url = f'https://api.mdblist.com/lists/{username}/{listname}/items'
    params = {'apikey': MDB_API_KEY}
    print(f"MDB List API Query: {url} params={params}", flush=True)
    response = requests.get(url, params=params)
    print(f"MDB List API Response: {response.status_code} {response.text[:500]}", flush=True)
    if response.status_code == 200:
        return response.json().get('movies', [])
    return []

def fetch_tmdb_movie_info(tmdb_id, lang='hu', imdb_id=None):
    # Use IMDB ID for cache key if available
    cache_key = imdb_id or tmdb_id
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f'{lang}_{cache_key}.json')
    # Try to load from cache
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    # Fetch from TMDb
    url = f'https://api.themoviedb.org/3/movie/{tmdb_id}'
    params = {'api_key': TMDB_API_KEY, 'language': lang}
    print(f"TMDb API Query: {url} params={params}", flush=True)
    response = requests.get(url, params=params)
    print(f"TMDb API Response: {response.status_code} {response.text[:500]}", flush=True)
    if response.status_code == 200:
        data = response.json()
        # Save to cache
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass
        return data
    return {}


@app.route('/api/mdb/xmltv', methods=['GET'])
def get_mdb_xmltv():
    lang = request.args.get('lang', 'en')
    today = datetime.now().date()
    with xmltv_cache_lock:
        if xmltv_cache['date'] == today and xmltv_cache['lang'] == lang and xmltv_cache['xmltv']:
            print("Serving XMLTV from cache", flush=True)
            return xmltv_response(xmltv_cache['xmltv'])
    lists = read_mdb_lists_config()
    start_time = datetime.now().replace(second=0, microsecond=0)
    xmltv = ['<?xml version="1.0" encoding="UTF-8"?>', '<tv generator-info-name="torrent TV">']
    channel_elements = []
    programme_elements = []
    for username_list, display_name, logo in lists:
        if '/' not in username_list:
            continue
        username, listname = username_list.split('/', 1)
        mdb_movies = fetch_mdb_list_movies(username, listname)
        channel_id = listname
        logo_url = channel_logo_url(channel_id, logo)
        icon = f'<icon src="{html.escape(logo_url)}"/>' if logo_url else ''
        channel_elements.append(f'<channel id="{channel_id}"><display-name>{html.escape(display_name)}</display-name>{icon}</channel>')
        current_time = start_time
        random_movies = mdb_movies[:]
        random.shuffle(random_movies)
        for movie in random_movies:
            tmdb_id = movie.get('ids', {}).get('tmdb')
            print(f"Fetching TMDb ID: {tmdb_id}", flush=True)
            imdb_id = movie.get('imdb') or movie.get('imdb_id')
            # Fetch info from cache or TMDb using tmdb_id, lang, and imdb_id
            tmdb_info = fetch_tmdb_movie_info(tmdb_id, lang, imdb_id) if tmdb_id else {}
            print(f"TMDb Info: {tmdb_info}", flush=True)
            runtime = tmdb_info.get('runtime') or movie.get('runtime') or 120
            local_title = tmdb_info.get('title') or tmdb_info.get('original_title') or movie.get('title', '')
            overview = tmdb_info.get('overview', '')
            local_title = html.escape(local_title)
            overview = html.escape(overview)
            year = tmdb_info.get('release_date', '')[:4] if tmdb_info.get('release_date') else movie.get('release_year', '')
            rating = tmdb_info.get('vote_average', '')
            prog_start = current_time
            prog_end = prog_start + timedelta(minutes=runtime)
            desc = f"{overview} IMDB: {html.escape(str(imdb_id))}, Year: {year}, Rating: {rating}, Runtime: {runtime} min"
            programme_elements.append(f'<programme start="{prog_start.strftime("%Y%m%d%H%M%S")} +0100" stop="{prog_end.strftime("%Y%m%d%H%M%S")} +0100" channel="{channel_id}">')
            programme_elements.append(f'  <title lang="{lang}">{local_title}</title>')
            programme_elements.append(f'  <desc lang="{lang}">{desc}</desc>')
            poster_path = tmdb_info.get('poster_path')
            if poster_path:
                programme_elements.append(f'  <icon src="{TMDB_IMAGE_BASE_URL}/{TMDB_POSTER_SIZE}{html.escape(poster_path)}"/>')
            programme_elements.append('</programme>')
            current_time = prog_end
            if prog_end.date() != start_time.date():
                break
    xmltv.extend(channel_elements)
    xmltv.extend(programme_elements)
    xmltv.append('</tv>')
    xmltv_str = '\n'.join(xmltv)
    with xmltv_cache_lock:
        xmltv_cache['date'] = today
        xmltv_cache['lang'] = lang
        xmltv_cache['xmltv'] = xmltv_str
    return xmltv_response(xmltv_str)

if __name__ == '__main__':
    app.run(debug=True, port=8765, host='0.0.0.0')
