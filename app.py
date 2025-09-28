
from flask import Flask, request, render_template_string, jsonify, make_response
import requests
from collections import Counter
from urllib.parse import urlencode
import os

app = Flask(__name__)

# ---- Defaults ----
DEFAULT_BBOX = {
    "lamin": os.getenv("LAMIN", "35.5"),
    "lamax": os.getenv("LAMAX", "42.5"),
    "lomin": os.getenv("LOMIN", "25.5"),
    "lomax": os.getenv("LOMAX", "45.5"),
}
DEFAULT_COUNTRY = os.getenv("COUNTRY", "Turkey")
OPEN_SKY_API = os.getenv("OPEN_SKY_API", "https://opensky-network.org/api/states/all")

HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenSky Results</title>
<style>
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }
  header { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
  .form { display: grid; grid-template-columns: repeat(6, minmax(120px, 1fr)); gap: 8px; margin-top: 12px; }
  input, button { padding: 8px; font-size: 14px; }
  table { border-collapse: collapse; width: 100%; margin-top: 16px; }
  th, td { border: 1px solid #e5e7eb; padding: 8px 10px; font-size: 13px; }
  th { background: #f3f4f6; text-align: left; position: sticky; top: 0; }
  .counts { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px,1fr)); gap: 6px; margin: 16px 0; }
  .pill { background:#eef2ff; padding:6px 8px; border-radius: 999px; font-size: 12px; display:inline-block; }
  .muted { color: #6b7280; font-size: 12px; }
  .error { background:#fee2e2; color:#7f1d1d; padding:10px; border-radius: 8px; }
  .bar { height: 6px; background: #6366f1; border-radius: 4px; }
</style>
</head>
<body>
  <header>
    <h1>OpenSky Results</h1>
    <a href="{{ bbox_url }}" class="muted">API request ↗</a>
  </header>

  {% if error %}
  <div class="error">Error fetching data: {{ error }}</div>
  {% endif %}

  <form class="form" action="/" method="get">
    <label>lamin<br><input name="lamin" value="{{ lamin }}" /></label>
    <label>lamax<br><input name="lamax" value="{{ lamax }}" /></label>
    <label>lomin<br><input name="lomin" value="{{ lomin }}" /></label>
    <label>lomax<br><input name="lomax" value="{{ lomax }}" /></label>
    <label>country<br><input name="country" value="{{ country }}" /></label>
    <div style="display:flex;align-items:end;"><button type="submit">Update</button></div>
  </form>

  <h3 style="margin-top:20px;">Counts by origin_country</h3>
  <div class="counts">
    {% set maxc = (country_counts[0][1] if country_counts else 1) %}
    {% for c, n in country_counts %}
      <div>
        <span class="pill">{{ c or "Unknown" }}</span>
        <div class="muted">{{ n }} flights</div>
        <div class="bar" style="width: {{ (n/maxc)*100 }}%"></div>
      </div>
    {% endfor %}
  </div>

  <h3>Filtered list ({{ country }}) — {{ rows|length }} flights</h3>
  <table>
    <thead>
      <tr>
        <th>icao24</th><th>callsign</th><th>origin_country</th>
        <th>longitude</th><th>latitude</th><th>geo_altitude</th>
        <th>velocity</th><th>true_track</th><th>on_ground</th>
        <th>last_contact</th>
      </tr>
    </thead>
    <tbody>
      {% for r in rows %}
        <tr>
          <td>{{ r["icao24"] }}</td>
          <td>{{ r["callsign"] }}</td>
          <td>{{ r["origin_country"] }}</td>
          <td>{{ r["longitude"] }}</td>
          <td>{{ r["latitude"] }}</td>
          <td>{{ r["geo_altitude"] }}</td>
          <td>{{ r["velocity"] }}</td>
          <td>{{ r["true_track"] }}</td>
          <td>{{ r["on_ground"] }}</td>
          <td>{{ r["last_contact"] }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>

  <p class="muted">Raw JSON: <a href="/json?lamin={{ lamin }}&lamax={{ lamax }}&lomin={{ lomin }}&lomax={{ lomax }}&country={{ country }}">/json</a></p>
</body>
</html>
"""

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

# HEAD health-check handler (Render sends HEAD to /)
@app.route("/", methods=["HEAD"])
def head_ok():
    return ("", 200)

@app.route("/", methods=["GET"])
def index():
    lamin = request.args.get("lamin", DEFAULT_BBOX["lamin"])
    lamax = request.args.get("lamax", DEFAULT_BBOX["lamax"])
    lomin = request.args.get("lomin", DEFAULT_BBOX["lomin"])
    lomax = request.args.get("lomax", DEFAULT_BBOX["lomax"])
    country = request.args.get("country", DEFAULT_COUNTRY)

    params = {"lamin": lamin, "lamax": lamax, "lomin": lomin, "lomax": lomax}
    states, err = fetch_states(params)
    bbox_url = f"{OPEN_SKY_API}?{urlencode(params)}"

    # Filter by origin_country
    keys = ["icao24","callsign","origin_country","time_position","last_contact",
            "longitude","latitude","baro_altitude","on_ground","velocity",
            "true_track","vertical_rate","sensors","geo_altitude","squawk",
            "spi","position_source"]
    filtered = []
    for s in states:
        if len(s) > 2 and s[2] == country:
            row = {k: (s[i] if i < len(s) else None) for i, k in enumerate(keys)}
            filtered.append(row)

    country_counts = summarize_by_country(states)

    return render_template_string(
        HTML,
        rows=filtered,
        country=country,
        country_counts=country_counts,
        lamin=lamin, lamax=lamax, lomin=lomin, lomax=lomax,
        bbox_url=bbox_url,
        error=err,
    )

@app.route("/json")
def json_view():
    lamin = request.args.get("lamin", DEFAULT_BBOX["lamin"])
    lamax = request.args.get("lamax", DEFAULT_BBOX["lamax"])
    lomin = request.args.get("lomin", DEFAULT_BBOX["lomin"])
    lomax = request.args.get("lomax", DEFAULT_BBOX["lomax"])
    country = request.args.get("country", DEFAULT_COUNTRY)

    params = {"lamin": lamin, "lamax": lamax, "lomin": lomin, "lomax": lomax}
    states, err = fetch_states(params)
    keys = ["icao24","callsign","origin_country","time_position","last_contact",
            "longitude","latitude","baro_altitude","on_ground","velocity",
            "true_track","vertical_rate","sensors","geo_altitude","squawk",
            "spi","position_source"]
    filtered = []
    for s in states:
        if len(s) > 2 and s[2] == country:
            row = {k: (s[i] if i < len(s) else None) for i, k in enumerate(keys)}
            filtered.append(row)

    return jsonify({
        "error": err,
        "query": params,
        "country": country,
        "count": len(filtered),
        "states": filtered
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
