# Flask IMDB Chart API

This is a small Flask webapp with a REST API to download IMDB charts (Top 250, Most Popular Movies).

# XMLTV Generator

A Flask-based REST API to generate an XMLTV EPG (Electronic Program Guide) from MDB lists, enriched with TMDb movie data. Supports multi-channel, multi-language guides, daily caching, and Docker deployment.

## Features
- Fetches movie lists from MDB (mdblist.com)
- Enriches movie data with TMDb (themoviedb.org) for localized titles, descriptions, runtime, and ratings
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

## Notes
- The EPG is cached in memory and refreshed daily after midnight.
- `.env` and `venv/` are excluded from git.
- All API queries and responses are logged to the server console.

## License
MIT
