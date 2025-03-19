#!/usr/bin/env python3

import csv
import subprocess
import os
import math
import sys
import re
import json
from datetime import datetime

# File path relative to the script
CSV_FILE_PATH = "static/COHA-Station-Coordinates-v1.csv"

# Change this to your Google Maps API key if not using environment variable
GOOGLE_MAPS_API_KEY = ""  # Will be set from environment variable


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    Returns distance in meters
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371000  # Radius of earth in meters
    return c * r


def get_file_content_at_commit(commit_hash, relative_path):
    """Get file content at a specific git commit"""
    try:
        return subprocess.check_output(
            ["git", "show", f"{commit_hash}:{relative_path}"],
            universal_newlines=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error getting file content at commit {commit_hash}: {e}")
        sys.exit(1)


def get_git_commits(file_path):
    """Get a list of git commits for the file"""
    try:
        # Get the git log for the file
        return subprocess.check_output(
            ["git", "log", "--pretty=format:%H", file_path],
            universal_newlines=True
        ).strip().split("\n")
    except subprocess.CalledProcessError as e:
        print(f"Error getting git log: {e}")
        sys.exit(1)


def get_versions_to_compare():
    """
    Determine which versions to compare:
    - If filesystem differs from latest commit, compare filesystem to latest commit
    - If filesystem matches latest commit, compare latest commit to previous commit
    """
    # Get the current directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, CSV_FILE_PATH)

    # Change to the repository root directory
    repo_root = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        universal_newlines=True
    ).strip()
    os.chdir(repo_root)

    # Get the relative path to the file from the repo root
    relative_path = os.path.relpath(file_path, repo_root)

    # Get the commits
    commits = get_git_commits(relative_path)
    if not commits or commits[0] == "":
        print(f"Error: No git history found for {file_path}")
        sys.exit(1)

    # Get current filesystem content
    with open(file_path, "r") as f:
        current_fs_content = f.read()

    # Get content of latest commit
    latest_commit = commits[0]
    latest_commit_content = get_file_content_at_commit(latest_commit, relative_path)

    # Compare filesystem content with latest commit
    if current_fs_content != latest_commit_content:
        # Filesystem differs from latest commit
        print(f"Comparing filesystem version with latest commit {latest_commit[:8]}...")
        return current_fs_content, latest_commit_content, "filesystem", latest_commit[:8]
    else:
        # Filesystem matches latest commit, compare with previous commit
        if len(commits) < 2:
            print("Only one commit exists in history. Nothing to compare.")
            sys.exit(0)

        previous_commit = commits[1]
        previous_commit_content = get_file_content_at_commit(previous_commit, relative_path)

        print(f"Filesystem matches latest commit. Comparing commits {latest_commit[:8]} and {previous_commit[:8]}...")
        return latest_commit_content, previous_commit_content, latest_commit[:8], previous_commit[:8]


def load_csv_to_dict(content):
    """Load CSV content into a dictionary keyed by Quadrat/Station"""
    lines = content.strip().split('\n')
    reader = csv.DictReader(lines)

    result = {}
    for row in reader:
        # Create a composite key from Quadrat and Station
        # Strip whitespace from keys and values
        cleaned_row = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
        key = f"{cleaned_row.get('Quadrat', '')}/{cleaned_row.get('Station', '')}"
        result[key] = cleaned_row

    return result


def natural_sort_key(key):
    """
    Sort keys naturally so that A10 comes after A9
    This works by separating the text and number parts
    """
    parts = re.split(r'(\d+)', key)
    parts[1::2] = map(int, parts[1::2])  # Convert numeric parts to integers
    return parts


def generate_map_html(changes, lat_col, lon_col, current_label, previous_label):
    """Generate HTML with Google Maps to visualize location changes"""

    # Try to get API key from environment
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY', GOOGLE_MAPS_API_KEY)
    if not api_key:
        print("Warning: No Google Maps API key found. Map may not work correctly.")
        print("Set your API key in the script or use environment variable GOOGLE_MAPS_API_KEY")

    # Prepare data for JavaScript
    map_data = []
    center_lat, center_lon = 0, 0
    count = 0

    for key, prev_data, curr_data, distance in changes:
        count += 1
        center_lat += float(curr_data[lat_col])
        center_lon += float(curr_data[lon_col])

        # Color based on distance (red for >50m, yellow for 20-50m, green for <20m)
        color = "red" if distance > 50 else "yellow" if distance > 20 else "green"

        map_data.append({
            "id": key,
            "prev": {
                "lat": float(prev_data[lat_col]),
                "lng": float(prev_data[lon_col])
            },
            "curr": {
                "lat": float(curr_data[lat_col]),
                "lng": float(curr_data[lon_col])
            },
            "distance": distance,
            "color": color
        })

    # Calculate center of the map (average of current locations)
    if count > 0:
        center_lat /= count
        center_lon /= count

    # Generate HTML
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    html_filename = f"location_changes_map_{timestamp}.html"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>COHA Station Location Changes</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        html, body, #map {{ height: 100%; width: 100%; margin: 0; padding: 0; }}
        #info-panel {{
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 1000;
            background-color: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.2);
            max-height: 95%;
            overflow-y: auto;
            max-width: 300px;
        }}
        .legend {{
            background-color: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.2);
            margin-bottom: 10px;
        }}
        .color-box {{
            display: inline-block;
            width: 12px;
            height: 12px;
            margin-right: 5px;
        }}
        .station-list {{
            max-height: 400px;
            overflow-y: auto;
            margin-top: 10px;
        }}
        .station-item {{
            cursor: pointer;
            padding: 3px;
            border-bottom: 1px solid #eee;
        }}
        .station-item:hover {{
            background-color: #f8f8f8;
        }}
        .station-item.selected {{
            background-color: #e8e8e8;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div id="info-panel">
        <h2>Location Changes</h2>
        <p>Comparing {current_label} vs {previous_label}</p>

        <div class="legend">
            <h3>Legend</h3>
            <div><span class="color-box" style="background-color: red;"></span> &gt;50m change</div>
            <div><span class="color-box" style="background-color: yellow;"></span> 20-50m change</div>
            <div><span class="color-box" style="background-color: green;"></span> &lt;20m change</div>
            <div>
                <svg height="20" width="60">
                    <line x1="10" y1="10" x2="50" y2="10" style="stroke:black;stroke-width:2" />
                    <circle cx="10" cy="10" r="4" stroke="black" stroke-width="1" fill="white" />
                    <circle cx="50" cy="10" r="4" stroke="black" stroke-width="1" fill="gray" />
                </svg>
                Direction of change
            </div>
        </div>

        <div>
            <h3>Filter</h3>
            <select id="filter-distance">
                <option value="all">All changes</option>
                <option value="significant">Significant (&gt;50m)</option>
                <option value="medium">Medium (20-50m)</option>
                <option value="minor">Minor (&lt;20m)</option>
            </select>
            <input type="text" id="search-station" placeholder="Search by ID" style="margin-top: 5px; width: 100%;">
        </div>

        <div class="station-list" id="station-list">
            <!-- Station list will be populated by JavaScript -->
        </div>
    </div>

    <div id="map"></div>

    <script>
        // Map data
        const mapData = {json.dumps(map_data)};
        let map;
        let markers = [];
        let lines = [];
        let activeInfoWindow = null;

        function initMap() {{
            map = new google.maps.Map(document.getElementById('map'), {{
                center: {{ lat: {center_lat}, lng: {center_lon} }},
                zoom: 12
            }});

            renderMarkers(mapData);
            populateStationList(mapData);

            // Set up event listeners
            document.getElementById('filter-distance').addEventListener('change', filterStations);
            document.getElementById('search-station').addEventListener('input', filterStations);
        }}

        function renderMarkers(data) {{
            // Clear existing markers and lines
            clearMapObjects();

            data.forEach(station => {{
                // Create markers for previous and current locations
                const prevMarker = new google.maps.Marker({{
                    position: station.prev,
                    map: map,
                    title: `${{station.id}} (Previous)`,
                    icon: {{
                        path: google.maps.SymbolPath.CIRCLE,
                        scale: 5,
                        fillColor: "white",
                        fillOpacity: 1,
                        strokeWeight: 1,
                        strokeColor: "black"
                    }}
                }});

                const currMarker = new google.maps.Marker({{
                    position: station.curr,
                    map: map,
                    title: `${{station.id}} (Current)`,
                    icon: {{
                        path: google.maps.SymbolPath.CIRCLE,
                        scale: 5,
                        fillColor: "gray",
                        fillOpacity: 1,
                        strokeWeight: 1,
                        strokeColor: "black"
                    }}
                }});

                // Create a line between the two points
                const line = new google.maps.Polyline({{
                    path: [station.prev, station.curr],
                    geodesic: true,
                    strokeColor: station.color,
                    strokeOpacity: 0.8,
                    strokeWeight: 2
                }});
                line.setMap(map);

                // Add info window
                const infoContent = `
                    <div>
                        <h3>${{station.id}}</h3>
                        <p>Distance: ${{station.distance.toFixed(2)}} meters</p>
                        <p>Previous: ${{station.prev.lat.toFixed(6)}}, ${{station.prev.lng.toFixed(6)}}</p>
                        <p>Current: ${{station.curr.lat.toFixed(6)}}, ${{station.curr.lng.toFixed(6)}}</p>
                    </div>
                `;

                const infoWindow = new google.maps.InfoWindow({{
                    content: infoContent
                }});

                // Add click event to both markers
                [prevMarker, currMarker].forEach(marker => {{
                    marker.addListener('click', () => {{
                        if (activeInfoWindow) {{
                            activeInfoWindow.close();
                        }}
                        infoWindow.open(map, marker);
                        activeInfoWindow = infoWindow;

                        // Highlight the station in the list
                        highlightStationInList(station.id);
                    }});
                }});

                // Store markers and lines for later reference
                markers.push(prevMarker, currMarker);
                lines.push(line);

                // Add data reference to markers for filtering
                prevMarker.stationData = station;
                currMarker.stationData = station;
                line.stationData = station;
            }});
        }}

        function clearMapObjects() {{
            markers.forEach(marker => marker.setMap(null));
            lines.forEach(line => line.setMap(null));
            markers = [];
            lines = [];
            if (activeInfoWindow) {{
                activeInfoWindow.close();
                activeInfoWindow = null;
            }}
        }}

        function populateStationList(data) {{
            const stationList = document.getElementById('station-list');
            stationList.innerHTML = '';

            data.sort((a, b) => b.distance - a.distance);

            data.forEach(station => {{
                const item = document.createElement('div');
                item.className = 'station-item';
                item.setAttribute('data-id', station.id);
                item.setAttribute('data-distance', station.distance);

                const distanceClass = station.distance > 50 ? 'significant' : 
                                     station.distance > 20 ? 'medium' : 'minor';
                item.classList.add(distanceClass);

                item.innerHTML = `
                    <span class="color-box" style="background-color: ${{station.color}};"></span>
                    ${{station.id}} - ${{station.distance.toFixed(2)}}m
                `;

                item.addEventListener('click', () => {{
                    // Center map on this station
                    map.setCenter(station.curr);
                    map.setZoom(18);

                    // Open info window
                    if (activeInfoWindow) {{
                        activeInfoWindow.close();
                    }}

                    const infoContent = `
                        <div>
                            <h3>${{station.id}}</h3>
                            <p>Distance: ${{station.distance.toFixed(2)}} meters</p>
                            <p>Previous: ${{station.prev.lat.toFixed(6)}}, ${{station.prev.lng.toFixed(6)}}</p>
                            <p>Current: ${{station.curr.lat.toFixed(6)}}, ${{station.curr.lng.toFixed(6)}}</p>
                        </div>
                    `;

                    const infoWindow = new google.maps.InfoWindow({{
                        content: infoContent,
                        position: station.curr
                    }});

                    infoWindow.open(map);
                    activeInfoWindow = infoWindow;

                    // Highlight this item
                    highlightStationInList(station.id);
                }});

                stationList.appendChild(item);
            }});
        }}

        function highlightStationInList(id) {{
            // Remove highlight from all stations
            document.querySelectorAll('.station-item').forEach(item => {{
                item.classList.remove('selected');
            }});

            // Add highlight to selected station
            const selectedItem = document.querySelector(`.station-item[data-id="${{id}}"]`);
            if (selectedItem) {{
                selectedItem.classList.add('selected');
                selectedItem.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
            }}
        }}

        function filterStations() {{
            const filterValue = document.getElementById('filter-distance').value;
            const searchText = document.getElementById('search-station').value.toLowerCase();

            // Filter the data based on criteria
            const filteredData = mapData.filter(station => {{
                // Distance filter
                if (filterValue === 'significant' && station.distance <= 50) return false;
                if (filterValue === 'medium' && (station.distance <= 20 || station.distance > 50)) return false;
                if (filterValue === 'minor' && station.distance >= 20) return false;

                // Search filter
                if (searchText && !station.id.toLowerCase().includes(searchText)) return false;

                return true;
            }});

            // Update the map and list
            renderMarkers(filteredData);
            populateStationList(filteredData);
        }}
    </script>

    <script async defer
        src="https://maps.googleapis.com/maps/api/js?key={api_key}&callback=initMap">
    </script>
</body>
</html>
"""

    # Write HTML to file
    with open(html_filename, 'w') as f:
        f.write(html_content)

    print(f"\nMap visualization created: {html_filename}")

    # Try to open the map in a browser
    try:
        import webbrowser
        webbrowser.open('file://' + os.path.realpath(html_filename))
    except Exception as e:
        print(f"Could not automatically open browser: {e}")
        print(f"Please open the file manually: {os.path.realpath(html_filename)}")

    return html_filename


def main():
    # Get the versions to compare
    current_content, previous_content, current_label, previous_label = get_versions_to_compare()

    # Load the versions
    current_data = load_csv_to_dict(current_content)
    previous_data = load_csv_to_dict(previous_content)

    # Look for latitude and longitude column names
    cur_cols = current_content.strip().split('\n')[0].split(',')
    lat_col = next((col.strip() for col in cur_cols if col.strip().lower() in ('lat', 'latitude')), None)
    lon_col = next((col.strip() for col in cur_cols if col.strip().lower() in ('lon', 'long', 'longitude')), None)

    if not lat_col or not lon_col:
        print(f"Error: Could not identify latitude/longitude columns. Found: {cur_cols}")
        sys.exit(1)

    print(f"Using columns: '{lat_col}' for latitude and '{lon_col}' for longitude\n")

    # Track changes for map visualization
    changes = []

    # Get all keys and sort them naturally
    all_keys = sorted(set(previous_data.keys()) | set(current_data.keys()),
                      key=lambda k: natural_sort_key(k.split('/')[0] + k.split('/')[1]))

    # Calculate distances and track changes
    for key in all_keys:
        if key in previous_data and key in current_data:
            prev_row = previous_data[key]
            curr_row = current_data[key]

            # Check if lat/lon exists in both versions
            if lat_col in prev_row and lat_col in curr_row and lon_col in prev_row and lon_col in curr_row:
                try:
                    # Calculate distance
                    distance = haversine_distance(
                        float(prev_row[lat_col]), float(prev_row[lon_col]),
                        float(curr_row[lat_col]), float(curr_row[lon_col])
                    )

                    if distance > 0:
                        changes.append((key, prev_row, curr_row, distance))

                        # Print significant changes to console
                        if distance > 50:
                            print(f"{key}: {distance:.2f}m (significant)")
                        elif distance > 20:
                            print(f"{key}: {distance:.2f}m (medium)")
                except (ValueError, TypeError) as e:
                    print(f"{key}: Error calculating distance - {e}")

    # Sort changes by distance (largest first)
    changes.sort(key=lambda x: x[3], reverse=True)

    # Generate a distribution of changes
    significant = sum(1 for _, _, _, d in changes if d > 50)
    medium = sum(1 for _, _, _, d in changes if 20 < d <= 50)
    minor = sum(1 for _, _, _, d in changes if 0 < d <= 20)

    # Print summary
    print(f"\n{'-' * 50}")
    print(f"Total stations with coordinate changes: {len(changes)}")
    print(f"  Significant changes (>50m): {significant}")
    print(f"  Medium changes (20-50m): {medium}")
    print(f"  Minor changes (<20m): {minor}")

    # Generate map visualization if there are changes
    if changes:
        try:
            html_file = generate_map_html(changes, lat_col, lon_col, current_label, previous_label)
            print(f"\nMap visualization created successfully: {html_file}")
        except Exception as e:
            print(f"\nError creating map visualization: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\nNo changes to visualize on the map.")


if __name__ == "__main__":
    main()