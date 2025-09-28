# OpenSky BBox Viewer (Flask)

A tiny Flask app that queries the OpenSky Network `/states/all` endpoint with a bounding box,
then renders the results as:
- Counts by `origin_country`
- A list/table filtered by a chosen country

## Local run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PORT=8080
python app.py
# open http://localhost:8080
```

Optional env vars:
```
LAMIN=35.5  LAMAX=42.5  LOMIN=25.5  LOMAX=45.5  COUNTRY=Turkey
OPEN_SKY_API=https://opensky-network.org/api/states/all
```

## Deploy to Render

- Push this folder to a Git repo.
- In Render, create a new **Web Service** from that repo.
- It will auto-detect `render.yaml` (or set build/start commands manually).

## Usage

Change the bbox and country in the form on `/`, or via query:
```
/?lamin=35.5&lamax=42.5&lomin=26&lomax=45&country=Israel
```
