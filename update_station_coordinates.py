#!/usr/bin/env python3
import csv
import os
import subprocess
import tempfile
import glob
import argparse
from collections import defaultdict

# Configuration
BUCKET_NAME = "coha-data"  # Update this to your bucket name
COORDINATES_FILE = "static/COHA-Station-Coordinates-v1.csv"  # Now in static/ subdirectory
YEAR = "2023"  # Default year - now set to 2023


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Update COHA station coordinates from observation data')
    parser.add_argument('--skip-download', action='store_true',
                        help='Skip downloading files if you already have them')
    parser.add_argument('--data-dir', type=str,
                        help='Directory containing observation data (if skip-download is used)')
    parser.add_argument('--year', type=str, default=YEAR,
                        help=f'Year to process (default: {YEAR})')
    parser.add_argument('--list-years', action='store_true',
                        help='List available years in the bucket and exit')
    return parser.parse_args()


def list_available_years():
    """List available years in the observation filenames"""
    try:
        cmd = f"gsutil ls gs://{BUCKET_NAME}/*.csv"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: Unable to list bucket contents. Check bucket name: {BUCKET_NAME}")
            print(result.stderr)
            return []

        years = set()
        for line in result.stdout.splitlines():
            # Extract year from filename like C.01.2023-04-27.20-49-50.csv
            filename = os.path.basename(line.strip())
            parts = filename.split('.')
            if len(parts) >= 3:
                date_part = parts[2]
                if '-' in date_part:
                    year = date_part.split('-')[0]
                    if year.isdigit() and len(year) == 4:
                        years.add(year)

        return sorted(list(years))
    except Exception as e:
        print(f"Error listing years: {e}")
        return []


def download_observations(data_dir=None):
    """Download observation files from GCS bucket to a temporary or specified directory"""
    # Use provided directory or create a temporary one
    if data_dir:
        temp_dir = data_dir
        print(f"Using existing data directory: {temp_dir}")
    else:
        temp_dir = tempfile.mkdtemp()
        print(f"Created temporary directory: {temp_dir}")

        # Create the download destination
        os.makedirs(temp_dir, exist_ok=True)

        # Download all observation files for the specified year
        # Using pattern matching for filenames containing the year
        cmd = f"gsutil -m cp 'gs://{BUCKET_NAME}/*{YEAR}*.csv' {temp_dir}/"
        print(f"Downloading {YEAR} observations to {temp_dir}")
        print(f"Running: {cmd}")

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Download failed: {result.stderr}")
            raise Exception(f"gsutil command failed: {result.stderr}")
        else:
            file_count = len(glob.glob(f"{temp_dir}/*.csv"))
            if file_count == 0:
                print(f"Warning: No files were downloaded for year {YEAR}")
                available_years = list_available_years()
                if available_years:
                    years_str = ", ".join(available_years)
                    print(f"Available years: {years_str}")
                raise ValueError(f"No data files found for year {YEAR}")
            else:
                print(f"Download completed successfully. Downloaded {file_count} files.")

    return temp_dir


def extract_coordinates(temp_dir):
    """Extract unique quadrat/station coordinates from observation files"""
    # Dictionary to hold the most recent observation file for each quadrat/station
    latest_files = {}
    observation_files = glob.glob(f"{temp_dir}/*{YEAR}*.csv")

    print(f"Finding most recent observation for each quadrat/station...")

    # First, determine the most recent file for each quadrat/station
    for file_path in observation_files:
        try:
            # Extract quadrat, station and date from filename
            filename = os.path.basename(file_path)
            parts = filename.split('.')
            if len(parts) >= 3:  # At least quadrat.station.date
                quadrat = parts[0].upper()

                # Handle station number - normalize to non-zero-padded form
                station = parts[1]
                if station.isdigit():
                    station = str(int(station))  # Remove any leading zeros

                # Extract date part
                date_part = parts[2]
                if '-' in date_part:  # Should be in format YYYY-MM-DD
                    # Create a key for this quadrat/station
                    key = (quadrat, station)

                    # If we haven't seen this quadrat/station, or if this file is newer
                    if key not in latest_files or filename > latest_files[key][0]:
                        latest_files[key] = (filename, file_path)
        except Exception as e:
            print(f"Error processing filename {file_path}: {e}")

    print(f"Found {len(latest_files)} unique quadrat/station locations in {YEAR} data")

    # Now process only the most recent file for each quadrat/station
    coordinates = {}
    for key, (filename, file_path) in latest_files.items():
        try:
            quadrat, station = key

            # Read the file for lat/long
            with open(file_path, 'r') as f:
                reader = csv.reader(f)
                try:
                    header = next(reader)  # Skip header row
                except StopIteration:
                    print(f"Warning: Empty file {file_path}")
                    continue

                # Find column indices - try both direct column names and case insensitive
                lat_idx = None
                lon_idx = None

                # Try exact matches first
                try:
                    lat_idx = header.index('latitude')
                    lon_idx = header.index('longitude')
                except ValueError:
                    # Try case-insensitive matches
                    header_lower = [h.lower() for h in header]
                    try:
                        lat_idx = header_lower.index('latitude')
                        lon_idx = header_lower.index('longitude')
                    except ValueError:
                        # Try alternate spellings
                        if 'lat' in header_lower:
                            lat_idx = header_lower.index('lat')
                        if 'long' in header_lower or 'lng' in header_lower:
                            lon_idx = header_lower.index('long' if 'long' in header_lower else 'lng')

                if lat_idx is None or lon_idx is None:
                    print(f"Warning: Could not find latitude/longitude columns in {file_path}")
                    print(f"Headers: {header}")
                    continue

                # Get the data row (should only be one per file)
                for row in reader:
                    if len(row) > max(lat_idx, lon_idx):
                        latitude = row[lat_idx]
                        longitude = row[lon_idx]

                        # Only keep valid coordinates
                        if latitude and longitude and latitude != "0" and longitude != "0":
                            # Check if values are numeric
                            try:
                                float(latitude)
                                float(longitude)
                                coordinates[key] = (latitude, longitude)
                                break  # Only process the first data row
                            except ValueError:
                                print(f"Warning: Invalid coordinates in {file_path}: {latitude}, {longitude}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    print(f"Extracted coordinates for {len(coordinates)} quadrat/station locations from {YEAR} data")
    return coordinates


def update_coordinates_file(coordinates):
    """Update the coordinates CSV file with year data"""
    if not os.path.exists(COORDINATES_FILE):
        print(f"Error: {COORDINATES_FILE} not found")
        return

    # Read existing coordinates
    existing_coords = {}
    with open(COORDINATES_FILE, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            if len(row) >= 4:
                quadrat = row[0]
                # Normalize station number by removing leading zeros
                station = row[1]
                if station.isdigit():
                    station = str(int(station))
                key = (quadrat, station)
                existing_coords[key] = row

    # Check if we're potentially reducing the number of entries
    if len(existing_coords) > 0 and len(coordinates) < len(existing_coords):
        print(f"Warning: Found fewer coordinates ({len(coordinates)}) than existing in file ({len(existing_coords)})")
        print("This is normal if only some stations were surveyed in the selected year.")

    # Create backup of original file
    backup_file = f"{COORDINATES_FILE}.bak"
    os.rename(COORDINATES_FILE, backup_file)
    print(f"Created backup of original file: {backup_file}")

    # Write updated coordinates file
    updated_count = 0

    with open(COORDINATES_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        # Gather all data to be written, sorted by quadrat and station
        sorted_entries = []

        # Update existing entries with new coordinates where available
        for key, row in existing_coords.items():
            quadrat, station = key

            # For reporting and matching, we need to check if coordinates exist
            # with the normalized station value
            matched = False
            if key in coordinates:
                # Direct match found (normalized station numbers)
                latitude, longitude = coordinates[key]
                matched = True

            if matched:
                # Update existing entry
                updated_row = row.copy()
                updated_row[2] = latitude  # Update latitude
                updated_row[3] = longitude  # Update longitude
                updated_row[4] = YEAR  # Update year taken
                sorted_entries.append((quadrat, int(station) if station.isdigit() else 0, updated_row))
                updated_count += 1
            else:
                # Keep existing entry unchanged
                sorted_entries.append((quadrat, int(station) if station.isdigit() else 0, row))

        # Sort by quadrat (alphabetically) then station (numerically)
        sorted_entries.sort(key=lambda x: (x[0], x[1]))

        # Write the sorted entries
        for _, _, row in sorted_entries:
            writer.writerow(row)

    print(f"Updated {updated_count} coordinates (out of {len(existing_coords)} total entries)")
    print(f"Updated coordinates file saved to {COORDINATES_FILE}")

    # Verify file is properly sorted
    verify_file_sorting(COORDINATES_FILE)


def verify_file_sorting(file_path):
    """Verify that the CSV file is properly sorted by quadrat and station"""
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header

        prev_quadrat = None
        prev_station = -1
        is_sorted = True
        row_count = 0

        for i, row in enumerate(reader, start=2):  # Start at line 2 (after header)
            row_count += 1
            if len(row) >= 2:
                quadrat = row[0]
                try:
                    # Normalize station to integer for comparison
                    station = int(row[1]) if row[1].isdigit() else 0
                except ValueError:
                    station = 0

                if prev_quadrat is not None:
                    # Check if current row comes after previous row in sort order
                    if quadrat < prev_quadrat or (quadrat == prev_quadrat and station < prev_station):
                        print(
                            f"Warning: File not properly sorted at line {i}: {quadrat}.{station} comes after {prev_quadrat}.{prev_station}")
                        is_sorted = False

                prev_quadrat = quadrat
                prev_station = station

        if is_sorted:
            print(f"Verification: File is properly sorted by quadrat and station with {row_count} total entries.")
        else:
            print("Warning: File is not properly sorted!")


def main():
    try:
        # Parse command line arguments
        args = parse_args()

        # Override YEAR with command-line argument
        global YEAR
        YEAR = args.year

        # Just list years and exit if requested
        if args.list_years:
            print("Listing available years in bucket...")
            years = list_available_years()
            if years:
                print(f"Available years: {', '.join(years)}")
            else:
                print(f"No observation data found in bucket {BUCKET_NAME}")
            return

        # Step 1: Get observation files (download or use existing)
        if args.skip_download:
            if not args.data_dir:
                print("Error: --data-dir must be specified when using --skip-download")
                return
            temp_dir = args.data_dir
            print(f"Skipping download, using existing data in {temp_dir}")
        else:
            temp_dir = download_observations(args.data_dir)

        # Check if we have any observation files
        files = glob.glob(f"{temp_dir}/*{YEAR}*.csv")
        if not files:
            print(f"Warning: No observation files found for year {YEAR}")
            print(f"Directory: {temp_dir}")
            if input("Continue anyway? (y/n): ").lower() != 'y':
                return
        else:
            print(f"Found {len(files)} observation files for year {YEAR}")

        # Step 2: Extract unique coordinates
        coordinates = extract_coordinates(temp_dir)

        # Step 3: Update coordinates file
        update_coordinates_file(coordinates)

        # Output location of data directory for future runs
        if not args.skip_download and not args.data_dir:
            print(f"\nTo reuse these files in future runs, use:")
            print(f"python update_coordinates.py --skip-download --data-dir {temp_dir} --year {YEAR}")

        print("Coordinate update completed successfully")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()