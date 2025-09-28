from flask import Flask, render_template_string, jsonify
import requests, os
from collections import Counter
from urllib.parse import urlencode

app = Flask(__name__)

# --- fixed server-side bbox ---
DEFAULT_BBOX = {
    "lamin": os.getenv("LAMIN", "35.9"),
    "lamax": os.getenv("LAMAX", "42.1"),
    "lomin": os.getenv("LOMIN", "25.9"),
    "lomax": os.getenv("LOMAX", "45.1"),
}
OPEN_SKY_API = "https://opensky-network.org/api/states/all"
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
<title>Israeli Aircraft Tracker</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
 body {font-family:system-ui, sans-serif; margin:0; padding:0;}
 header {padding:12px 20px; display:flex; gap:12px; align-items:center; background:#f3f4f6;}
 h1 {margin:0; font-size:20px;}
 #btnRefresh[disabled]{opacity:.6;cursor:not-allowed;}
 #map {height:60vh; width:100%;}
 .counts{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;padding:10px;}
 .count-card{border:1px solid #ddd;border-radius:10px;padding:8px;}
 .pill{background:#eef2ff;padding:4px 8px;border-radius:999px;font-size:12px;display:inline-block;}
 .israel .pill{background:#ffe4e6;font-weight:700;color:#b91c1c;}
 table{border-collapse:collapse;width:100%;margin:10px;}
 th,td{border:1px solid #e5e7eb;padding:6px 8px;font-size:13px;}
 th{background:#f3f4f6;}
</style>
</head>
<body>
<header>
  <h1>Israeli Aircraft Over Turkey</h1>
  <button id="btnRefresh">Refresh</button>
</header>

<div id="map"></div>

<h3 style="margin:10px;">Counts by origin_country</h3>
<div id="counts" class="counts">
  {% set maxc = (country_counts[0][1] if country_counts else 1) %}
  {% for c,n in country_counts %}
    <div class="count-card {% if c=='Israel' %}israel{% endif %}">
      <div class="pill">{{c or "Unknown"}}</div>
      <div>{{n}} flights</div>
    </div>
  {% endfor %}
</div>

<h3 style="margin:10px;">Israeli flights — <span id="rowCount">{{rows|length}}</span></h3>
<table id="dataTable">
<thead>
<tr>
 <th>icao24</th><th>callsign</th><th>longitude</th><th>latitude</th>
 <th>geo_altitude</th><th>velocity</th><th>true_track</th>
</tr>
</thead>
<tbody>
{% for s in rows %}
<tr>
 <td>{{s[0]}}</td><td>{{s[1]}}</td><td>{{s[5]}}</td><td>{{s[6]}}</td>
 <td>{{s[13]}}</td><td>{{s[9]}}</td><td>{{s[10]}}</td>
</tr>
{% endfor %}
</tbody>
</table>

<script>
let map = L.map('map').setView([39,35],6);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
  attribution:'&copy; OpenStreetMap contributors'
}).addTo(map);

let markersLayer = L.layerGroup().addTo(map);

function updateMap(rows){
  markersLayer.clearLayers();
  if(!rows.length) return;
  let bounds = [];
  rows.forEach(r=>{
    if(r[5] && r[6]){
      const m = L.marker([r[6], r[5]], {
        icon: L.icon({
          iconUrl:'https://cdn-icons-png.flaticon.com/512/67/67902.png',
          iconSize:[24,24]
        })
      }).bindPopup(`<b>${r[1]||''}</b><br>Alt: ${r[13]||'?' } m<br>Vel: ${r[9]||'?'} m/s`);
      m.addTo(markersLayer);
      bounds.push([r[6], r[5]]);
    }
  });
  if(bounds.length) map.fitBounds(bounds, {padding:[20,20]});
}

async function refresh(){
  const btn=document.getElementById('btnRefresh');
  btn.disabled=true; btn.textContent='Refreshing...';
  try{
    const r=await fetch('/json',{cache:'no-store'});
    const d=await r.json();
    document.getElementById('rowCount').textContent=d.rows.length;

    // counts
    const cdiv=document.getElementById('counts');
    cdiv.innerHTML='';
    d.counts.forEach(([name,cnt])=>{
      const card=document.createElement('div');
      card.className='count-card'+(name==='Israel'?' israel':'');
      card.innerHTML=`<div class="pill">${name||'Unknown'}</div><div>${cnt} flights</div>`;
      cdiv.appendChild(card);
    });

    // table
    const tb=document.querySelector('#dataTable tbody');
    tb.innerHTML='';
    d.rows.forEach(r=>{
      const tr=document.createElement('tr');
      tr.innerHTML=`<td>${r[0]||''}</td><td>${r[1]||''}</td><td>${r[5]||''}</td><td>${r[6]||''}</td>
                    <td>${r[13]||''}</td><td>${r[9]||''}</td><td>${r[10]||''}</td>`;
      tb.appendChild(tr);
    });

    updateMap(d.rows);
  }catch(e){alert(e);}
  btn.disabled=false; btn.textContent='Refresh';
}

document.getElementById('btnRefresh').addEventListener('click',refresh);
updateMap({{ rows|tojson }});
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
    return url, data.get("states") or []

@app.route("/")
def index():
    try:
        bbox_url, states = _fetch_states()
    except Exception as e:
        return f"<h1>Error: {e}</h1>"
    counts = Counter([s[2] for s in states if s and len(s) >= len(COLS)])
    rows  = [s for s in states if s and len(s) >= len(COLS) and s[2]=="Israel"]
    return render_template_string(HTML, bbox_url=bbox_url,
                                  country_counts=sorted(counts.items(), key=lambda x:x[1], reverse=True),
                                  rows=rows)

@app.route("/json")
def json_data():
    bbox_url, states = _fetch_states()
    counts = Counter([s[2] for s in states if s and len(s) >= len(COLS)])
    rows  = [s for s in states if s and len(s) >= len(COLS) and s[2]=="Israel"]
    return jsonify({"bbox_url":bbox_url,
                    "counts":sorted(counts.items(), key=lambda x:x[1], reverse=True),
                    "rows":rows})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
