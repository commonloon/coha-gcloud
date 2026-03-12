import string
import re
import datetime
import pytz
import csv
import html
import io
import os
from functools import wraps
from google.cloud import storage
from google.api_core.exceptions import PreconditionFailed

from flask import Flask, jsonify, render_template, request, redirect, Response
import markdown

MAPS_API_KEY = os.environ.get("COHA_MAPS_API_KEY")
MAP_ID = os.environ.get("COHA_GOOGLE_MAP_ID")
ADMIN_PASSWORD = os.environ.get("COHA_ADMIN_PASSWORD", "")

STORAGE_BUCKET_NAME = os.environ.get("COHA_BUCKET_NAME", "coha-data")
STORAGE_BUCKET_PUBLIC_URL = "https://storage.googleapis.com/" + STORAGE_BUCKET_NAME
FORM_FIELD_NAMES = [
    "quadrat", "station",
    "cloud", "wind", "noise", "latitude", "longitude",
    "detection", "direction", "distance", "detection_type", "age_class",
    "observers", "notes"
]
FILE_FIELD_NAMES = FORM_FIELD_NAMES.copy()
FILE_FIELD_NAMES.append("timestamp")
OPTIONAL_FIELDS = ["direction", "distance", "detection_type", "age_class"]

SUMMARY_FILE_NAME = "COHA-data-all-years.csv"
SUMMARY_FILE_PUBLIC_URL = STORAGE_BUCKET_PUBLIC_URL + "/" + SUMMARY_FILE_NAME

# Pre-compiled once; used in every blob-listing call
DATA_FILE_NAME_PATTERN = r"[A-X]\.([0-9]){2}\.([0-9]{4})-[0-1][0-9]-[0-3][0-9]\.[0-6][0-9]-[0-6][0-9]-[0-6][0-9]\.csv"
_DATA_FILE_RE = re.compile(DATA_FILE_NAME_PATTERN)

SURVEY_BOUNDS = {
    "west": -123.157770,
    "north": 49.263912,
    "south": 49.209423,
    "east": -122.937837
}

MARKDOWN_EXTENSIONS = [
    'markdown.extensions.extra',
    'markdown.extensions.codehilite',
    'markdown.extensions.toc',
    'markdown.extensions.tables',
    'markdown.extensions.fenced_code',
]

app = Flask(__name__, template_folder="templates", static_folder='static', static_url_path='')

unselected: str = "not selected"
quadrats = list(string.ascii_uppercase)[:24]    # 24 quadrats named A-X
stations = [str(i) for i in range(1, 17)]       # 16 stations per quadrat
cloudValues = [str(i) for i in range(0, 5)]
windValues  = [str(i) for i in range(0, 5)]
noiseValues = [str(i) for i in range(0, 4)]
quadrats.insert(0, unselected)
stations.insert(0, unselected)

GCP_PROJECT_ID = os.environ.get("COHA_GCP_PROJECT_ID")

# Module-level storage client — created once per instance to avoid repeated auth overhead
_storage_client = None

def get_storage_client():
    global _storage_client
    if _storage_client is None:
        try:
            if GCP_PROJECT_ID:
                _storage_client = storage.Client(project=GCP_PROJECT_ID)
            else:
                _storage_client = storage.Client()
        except Exception as e:
            print(f"Error creating storage client: {e}")
            _storage_client = storage.Client.create_anonymous_client()
    return _storage_client


def get_bucket():
    return get_storage_client().bucket(STORAGE_BUCKET_NAME)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _csv_to_string(columns, rows):
    """Serialise a list of dicts to a CSV string with a header row."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _year_from_filename(name):
    """Extract the 4-digit year from an observation filename (Q.SS.YYYY-...)."""
    return name[5:9]


def _iter_observation_blobs(year=None):
    """
    Yield GCS blob objects whose names match the observation file pattern.
    If year is given, only blobs for that year are yielded.
    """
    year_str = str(year) if year is not None else None
    for blob in get_storage_client().list_blobs(STORAGE_BUCKET_NAME):
        if not _DATA_FILE_RE.match(blob.name):
            continue
        if year_str is not None and _year_from_filename(blob.name) != year_str:
            continue
        yield blob


# ---------------------------------------------------------------------------
# GCS read/write
# ---------------------------------------------------------------------------

def csv_write_to_google_cloud(filename, columns, data):
    """
    Unconditionally write a CSV to GCS (used by full regeneration).
    Returns (success: bool, message: str).
    """
    blob = get_bucket().blob(filename)
    blob.cache_control = "max-age=0,no-store"
    try:
        blob.upload_from_string(_csv_to_string(columns, data), content_type="text/csv")
        return True, f"saved data to file {filename}"
    except Exception as e:
        return False, f"Failed to save data: {e}"


def remove_from_summary_file(blob_name, timestamp, max_retries=3):
    """
    Remove all rows matching timestamp from a summary CSV using generation-match.

    Matching on timestamp is sufficient: each individual file has one row whose
    timestamp value equals the timestamp encoded in its filename.  If two files
    somehow share the same timestamp (manual imports, etc.) all matching rows are
    removed — correct behaviour since the source file no longer exists.

    Returns (success: bool, message: str).
    """
    blob = get_bucket().blob(blob_name)
    blob.cache_control = "max-age=0,no-store"

    for attempt in range(max_retries):
        try:
            content = blob.download_as_text()
            generation = blob.generation
            rows = list(csv.DictReader(io.StringIO(content)))
        except Exception:
            return True, f"{blob_name} not found — nothing to remove"

        filtered = [r for r in rows if r.get("timestamp") != timestamp]
        removed = len(rows) - len(filtered)

        try:
            blob.upload_from_string(
                _csv_to_string(FILE_FIELD_NAMES, filtered),
                content_type="text/csv",
                if_generation_match=generation
            )
            return True, f"Removed {removed} row(s) from {blob_name}"
        except PreconditionFailed:
            continue
        except Exception as e:
            return False, f"Failed to update {blob_name}: {e}"

    return False, f"Gave up updating {blob_name} after {max_retries} retries"


def append_to_summary_file(blob_name, new_row, max_retries=3):
    """
    Append a row to a summary CSV using GCS generation-match for concurrency safety.

    If two Cloud Run instances try to update the summary simultaneously, the
    generation-match precondition causes one write to fail. The loser retries,
    re-reading the (now updated) file so neither observation is lost.

    Returns (success: bool, message: str).
    """
    blob = get_bucket().blob(blob_name)
    blob.cache_control = "max-age=0,no-store"

    for attempt in range(max_retries):
        try:
            content = blob.download_as_text()
            generation = blob.generation
            rows = list(csv.DictReader(io.StringIO(content)))
        except Exception:
            # File does not exist yet; generation=0 means "write only if absent"
            rows = []
            generation = 0

        rows.append(new_row)

        try:
            blob.upload_from_string(
                _csv_to_string(FILE_FIELD_NAMES, rows),
                content_type="text/csv",
                if_generation_match=generation
            )
            return True, f"Updated {blob_name}"
        except PreconditionFailed:
            # Another instance wrote first — retry with fresh read
            continue
        except Exception as e:
            return False, f"Failed to update {blob_name}: {e}"

    # All retries exhausted. The individual observation file was already saved
    # safely; a future admin regen will bring the summary back in sync.
    print(f"Warning: gave up updating {blob_name} after {max_retries} retries")
    return False, f"Summary update for {blob_name} deferred — individual file saved safely"


def regenerate_data_summaries():
    """
    Full regeneration: read every individual observation file and rebuild all
    summary CSVs. Slow but always correct; called only from the admin endpoint
    and as a cold-start fallback.
    """
    data = get_data()
    yearly_data = parse_data_by_year(data)

    # All-years summary sorted by year, then by quadrat/station/timestamp within each year
    # (within-year order comes from list_blobs, which is lexicographic by blob name)
    data_sorted = []
    for year in sorted(yearly_data.keys()):
        data_sorted.extend(yearly_data[year])

    csv_write_to_google_cloud(SUMMARY_FILE_NAME, FILE_FIELD_NAMES, data_sorted)
    for year, rows in yearly_data.items():
        csv_write_to_google_cloud(f"COHA-data-{year}.csv", FILE_FIELD_NAMES, rows)

    return data_sorted, yearly_data


def parse_data_by_year(data):
    """Group a list of observation dicts by year string."""
    yearly_data = {}
    for row in data:
        year = row["timestamp"][0:4]
        yearly_data.setdefault(year, []).append(row)
    return yearly_data


def get_data(year=None):
    """
    Read individual observation files for the given year (or all years).
    Uses blob objects from list_blobs directly — no redundant API calls.
    """
    data = []
    for blob in _iter_observation_blobs(year):
        try:
            content = blob.download_as_text()
            for row in csv.DictReader(io.StringIO(content)):
                data.append(dict(row))
        except Exception as e:
            print(f"Skipping {blob.name}: {e}")
    return data


def get_summary_data(summary_file=SUMMARY_FILE_NAME):
    """Read data from a summary CSV. Returns empty list if the file is absent."""
    data = []
    try:
        content = get_bucket().blob(summary_file).download_as_text()
        for row in csv.DictReader(io.StringIO(content)):
            data.append(dict(row))
    except Exception as e:
        print(f"Could not read {summary_file}: {e}")
    return data


def load_station_coords():
    coords = {}
    with open("static/COHA-Station-Coordinates-v1.csv", "r") as f:
        for row in csv.DictReader(f):
            q, s = row["Quadrat"], row["Station"]
            coords.setdefault(q, {})[s] = {
                "latitude":  row["latitude"],
                "longitude": row["longitude"],
                "year":      row["year taken"]
            }
    return coords


def sanitize_text_input(untrusted, max_len=100):
    sanitized = re.sub(r"[^A-Za-z.,:; ']", "", untrusted)
    return sanitized[:max_len]


def get_cookie_data():
    observers = sanitize_text_input(request.cookies.get('observers', ''))
    quadrat   = request.cookies.get('quadrat', 'Choose')
    quadrat   = quadrat if quadrat in quadrats else 'Choose'
    return observers, quadrat


def is_iphone():
    return re.search('iPhone', str(request.headers.get("user-agent"))) is not None


def requires_admin(f):
    """Decorator: enforce HTTP Basic Auth using the COHA_ADMIN_PASSWORD env var."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not ADMIN_PASSWORD:
            return Response(
                "Admin access not configured — set the COHA_ADMIN_PASSWORD environment variable.",
                503
            )
        auth = request.authorization
        if not auth or auth.password != ADMIN_PASSWORD:
            return Response(
                "Authentication required",
                401,
                {"WWW-Authenticate": 'Basic realm="COHA Admin"'}
            )
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Survey form
# ---------------------------------------------------------------------------

@app.route('/')
def collect_data():
    observers, quadrat = get_cookie_data()
    iphone = is_iphone()
    return render_template('coha-ui.html',
                           observers=observers, quadrat=quadrat,
                           message="Select Station and conditions before starting the survey.",
                           iphone=iphone,
                           quadrats=quadrats, stations=stations,
                           coords=load_station_coords(),
                           maps_api_key=MAPS_API_KEY,
                           map_id=MAP_ID)


@app.route('/save/', methods=['GET', 'POST'])
def save_data():
    ASCII_MAP = {k: '^' for k in range(32)}
    ok_to_save = True
    bad = "bad value"
    timestamp = datetime.datetime.now(tz=pytz.timezone("Canada/Pacific")).strftime("%Y-%m-%d.%H-%M-%S")
    observers, quadrat = get_cookie_data()

    fields = {"timestamp": timestamp}
    errmsg = "ERROR: Failed to save observation.   "
    msg = ""

    for field in FORM_FIELD_NAMES:
        try:
            fields[field] = request.form[field]
        except Exception:
            fields[field] = ""
            if field not in OPTIONAL_FIELDS:
                msg += f" Missing value for field: {field}.  "

    # Validate latitude and longitude
    for coord, lo, hi, label in [
        ("latitude",  SURVEY_BOUNDS["south"] - 0.1, SURVEY_BOUNDS["north"] + 0.1, "latitude"),
        ("longitude", SURVEY_BOUNDS["west"]  - 0.1, SURVEY_BOUNDS["east"]  + 0.1, "longitude"),
    ]:
        val = fields[coord]
        if val == "":
            ok_to_save = False
            errmsg += f"{label} must have a value.  "
            fields[coord] = bad
        else:
            try:
                fval = float(val)
                if fval < lo or fval > hi:
                    ok_to_save = False
                    errmsg += f"{label} out of bounds.  "
                    fields[coord] = bad
                else:
                    fields[coord] = str(fval)
            except Exception:
                ok_to_save = False
                errmsg += f"invalid value for {label}.  "
                fields[coord] = bad

    # Sanitize remaining fields
    fields["observers"]      = sanitize_text_input(fields["observers"])
    fields["quadrat"]        = fields["quadrat"]   if fields["quadrat"]   in quadrats    else bad
    fields["station"]        = fields["station"]   if fields["station"]   in stations    else bad
    fields["cloud"]          = fields["cloud"]     if fields["cloud"]     in cloudValues else bad
    fields["wind"]           = fields["wind"]      if fields["wind"]      in windValues  else bad
    fields["noise"]          = fields["noise"]     if fields["noise"]     in noiseValues else bad
    fields["notes"]          = html.escape(fields["notes"].translate(ASCII_MAP))[:2048]
    fields["detection"]      = fields["detection"] if fields["detection"] in ["no", "yes"] else bad
    fields["detection_type"] = fields["detection_type"] if fields["detection_type"] in ["A", "V"] else ""
    fields["age_class"]      = fields["age_class"] if fields["age_class"] in ["unknown", "juvenile", "adult"] else ""

    for key in ("direction", "distance"):
        if fields.get(key):
            fields[key] = str(int(re.sub(r"[^0-9]", "", fields[key])))[:4]
        else:
            fields[key] = ""

    if any(fields[f] == bad for f in FORM_FIELD_NAMES):
        ok_to_save = False

    if ok_to_save:
        # 1. Write the individual observation file — this is the canonical record.
        #    Each filename is unique (quadrat + station + timestamp), so there is
        #    no possibility of a write conflict here.
        filename = "{}.{:02d}.{}.csv".format(
            fields['quadrat'], int(fields['station']), timestamp
        )
        ok, msg = csv_write_to_google_cloud(filename, FILE_FIELD_NAMES, [fields])

        if ok:
            # 2. Update the summary files using generation-match conditional writes.
            #    If a concurrent save causes a collision, the loser retries so both
            #    observations end up in the summary.  If all retries fail the
            #    individual file is still safe and an admin regen will fix the summary.
            year = timestamp[:4]
            ok1, m1 = append_to_summary_file(f"COHA-data-{year}.csv", fields)
            ok2, m2 = append_to_summary_file(SUMMARY_FILE_NAME, fields)
            if not ok1 or not ok2:
                print(f"Summary update warning — {m1}; {m2}")
    else:
        msg = errmsg + msg

    iphone = is_iphone()
    return render_template('coha-ui.html',
                           observers=observers, quadrat=quadrat,
                           message=msg, iphone=iphone,
                           quadrats=quadrats, stations=stations,
                           coords=load_station_coords(),
                           maps_api_key=MAPS_API_KEY,
                           map_id=MAP_ID)


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

@app.route('/map/')
def show_map():
    """Display survey points. Reads summary file only — no individual file scans."""
    data = get_summary_data()
    if not data:
        # Summary missing (e.g. first deployment); fall back to full regeneration
        data, _ = regenerate_data_summaries()

    yearly_data = parse_data_by_year(data)
    year = datetime.date.today().year
    years = sorted(yearly_data.keys())
    if str(year) not in years and years:
        year = years[-1]

    return render_template('coha-map.html',
                           year=year,
                           years=years,
                           maps_api_key=MAPS_API_KEY,
                           map_id=MAP_ID)


@app.route('/map/data')
def map_data():
    """Return all survey data as JSON for client-side map rendering."""
    try:
        data = get_summary_data()
        return jsonify(parse_data_by_year(data))
    except Exception as e:
        print(f"Error in map_data: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Data download
# ---------------------------------------------------------------------------

@app.route('/data/')
def csv_data():
    """Display links to download the public summary CSV files."""
    data = get_summary_data()
    if not data:
        data, _ = regenerate_data_summaries()

    yearly_data = parse_data_by_year(data)
    years = sorted(yearly_data.keys())
    yearly_summaries = {
        y: f"{STORAGE_BUCKET_PUBLIC_URL}/COHA-data-{y}.csv" for y in years
    }
    return render_template("coha-download.html",
                           all_years=SUMMARY_FILE_PUBLIC_URL,
                           years=years,
                           yearly_summaries=yearly_summaries)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

_YEAR_RE = re.compile(r"^\d{4}$")


@app.route('/admin/')
@requires_admin
def admin_page():
    """
    List individual observation files for the selected year.
    Shows filenames only (fast); use /admin/view/ to inspect content.
    """
    selected_year = request.args.get('year', str(datetime.date.today().year))
    if not _YEAR_RE.match(selected_year):
        selected_year = str(datetime.date.today().year)

    op       = request.args.get('op', '')
    op_file  = request.args.get('file', '')
    op_count = request.args.get('count', '')

    filenames = []
    all_years = set()

    for blob in _iter_observation_blobs():   # no year filter — collect all_years in one pass
        file_year = _year_from_filename(blob.name)
        all_years.add(file_year)
        if file_year == selected_year:
            filenames.append(blob.name)

    filenames.sort()

    return render_template('coha-admin.html',
                           year=selected_year,
                           all_years=sorted(all_years),
                           filenames=filenames,
                           op=op,
                           op_file=op_file,
                           op_count=op_count)


@app.route('/admin/view/')
@requires_admin
def admin_view():
    """Return the raw CSV content of a single observation file as plain text."""
    filename = request.args.get('filename', '')
    if not _DATA_FILE_RE.match(filename):
        return "Invalid filename", 400
    try:
        content = get_bucket().blob(filename).download_as_text()
        return Response(content, mimetype='text/plain')
    except Exception as e:
        return f"Could not read {filename}: {e}", 500


@app.route('/admin/delete/', methods=['POST'])
@requires_admin
def admin_delete():
    """Delete an individual observation file and remove it from the summary files."""
    filename = request.form.get('filename', '')
    if not _DATA_FILE_RE.match(filename):
        return "Invalid filename", 400

    # Read the timestamp from the file before deleting so we know what to remove
    try:
        content = get_bucket().blob(filename).download_as_text()
        rows = list(csv.DictReader(io.StringIO(content)))
        timestamp = rows[0].get("timestamp", "") if rows else ""
    except Exception as e:
        return f"Could not read {filename}: {e}", 500

    try:
        get_bucket().blob(filename).delete()
    except Exception as e:
        return f"Failed to delete {filename}: {e}", 500

    # Remove the deleted row from both summary files
    year = _year_from_filename(filename)
    ok1, m1 = remove_from_summary_file(f"COHA-data-{year}.csv", timestamp)
    ok2, m2 = remove_from_summary_file(SUMMARY_FILE_NAME, timestamp)
    if not ok1 or not ok2:
        print(f"Summary update warning after delete — {m1}; {m2}")

    return redirect(f"/admin/?year={year}&op=deleted&file={filename}")


@app.route('/admin/regen/', methods=['POST'])
@requires_admin
def admin_regen():
    """Force a full regeneration of all summary files from individual observation files."""
    data, _ = regenerate_data_summaries()
    return redirect(f"/admin/?op=regenerated&count={len(data)}")


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

@app.route('/helpmd/')
def show_help_md():
    with open("static/HELP.md", 'r', encoding='utf-8') as f:
        md_content = f.read()
    html_content = markdown.markdown(md_content, extensions=MARKDOWN_EXTENSIONS)
    return render_template('help.html', mkd_text=html_content)


@app.route('/help/')
def show_help():
    return redirect('https://github.com/commonloon/coha-gcloud/blob/main/static/HELP.md')


if __name__ == '__main__':
    app.run()
