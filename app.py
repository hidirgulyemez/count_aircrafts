from flask import Flask, render_template_string, jsonify
import requests
import os
from collections import Counter
from urllib.parse import urlencode

app = Flask(__name__)

# ----- Fixed bounding box (server side) -----
DEFAULT_BBOX = {
    "lamin": os.getenv("LAMIN", "35.5"),
    "lamax": os.getenv("LAMAX", "42.5"),
    "lomin": os.getenv("LOMIN", "25.5"),
    "lomax": os.getenv("LOMAX", "45.5"),
}
OPEN_SKY_API = os.getenv("OPEN_SKY_API", "https://opensky-network.org/api/states/all")

COLS = [
    "icao24","callsign","origin_country","time_position","last_contact",
    "longitude","latitude","baro_altitude","on_ground","velocity",
    "true_track","vertical_rate","sensors","geo_altitude","squawk",
    "spi","position_source"
]

HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>OpenSky — Israeli Flights over Turkish Airspace now</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { --muted:#6b7280; --bar:#6366f1; --b:#e5e7eb; }
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }
  header { display:flex; gap:12px; align-items:baseline; flex-wrap:wrap; }
  .muted { color:var(--muted); font-size:12px; }
  #btnRefresh[disabled] { opacity:.6; cursor:not-allowed; }
  .error { background:#fee2e2; color:#7f1d1d; padding:10px; border-radius:8px; margin-top:10px; }

  .counts { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px,1fr)); gap:10px; margin:16px 0; }
  .count-card { border:1px solid var(--b); border-radius:10px; padding:10px; }
  .pill { background:#eef2ff; padding:6px 8px; border-radius:999px; font-size:12px; display:inline-block; }
  .bar { height:6px; background:var(--bar); border-radius:4px; margin-top:6px; }
  .israel .pill { background:#ffe4e6; font-weight:700; color:#b91c1c; }
  .israel .bar { background:#b91c1c; }

  table { border-collapse: collapse; width: 100%; margin-top: 16px; }
  th, td { border: 1px solid var(--b); padding: 8px 10px; font-size: 13px; }
  th { background: #f3f4f6; text-align: left; position: sticky; top: 0; z-index: 1; }
</style>
</head>
<body>
  <header>
    <h1>OpenSky Results — Israel flights</h1>
    <a id="apiLink" class="muted" href="{{ bbox_url }}" target="_blank" rel="noreferrer">API request ↗</a>
    <button id="btnRefresh" type="button">Refresh</button>
  </header>

  {% if error %}
    <div class="error">Error fetching data: {{ error }}</div>
  {% endif %}

  <div class="muted">Table shows only flights with origin_country = <b>Israel</b>.</div>

  <h3 style="margin-top:20px;">Counts by origin_country</h3>
  <div id="counts" class="counts">
    {% set maxc = (country_counts[0][1] if country_counts else 1) %}
    {% for c, n in country_counts %}
      <div class="count-card {% if c == 'Israel' %}israel{% endif %}">
        <div class="pill">{{ c or "Unknown" }}</div>
        <div class="muted">{{ n }} flights</div>
        <div class="bar" style="width: {{ (n/maxc)*100 }}%"></div>
      </div>
    {% endfor %}
  </div>

  <h3 id="tableHeading">Flights from Israel — <span id="rowCount">{{ rows|length }}</span> flights</h3>
  <table id="dataTable">
    <thead>
      <tr>
        <th>icao24</th><th>callsign</th><th>origin_country</th>
        <th>longitude</th><th>latitude</th><th>geo_altitude</th>
        <th>velocity</th><th>true_track</th><th>on_ground</th>
      </tr>
    </thead>
    <tbody>
      {% for s in rows %}
      <tr class="israel">
        <td>{{ s[0] }}</td>
        <td>{{ s[1] }}</td>
        <td>{{ s[2] }}</td>
        <td>{{ s[5] }}</td>
        <td>{{ s[6] }}</td>
        <td>{{ s[13] }}</td>
        <td>{{ s[9] }}</td>
        <td>{{ s[10] }}</td>
        <td>{{ s[8] }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

<script>
async function refreshData() {
  const btn = document.getElementById('btnRefresh');
  btn.disabled = true;
  const oldText = btn.textContent;
  btn.textContent = 'Refreshing...';

  try {
    const res = await fetch('/json', { cache: 'no-store' });
    if (!res.ok) throw new Error('Request failed: ' + res.status);
    const data = await res.json();

    // Update counts
    const countsDiv = document.getElementById('counts');
    countsDiv.innerHTML = '';
    const maxc = data.counts.length ? data.counts[0][1] : 1;
    for (const [name, cnt] of data.counts) {
      const isIsrael = name === 'Israel';
      const card = document.createElement('div');
      card.className = 'count-card' + (isIsrael ? ' israel' : '');
      card.innerHTML = `
        <div class="pill">${name || 'Unknown'}</div>
        <div class="muted">${cnt} flights</div>
        <div class="bar" style="width:${(cnt / maxc) * 100}%"></div>`;
      countsDiv.appendChild(card);
    }

    // Update table (Israel only)
    const tb = document.querySelector('#dataTable tbody');
    tb.innerHTML = '';
    for (const s of data.rows) {
      const tr = document.createElement('tr');
      tr.className = 'israel';
      tr.innerHTML = `
        <td>${s[0] ?? ''}</td>
        <td>${s[1] ?? ''}</td>
        <td>${s[2] ?? ''}</td>
        <td>${s[5] ?? ''}</td>
        <td>${s[6] ?? ''}</td>
        <td>${s[13] ?? ''}</td>
        <td>${s[9] ?? ''}</td>
        <td>${s[10] ?? ''}</td>
        <td>${s[8] ?? ''}</td>`;
      tb.appendChild(tr);
    }

    document.getElementById('rowCount').textContent = data.rows.length;
    document.getElementById('apiLink').href = data.bbox_url;

  } catch (e) {
    alert('Refresh failed: ' + e.message);
  } finally {
    btn.textContent = oldText;
    btn.disabled = false;
  }
}

document.getElementById('btnRefresh').addEventListener('click', refreshData);
</script>
</body>
</html>
"""

def _build_bbox_url():
    return f"{OPEN_SKY_API}?{urlencode(DEFAULT_BBOX)}"

def _fetch_states():
    url = _build_bbox_url()
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    if "states" not in data or data["states"] is None:
        return url, []
    return url, data["states"]

@app.route("/")
def index():
    error = None
    try:
        bbox_url, states = _fetch_states()
    except Exception as e:
        error = str(e)
        bbox_url, states = _build_bbox_url(), []

    counts = Counter([s[2] for s in states if s and len(s) >= len(COLS)])
    counts_sorted = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)

    # Filter only Israel flights
    rows = [s for s in states if s and len(s) >= len(COLS) and s[2] == "Israel"]

    return render_template_string(
        HTML,
        error=error,
        bbox_url=bbox_url,
        country_counts=counts_sorted,
        rows=rows
    )

@app.route("/json")
def json_data():
    try:
        bbox_url, states = _fetch_states()
        counts = Counter([s[2] for s in states if s and len(s) >= len(COLS)])
        counts_sorted = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        rows = [s for s in states if s and len(s) >= len(COLS) and s[2] == "Israel"]
        return jsonify({
            "bbox_url": bbox_url,
            "counts": counts_sorted,
            "rows": rows,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 502

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
