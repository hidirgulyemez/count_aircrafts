from flask import Flask, request, render_template, jsonify
import os
import requests
from collections import Counter
from urllib.parse import urlencode

app = Flask(__name__)

# --- Defaults (can be overridden by query params or env) ---
DEFAULT_BBOX = {
    "lamin": os.getenv("LAMIN", "35.5"),
    "lamax": os.getenv("LAMAX", "42.5"),
    "lomin": os.getenv("LOMIN", "25.5"),
    "lomax": os.getenv("LOMAX", "45.5"),
}
DEFAULT_COUNTRY = os.getenv("COUNTRY", "Turkey")
OPEN_SKY_API = os.getenv("OPEN_SKY_API", "https://opensky-network.org/api/states/all")

def fetch_states(params):
    try:
        r = requests.get(OPEN_SKY_API, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("states", []), None
    except Exception as e:
        return [], str(e)

def summarize_by_country(states):
    counts = Counter([s[2] for s in states if len(s) > 2])
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)

@app.route("/")
def index():
    # Read query params or fall back to defaults
    lamin = request.args.get("lamin", DEFAULT_BBOX["lamin"])
    lamax = request.args.get("lamax", DEFAULT_BBOX["lamax"])
    lomin = request.args.get("lomin", DEFAULT_BBOX["lomin"])
    lomax = request.args.get("lomax", DEFAULT_BBOX["lomax"])
    country = request.args.get("country", DEFAULT_COUNTRY)

    params = {"lamin": lamin, "lamax": lamax, "lomin": lomin, "lomax": lomax}
    states, err = fetch_states(params)
    bbox_url = f"{OPEN_SKY_API}?{urlencode(params)}"

    # Filter by registered country (origin_country at index 2)
    filtered = [s for s in states if len(s) > 2 and s[2] == country]

    # Build a neat dict list for template
    keys = ["icao24","callsign","origin_country","time_position","last_contact",
            "longitude","latitude","baro_altitude","on_ground","velocity",
            "true_track","vertical_rate","sensors","geo_altitude","squawk",
            "spi","position_source"]
    rows = []
    for s in filtered:
        row = {}
        for i, k in enumerate(keys):
            row[k] = s[i] if i < len(s) else None
        rows.append(row)

    country_counts = summarize_by_country(states)

    return render_template(
        "index.html",
        rows=rows,
        country=country,
        country_counts=country_counts,
        lamin=lamin, lamax=lamax, lomin=lomin, lomax=lomax,
        bbox_url=bbox_url,
        error=err,
    )

@app.route("/json")
def json_view():
    # Useful for seeing the raw filtered JSON
    lamin = request.args.get("lamin", DEFAULT_BBOX["lamin"])
    lamax = request.args.get("lamax", DEFAULT_BBOX["lamax"])
    lomin = request.args.get("lomin", DEFAULT_BBOX["lomin"])
    lomax = request.args.get("lomax", DEFAULT_BBOX["lomax"])
    country = request.args.get("country", DEFAULT_COUNTRY)

    params = {"lamin": lamin, "lamax": lamax, "lomin": lomin, "lomax": lomax}
    states, err = fetch_states(params)
    filtered = [s for s in states if len(s) > 2 and s[2] == country]
    return jsonify({
        "error": err,
        "query": params,
        "country": country,
        "count": len(filtered),
        "states": filtered
    })

if __name__ == "__main__":
    # Local dev
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=True)
