#!/usr/bin/env python3

import csv
import subprocess
import os
import math
import sys
import re
import json
import logging
import webbrowser
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# File path relative to the script
CSV_FILE_PATH = "static/COHA-Station-Coordinates-v1.csv"

# Change this to your Google Maps API key if not using environment variable
GOOGLE_MAPS_API_KEY = ""  # Will be set from environment variable

# Grid corners provided by the user
NW_CORNER = (49.263732, -123.157839)  # Northwest corner of quadrat A
SE_CORNER = (49.209817, -122.938138)  # Southeast corner of quadrat X

# Grid dimensions
GRID_ROWS = 3  # Number of rows (A-Q-I, etc.)
GRID_COLS = 8  # Number of columns (A-B-C-D-E-F-G-H, etc.)


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
        logging.error(f"Error getting file content at commit {commit_hash}: {e}")
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
        logging.error(f"Error getting git log: {e}")
        sys.exit(1)


def get_versions_to_compare():
    """
    Determine which versions to compare:
    - If filesystem differs from latest commit, compare filesystem to latest commit
    - If filesystem matches latest commit, compare latest commit to previous commit
    """
    logging.info("Determining versions to compare...")

    # Get the current directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, CSV_FILE_PATH)

    logging.info(f"Looking for file at: {file_path}")
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        sys.exit(1)

    # Change to the repository root directory
    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            universal_newlines=True
        ).strip()
        logging.info(f"Git repository root: {repo_root}")
        os.chdir(repo_root)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error finding git repository root: {e}")
        sys.exit(1)

    # Get the relative path to the file from the repo root
    relative_path = os.path.relpath(file_path, repo_root)
    logging.info(f"Relative path: {relative_path}")

    # Get the commits
    commits = get_git_commits(relative_path)
    if not commits or commits[0] == "":
        logging.error(f"Error: No git history found for {file_path}")
        sys.exit(1)

    logging.info(f"Found {len(commits)} commits for this file")

    # Get current filesystem content
    with open(file_path, "r") as f:
        current_fs_content = f.read()

    # Get content of latest commit
    latest_commit = commits[0]
    latest_commit_content = get_file_content_at_commit(latest_commit, relative_path)

    # Compare filesystem content with latest commit
    if current_fs_content != latest_commit_content:
        # Filesystem differs from latest commit
        logging.info(f"Comparing filesystem version with latest commit {latest_commit[:8]}...")
        return current_fs_content, latest_commit_content, "filesystem", latest_commit[:8]
    else:
        # Filesystem matches latest commit, compare with previous commit
        if len(commits) < 2:
            logging.warning("Only one commit exists in history. Nothing to compare.")
            sys.exit(0)

        previous_commit = commits[1]
        previous_commit_content = get_file_content_at_commit(previous_commit, relative_path)

        logging.info(
            f"Filesystem matches latest commit. Comparing commits {latest_commit[:8]} and {previous_commit[:8]}...")
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


def calculate_quadrat_boundaries():
    """Calculate the boundaries of all quadrats in the grid"""
    # Grid dimensions
    nw_lat, nw_lon = NW_CORNER
    se_lat, se_lon = SE_CORNER

    lat_range = nw_lat - se_lat
    lon_range = se_lon - nw_lon

    quad_lat_size = lat_range / GRID_ROWS
    quad_lon_size = lon_range / GRID_COLS

    # Calculate boundaries for each quadrat
    quadrat_boundaries = {}

    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            # Convert row,col to quadrat letter (A-X)
            quadrat_index = row * GRID_COLS + col
            quadrat = chr(65 + quadrat_index)  # 65 is ASCII for 'A'

            # Calculate lat/lon boundaries
            north = nw_lat - (row * quad_lat_size)
            south = north - quad_lat_size
            west = nw_lon + (col * quad_lon_size)
            east = west + quad_lon_size

            quadrat_boundaries[quadrat] = {
                'north': north,
                'south': south,
                'west': west,
                'east': east
            }

    return quadrat_boundaries


def calculate_station_coordinates(quadrat_boundaries):
    """Calculate ideal coordinates for all stations in all quadrats"""
    station_coordinates = {}

    for quadrat, bounds in quadrat_boundaries.items():
        # Divide quadrat into 4x4 grid for stations
        lat_step = (bounds['north'] - bounds['south']) / 4
        lon_step = (bounds['east'] - bounds['west']) / 4

        # Calculate coordinates for each station
        for row in range(4):
            for col in range(4):
                # Determine station number using serpentine pattern
                if row % 2 == 0:  # Rows 0, 2 (numbered 1, 3) - west to east
                    station_num = (row * 4) + col + 1
                else:  # Rows 1, 3 (numbered 2, 4) - east to west
                    station_num = (row * 4) + (4 - col)

                # Calculate station coordinates (center of each cell)
                lat = bounds['north'] - (row * lat_step) - (lat_step / 2)
                lon = bounds['west'] + (col * lon_step) + (lon_step / 2)

                station_key = f"{quadrat}/{station_num}"
                station_coordinates[station_key] = {
                    'lat': lat,
                    'lon': lon,
                    'row': row,
                    'col': col
                }

    return station_coordinates


def determine_expected_station(lat, lon, quadrat_boundaries):
    """
    Determine the expected quadrat and station number for a given coordinate
    """
    try:
        lat_float = float(lat)
        lon_float = float(lon)
    except (ValueError, TypeError):
        return None, None

    # Find which quadrat contains this point
    containing_quadrat = None
    for quadrat, bounds in quadrat_boundaries.items():
        if (bounds['south'] <= lat_float <= bounds['north'] and
                bounds['west'] <= lon_float <= bounds['east']):
            containing_quadrat = quadrat
            break

    if not containing_quadrat:
        return None, None

    # Calculate position within the quadrat
    bounds = quadrat_boundaries[containing_quadrat]
    lat_pos = (bounds['north'] - lat_float) / (bounds['north'] - bounds['south'])
    lon_pos = (lon_float - bounds['west']) / (bounds['east'] - bounds['west'])

    # Convert to row, col (0-3)
    row = min(3, max(0, int(lat_pos * 4)))
    col = min(3, max(0, int(lon_pos * 4)))

    # Determine station number using serpentine pattern
    if row % 2 == 0:  # Rows 0, 2 (numbered 1, 3) - west to east
        station_num = (row * 4) + col + 1
    else:  # Rows 1, 3 (numbered 2, 4) - east to west
        station_num = (row * 4) + (4 - col)

    return containing_quadrat, str(station_num)


def render_html_template(template_path, output_path, template_data):
    """Render HTML template with the provided data"""
    # Read the template file
    with open(template_path, 'r') as f:
        template_content = f.read()

    # Substitute all placeholders in the template
    for key, value in template_data.items():
        placeholder = f"{{{{ {key} }}}}"
        template_content = template_content.replace(placeholder, str(value))

    # Write the final HTML
    with open(output_path, 'w') as f:
        f.write(template_content)

    return output_path


def main():
    """Main function to process data and create visualization"""
    # Get versions to compare
    current_content, previous_content, current_label, previous_label = get_versions_to_compare()

    # Load the versions
    current_data = load_csv_to_dict(current_content)
    previous_data = load_csv_to_dict(previous_content)

    # Look for latitude and longitude column names
    cur_cols = current_content.strip().split('\n')[0].split(',')
    lat_col = next((col.strip() for col in cur_cols if col.strip().lower() in ('lat', 'latitude')), None)
    lon_col = next((col.strip() for col in cur_cols if col.strip().lower() in ('lon', 'long', 'longitude')), None)

    if not lat_col or not lon_col:
        logging.error(f"Error: Could not identify latitude/longitude columns. Found: {cur_cols}")
        sys.exit(1)

    logging.info(f"Using columns: '{lat_col}' for latitude and '{lon_col}' for longitude")

    # Calculate quadrat boundaries and station coordinates
    quadrat_boundaries = calculate_quadrat_boundaries()
    station_coordinates = calculate_station_coordinates(quadrat_boundaries)
    logging.info(
        f"Calculated boundaries for {len(quadrat_boundaries)} quadrats and coordinates for {len(station_coordinates)} stations")

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
                        # Determine expected station
                        quadrat, station = key.split('/')
                        expected_quadrat, expected_station = determine_expected_station(
                            curr_row[lat_col], curr_row[lon_col], quadrat_boundaries
                        )

                        changes.append((key, prev_row, curr_row, distance, expected_quadrat, expected_station))

                        # Print significant changes to console
                        if distance > 50:
                            expected_info = f" (expected: {expected_quadrat}/{expected_station})" if expected_quadrat and expected_station and (
                                        expected_quadrat != quadrat or expected_station != station) else ""
                            logging.info(f"{key}: {distance:.0f}m (significant){expected_info}")
                except (ValueError, TypeError) as e:
                    logging.error(f"{key}: Error calculating distance - {e}")

    # Sort changes by quadrat and then by station naturally
    changes.sort(key=lambda x: (
        x[0].split('/')[0],  # Sort by quadrat
        natural_sort_key(x[0].split('/')[1])  # Then by station naturally
    ))

    # Generate a distribution of changes
    significant = sum(1 for _, _, _, d, _, _ in changes if d > 50)
    medium = sum(1 for _, _, _, d, _, _ in changes if 20 < d <= 50)
    minor = sum(1 for _, _, _, d, _, _ in changes if 0 < d <= 20)

    # Count mismatches where expected station is different from current
    mismatches = sum(1 for key, _, _, _, eq, es in changes
                     if eq and es and (eq != key.split('/')[0] or es != key.split('/')[1]))

    # Print summary
    logging.info(f"Total stations with coordinate changes: {len(changes)}")
    logging.info(f"  Significant changes (>50m): {significant}")
    logging.info(f"  Medium changes (20-50m): {medium}")
    logging.info(f"  Minor changes (<20m): {minor}")
    logging.info(f"  Possible station mismatches: {mismatches}")

    # Prepare data for template
    map_data = []
    center_lat, center_lon = 0, 0
    count = 0

    for key, prev_data, curr_data, distance, expected_quadrat, expected_station in changes:
        count += 1
        center_lat += float(curr_data[lat_col])
        center_lon += float(curr_data[lon_col])

        # Color based on distance (red for >50m, yellow for 20-50m, green for <20m)
        color = "red" if distance > 50 else "yellow" if distance > 20 else "green"

        # Extract quadrat and station
        quadrat, station = key.split('/')

        # Check if there's a station number mismatch
        has_mismatch = expected_quadrat and expected_station and (
                expected_quadrat != quadrat or expected_station != station
        )

        map_data.append({
            "id": key,
            "quadrat": quadrat,
            "station": station,
            "expectedQuadrat": expected_quadrat,
            "expectedStation": expected_station,
            "prev": {
                "lat": float(prev_data[lat_col]),
                "lng": float(prev_data[lon_col])
            },
            "curr": {
                "lat": float(curr_data[lat_col]),
                "lng": float(curr_data[lon_col])
            },
            "distance": distance,
            "color": color,
            "hasMismatch": has_mismatch
        })

    # Calculate center of the map (average of current locations)
    if count > 0:
        center_lat /= count
        center_lon /= count

    # Try to get API key from environment
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY', GOOGLE_MAPS_API_KEY)
    if not api_key:
        logging.warning("No Google Maps API key found. Map may not work correctly.")
        logging.warning("Set your API key in the script or use environment variable GOOGLE_MAPS_API_KEY")

    # Prepare data for the template
    template_data = {
        "api_key": api_key,
        "center_lat": center_lat,
        "center_lon": center_lon,
        "current_label": current_label,
        "previous_label": previous_label,
        "map_data": json.dumps(map_data),
        "quadrat_boundaries": json.dumps(quadrat_boundaries),
        "station_coordinates": json.dumps(station_coordinates)
    }

    # Generate HTML
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    html_filename = f"location_changes_map_{timestamp}.html"

    # Read the template file - use same directory as script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(script_dir, "templates")
    template_path = os.path.join(template_dir, "location_changes_template.html")

    # Check if template exists
    if not os.path.exists(template_path):
        logging.error(f"Template file not found: {template_path}")
        logging.error("Please create the template file first.")
        sys.exit(1)

    # Render the template
    output_path = os.path.join(os.getcwd(), html_filename)
    render_html_template(template_path, output_path, template_data)

    logging.info(f"Map visualization created: {html_filename}")

    # Try to open the map in a browser
    try:
        webbrowser.open('file://' + os.path.realpath(output_path))
    except Exception as e:
        logging.error(f"Could not automatically open browser: {e}")
        logging.info(f"Please open the file manually: {os.path.realpath(output_path)}")

    return html_filename


if __name__ == "__main__":
    # Execute main function
    try:
        print("Script starting...")
        main()
        print("Script completed successfully")
    except Exception as e:
        print(f"Error executing main function: {e}")
        import traceback

        traceback.print_exc()