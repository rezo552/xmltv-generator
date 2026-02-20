# Flask IMDB Chart API

This is a small Flask webapp with a REST API to download IMDB charts (Top 250, Most Popular Movies).

## Endpoints

- `/api/imdb/top250` — Returns IMDB Top 250 movies as JSON
- `/api/imdb/popular` — Returns IMDB Most Popular movies as JSON

## Setup

1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Run the app:
   ```sh
   python app.py
   ```

## Example

Fetch Top 250 movies:
```
curl http://127.0.0.1:5000/api/imdb/top250
```
