#!/usr/bin/env python3

import csv
import subprocess
import os
import math
import sys
import re
from colorama import Fore, Style, init

# Initialize colorama for cross-platform colored terminal output
init()

# File path relative to the script
CSV_FILE_PATH = "static/COHA-Station-Coordinates-v1.csv"


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


def main():
    # Get the versions to compare
    current_content, previous_content, current_label, previous_label = get_versions_to_compare()

    # Load the versions
    current_data = load_csv_to_dict(current_content)
    previous_data = load_csv_to_dict(previous_content)

    # Print header
    print(f"\nComparing {current_label} with {previous_label}...")

    # Debug: Print column names from both versions to help diagnose issues
    print("\nDebug - Column Names:")
    cur_cols = current_content.strip().split('\n')[0].split(',')
    prev_cols = previous_content.strip().split('\n')[0].split(',')
    print(f"Current version columns: {[col.strip() for col in cur_cols]}")
    print(f"Previous version columns: {[col.strip() for col in prev_cols]}")

    # Look for latitude and longitude column names
    lat_col = next((col for col in cur_cols if col.strip().lower() in ('lat', 'latitude')), None)
    lon_col = next((col for col in cur_cols if col.strip().lower() in ('lon', 'long', 'longitude')), None)

    if not lat_col or not lon_col:
        print(f"Error: Could not identify latitude/longitude columns. Found: {cur_cols}")
        sys.exit(1)

    print(f"Using columns: '{lat_col.strip()}' for latitude and '{lon_col.strip()}' for longitude\n")

    # Normalize column names
    lat_col = lat_col.strip()
    lon_col = lon_col.strip()

    print(f"{'Quadrat/Station':<20} {'Distance (m)':<15} {'Status'}\n{'-' * 50}")

    # Track stations that have significant changes
    significant_changes = []
    all_changes = []

    # Get all keys and sort them naturally
    all_keys = sorted(set(previous_data.keys()) | set(current_data.keys()),
                      key=lambda k: natural_sort_key(k.split('/')[0] + k.split('/')[1]))

    # Compare coordinates and calculate distances
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
                        all_changes.append((key, distance))

                    # Format output with highlighting for significant changes
                    if distance > 50:
                        status = f"{Fore.RED}SIGNIFICANT CHANGE{Style.RESET_ALL}"
                        significant_changes.append((key, distance))
                        print(f"{key:<20} {distance:<15.2f} {status}")
                    elif distance > 0:
                        print(f"{key:<20} {distance:<15.2f} Minor change")
                except (ValueError, TypeError) as e:
                    print(f"{key:<20} {'ERROR':<15} Could not calculate distance: {e}")
                    print(
                        f"  Debug - Values: prev({prev_row[lat_col]}, {prev_row[lon_col]}) curr({curr_row[lat_col]}, {curr_row[lon_col]})")
            else:
                missing = []
                if lat_col not in prev_row: missing.append(f"prev {lat_col}")
                if lat_col not in curr_row: missing.append(f"curr {lat_col}")
                if lon_col not in prev_row: missing.append(f"prev {lon_col}")
                if lon_col not in curr_row: missing.append(f"curr {lon_col}")
                print(f"{key:<20} {'N/A':<15} Missing coordinate data: {', '.join(missing)}")
        elif key in previous_data:
            print(f"{key:<20} {'REMOVED':<15} Station removed")
        elif key in current_data:
            print(f"{key:<20} {'NEW':<15} New station added")

    # Summary
    print(f"\n{'-' * 50}")
    print(f"Total stations with coordinate changes: {len(all_changes)}")

    if significant_changes:
        print(
            f"\n{Fore.RED}Found {len(significant_changes)} stations with significant changes (>50m):{Style.RESET_ALL}")
        for key, distance in significant_changes:
            print(f"  - {key}: {distance:.2f}m")
    else:
        print(f"\n{Fore.GREEN}No significant location changes found (>50m){Style.RESET_ALL}")


if __name__ == "__main__":
    main()