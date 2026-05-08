import requests
import pandas as pd
import time

ACCESS_TOKEN = 'MLY|35816332414678604|6111251f92735c5b73484ad3b0812f64'

# ═══════════════════════════════════════════════════════════════════════════
# REGION SELECTION — Comment/uncomment to switch
# ═══════════════════════════════════════════════════════════════════════════
# Islington only
BBOX = (-0.1389, 51.5200, -0.0874, 51.5685)
OUT_CSV = r'C:\Users\maria\Documents\GitHub\DataEncoding_G02_Urban-Safety\mapillary_streetlights_islington.csv'

# Full Greater London (uncomment to use instead)
# BBOX = (-0.510, 51.280, 0.334, 51.684)
# OUT_CSV = r'C:\Users\maria\Documents\GitHub\DataEncoding_G02_Urban-Safety\mapillary_streetlights_london.csv'


def fetch_lights_for_tile(min_lon, min_lat, max_lon, max_lat, token):
    """Fetch all street light detections for one tile, handling pagination."""
    url = 'https://graph.mapillary.com/map_features'
    params = {
        'access_token' : token,
        'fields'       : 'id,object_value,geometry',
        'bbox'         : f'{min_lon},{min_lat},{max_lon},{max_lat}',
        'object_value': 'object--street-light',  # Changed from object_values (singular)
        'limit'        : 2000
    }
    points = []
    while True:
        max_retries = 3
        r = None
        for attempt in range(max_retries):
            try:
                r = requests.get(url, params=params, timeout=60)
                break
            except requests.exceptions.ReadTimeout:
                if attempt < max_retries - 1:
                    wait = 5 * (2 ** attempt)  # 5s, 10s, 20s
                    print(f'    [Timeout, retry in {wait}s]', end=' ')
                    time.sleep(wait)
                else:
                    print(f'    [Failed after {max_retries} attempts]')
                    return points
        
        if r.status_code != 200:
            print(f'  Error {r.status_code}: {r.text[:200]}')
            # Print debug URL on error
            if 'debug' in params:
                print(f'  URL: {r.request.url}')
            break
        data = r.json()
        
        # Debug: show response on first tile
        if not points and not all_points:
            print(f'\n  [Debug] Response keys: {data.keys()}')
            if 'data' in data:
                print(f'  [Debug] Found {len(data["data"])} features')
        
        batch = data.get('data', [])
        for f in batch:
            coords = f['geometry']['coordinates']
            points.append({'mapillary_id': f['id'], 'longitude': coords[0], 'latitude': coords[1]})
        cursor = data.get('paging', {}).get('cursors', {}).get('after')
        if not cursor or len(batch) < 2000:
            break
        params['after'] = cursor
        time.sleep(0.2)  # be polite to the API
    return points

# Tile the bounding box into a 4x4 grid
import numpy as np
min_lon, min_lat, max_lon, max_lat = BBOX
lons = np.linspace(min_lon, max_lon, 9)
lats = np.linspace(min_lat, max_lat, 9)

all_points = []
total_tiles = 16
for i, (lon0, lon1) in enumerate(zip(lons, lons[1:])):
    for j, (lat0, lat1) in enumerate(zip(lats, lats[1:])):
        tile_num = i * 4 + j + 1
        print(f'Tile {tile_num}/{total_tiles}...', end=' ')
        pts = fetch_lights_for_tile(lon0, lat0, lon1, lat1, ACCESS_TOKEN)
        print(f'{len(pts)} lights found')
        all_points.extend(pts)
        time.sleep(0.3)

# Deduplicate (tiles share edges)
df = pd.DataFrame(all_points).drop_duplicates(subset='mapillary_id')
df.to_csv(OUT_CSV, index=False)
print(f'\nSaved {len(df):,} street lights to {OUT_CSV}')