
import html
from threading import Lock
import os
from dotenv import load_dotenv

load_dotenv()
xmltv_cache = {'date': None, 'lang': None, 'xmltv': None}
xmltv_cache_lock = Lock()

from flask import Flask, jsonify, request, Response
import requests
import random
from datetime import datetime, timedelta


app = Flask(__name__)

# MDB and TMDb API keys from environment variables
MDB_API_KEY = os.environ.get('MDB_API_KEY')
TMDB_API_KEY = os.environ.get('TMDB_API_KEY')


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
                if username_list and display_name:
                    lists.append((username_list, display_name))
    except Exception:
        pass
    return lists

def fetch_mdb_list_movies(username, listname):
    url = f'https://api.mdblist.com/lists/{username}/{listname}/items'
    params = {'apikey': MDB_API_KEY}
    print(f"MDB List API Query: {url} params={params}", flush=True)
    response = requests.get(url, params=params)
    print(f"MDB List API Response: {response.status_code} {response.text[:500]}", flush=True)
    if response.status_code == 200:
        return response.json().get('movies', [])
    return []

def fetch_tmdb_movie_info(tmdb_id, lang='hu'):
    url = f'https://api.themoviedb.org/3/movie/{tmdb_id}'
    params = {'api_key': TMDB_API_KEY, 'language': lang}
    print(f"TMDb API Query: {url} params={params}", flush=True)
    response = requests.get(url, params=params)
    print(f"TMDb API Response: {response.status_code} {response.text[:500]}", flush=True)
    if response.status_code == 200:
        return response.json()
    return {}


@app.route('/api/mdb/xmltv', methods=['GET'])
def get_mdb_xmltv():
    lang = request.args.get('lang', 'en')
    today = datetime.now().date()
    with xmltv_cache_lock:
        if xmltv_cache['date'] == today and xmltv_cache['lang'] == lang and xmltv_cache['xmltv']:
            print("Serving XMLTV from cache", flush=True)
            return Response(xmltv_cache['xmltv'], mimetype='application/xml')
    lists = read_mdb_lists_config()
    start_time = datetime.now().replace(second=0, microsecond=0)
    xmltv = ['<?xml version="1.0" encoding="UTF-8"?>', '<tv generator-info-name="torrent TV">']
    channel_elements = []
    programme_elements = []
    for username_list, display_name in lists:
        if '/' not in username_list:
            continue
        username, listname = username_list.split('/', 1)
        mdb_movies = fetch_mdb_list_movies(username, listname)
        channel_id = listname
        channel_elements.append(f'<channel id="{channel_id}"><display-name>{html.escape(display_name)}</display-name></channel>')
        current_time = start_time
        random_movies = mdb_movies[:]
        random.shuffle(random_movies)
        for movie in random_movies:
            tmdb_id = movie.get('ids', {}).get('tmdb')
            print(f"Fetching TMDb ID: {tmdb_id}", flush=True)
            imdb_id = movie.get('imdb') or movie.get('imdb_id')
            # Always fetch info from TMDb using tmdb_id and lang
            tmdb_info = fetch_tmdb_movie_info(tmdb_id, lang) if tmdb_id else {}
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
    return Response(xmltv_str, mimetype='application/xml')

if __name__ == '__main__':
    app.run(debug=True, port=8765, host='0.0.0.0')
