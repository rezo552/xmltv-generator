# Flask IMDB Chart API

This is a small Flask webapp with a REST API to download IMDB charts (Top 250, Most Popular Movies).

# XMLTV Generator

A Flask-based REST API to generate an XMLTV EPG (Electronic Program Guide) from MDB lists, enriched with TMDb movie data. Supports multi-channel, multi-language guides, daily caching, and Docker deployment.

## Features
- Fetches movie lists from MDB (mdblist.com)
- Enriches movie data with TMDb (themoviedb.org) for localized titles, descriptions, runtime, ratings and movie covers (posters)
- Channel logos
- Generates XMLTV EPG for all configured MDB lists as channels
- Language selection for title and description (via `lang` query param)
- Daily caching of generated EPG (auto-refreshes after midnight)
- Logs all MDB and TMDb API queries and responses
- Docker and Docker Compose support
- API keys loaded from `.env` file (see `.env.example`)

## Requirements
- Python 3.8+
- MDB API key (https://mdblist.com/api)
- TMDb API key (https://www.themoviedb.org/documentation/api)

## Setup
1. Clone the repository:
   ```sh
   git clone https://github.com/rezo552/xmltv-generator.git
   cd xmltv-generator
   ```
2. Create and activate a virtual environment:
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your API keys:
   ```sh
   cp .env.example .env
   # Edit .env and set MDB_API_KEY and TMDB_API_KEY
   ```

5. Configure your MDB lists in `mdb_lists.cfg`:
   - Each line should be in the format: `username/listname`
   - Lines starting with `#` are ignored as comments
   - Each entry creates a separate channel in the XMLTV output

### Example mdb_lists.cfg
```
# Example list configuration
user1/favorites
user2/top-movies
```

### Channel logos
Each channel gets an `<icon>` in the XMLTV if a logo exists, served by the app under `/logos/`:
- default file: `logos/<channel id>.png` (the channel id is the list name, e.g. `logos/top-movies.png`)
- or an optional third column in `mdb_lists.cfg`: a file name in `logos/` or a full `http(s)://` URL
  ```
  user1/favorites,Favourites,favourites.png
  user2/top-movies,Top Movies,https://example.com/top.png
  ```
- `LOGO_BASE_URL` sets the address used in the logo links, e.g. `http://192.168.1.10:8765` (default: the host the guide was requested from)

`tools/make_logos.py` generates simple logos for all configured channels (a symbol picked from the channel name, or its initials):
```sh
pip install pillow   # also needs the DejaVu fonts, e.g. apt install fonts-dejavu-core
python tools/make_logos.py mdb_lists.cfg logos
```

## Running
### Locally
```sh
python app.py
```
The API will be available at http://localhost:8765/api/mdb/xmltv

### With Docker
Build and run with Docker Compose:
```sh
docker-compose up --build
```

## API Usage
### Get XMLTV EPG
```
GET /api/mdb/xmltv?lang=hu
```
- `lang`: (optional) Language code for title/description (default: `en`)

Returns: XMLTV EPG for all configured MDB lists as channels.

## Environment Variables
Set these in your `.env` file:
- `MDB_API_KEY` — Your MDB API key
- `TMDB_API_KEY` — Your TMDb API key
- `LOGO_BASE_URL` — (optional) public address used in channel logo links
- `TMDB_POSTER_SIZE` — (optional) size of the movie covers added to each programme as `<icon>`, one of TMDb's poster sizes: `w92`, `w154`, `w185`, `w342`, `w500` (default), `w780`, `original`

## Notes
- The EPG is cached in memory and refreshed daily after midnight.
- `.env` and `venv/` are excluded from git.
- All API queries and responses are logged to the server console.

## License
MIT
