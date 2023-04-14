import string
import re
import datetime
import pytz
import csv
import html
import os
from google.cloud import storage

from flask import Flask
from flask import render_template, request, redirect
from flaskext.markdown import Markdown

MAPS_API_KEY = os.environ.get("COHA_MAPS_API_KEY")

STORAGE_BUCKET_NAME = "coha-data"
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
DATA_FILE_NAME_PATTERN = "[A-X]\\.([0-9]){2}\\.([0-9]{4})-[0-1][0-9]-[0-3][0-9]\\.[0-6][0-9]-[0-6][0-9]-[0-6][0-9]\\.csv"

SURVEY_BOUNDS = {
    "west": -123.157770,
    "north": 49.263912,
    "south": 49.209423,
    "east": -122.937837
}

app = Flask(__name__, template_folder="templates", static_folder='static', static_url_path='')
Markdown(app)

unselected: str = "not selected"
quadrats = list(string.ascii_uppercase)[:24]    # 24 Quadrats named A-X
stations = [str(i) for i in range(1, 17, 1)]    # 16 stations in each quadrat, numbered 1-16
cloudValues = [str(i) for i in range(0, 5, 1)]  # valid values are 0-4
windValues  = [str(i) for i in range(0, 5, 1)]  # valid values are 0-4
noiseValues = [str(i) for i in range(0, 4, 1)]  # valid values are 0-3
quadrats.insert(0, unselected)
stations.insert(0, unselected)


def csv_write_to_google_cloud(filename, columns, data):
    """
    Write a CSV file from an array of dicts (each array element is a dict with the relevant columns)
    columns: list of column names in the order you would like them written
    data: array of dicts to write
    """
    storage_client = storage.Client()
    bucket_name = STORAGE_BUCKET_NAME
    try:
        # first try to read from an existing bucket
        bucket = storage_client.get_bucket(bucket_name)
    except Exception as e:
        bucket = None

    if bucket is None:
        # try creating the bucket if the read failed.
        # TODO: use a more elegant check for bucket existence
        try:
            bucket = storage_client.create_bucket(bucket_name)
        except Exception as e:
            return "Failed to create bucket to save data.  Data NOT saved, sorry"

    # files are all blobs in the google cloud
    blob = bucket.blob(filename)
    blob.cache_control = "max-age=0,no-store"  # disable caching so clients can read immediately after update
    try:
        with blob.open('w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        msg = "saved data to file {}".format(filename)
    except Exception as e:
        msg = "Failed to save data"

    return msg


def is_there_new_data():
    """
    Returns true if any object in the bucket has a newer timestamp than SUMMARY_FILE_NAME
    """
    storage_client = storage.Client()
    bucket_name = STORAGE_BUCKET_NAME
    # first try to read from an existing bucket
    bucket = storage_client.get_bucket(bucket_name)

    if bucket is None:
        # TODO: display error page on failure
        return "Failed to open data bucket " + STORAGE_BUCKET_NAME + ", sorry"

    # check all blobs in the bucket, adding those from this year to the list
    blob_list = storage_client.list_blobs(STORAGE_BUCKET_NAME)
    reference_time = None
    last_data_update_time = None
    for blob in blob_list:
        m = re.match(DATA_FILE_NAME_PATTERN, blob.name)
        if m:
            if last_data_update_time is None or blob.updated > last_data_update_time:
                last_data_update_time = blob.updated
        elif blob.name == SUMMARY_FILE_NAME:
            reference_time = blob.updated

    is_new = False
    if last_data_update_time is not None and (reference_time is None or reference_time < last_data_update_time):
        is_new = True
    return is_new


def regenerate_data_summaries():
    """
    Recreate all the data summary CSV files
    """
    # gather all the data
    data = get_data()

    yearly_data = parse_data_by_year(data)

    # create the summary data file
    csv_write_to_google_cloud(SUMMARY_FILE_NAME, FILE_FIELD_NAMES, data)

    # now write summary files for all years
    # TODO: this is inefficient.  We should only update the file for years with new data
    yearly_summaries = {}
    for year in yearly_data.keys():
        year_file_name = "COHA-data-" + str(year) + ".csv"
        yearly_summaries[year] = STORAGE_BUCKET_PUBLIC_URL + "/" + year_file_name
        csv_write_to_google_cloud(year_file_name, FILE_FIELD_NAMES, yearly_data[year])

    return data, yearly_data


def regenerate_current_year():
    """
    Recreate all the data summary CSV files
    """
    year = datetime.datetime.now().year

    # gather all the data
    current_data = get_data(year)

    # read the summary file to get data for other years
    summary_data = get_summary_data(SUMMARY_FILE_NAME)

    yearly_data = parse_data_by_year(summary_data)
    yearly_data[str(year)] = current_data

    # now rebuild the complete data set with the updated current year
    data = []
    for y in sorted(yearly_data.keys()):
        data += yearly_data[y]

    # create the summary data file
    csv_write_to_google_cloud(SUMMARY_FILE_NAME, FILE_FIELD_NAMES, data)

    # now write a new summary file the current year
    year_file_name = "COHA-data-" + str(year) + ".csv"
    csv_write_to_google_cloud(year_file_name, FILE_FIELD_NAMES, current_data)

    return data, yearly_data


def parse_data_by_year(data):
    """
    Returns the data broken out by year
    """
    # compile lists of the data from each year, so we can save year files
    yearly_data = {}
    for i in range(0, len(data)):
        year = data[i]["timestamp"][0:4]
        if year in yearly_data:
            yearly_data[year].append(data[i])
        else:
            yearly_data[year] = [data[i]]
    return yearly_data


def get_data(year=None):
    """
    Read all the data files for the specified year and return an array of dicts whose keys are the field names

    """
    data = []
    storage_client = storage.Client()
    bucket_name = STORAGE_BUCKET_NAME
    # first try to read from an existing bucket
    bucket = storage_client.get_bucket(bucket_name)

    if bucket is None:
        # TODO: display error page on failure
        return "Failed to open data bucket " + STORAGE_BUCKET_NAME + ", sorry"

    # check all blobs in the bucket, adding those from this year to the list
    year = year  # need the year as a string
    year_pattern = "[A-X][.][0-9][0-9][.]" + str(year)
    names = []
    for blob in storage_client.list_blobs(STORAGE_BUCKET_NAME):
        name = blob.name
        # only process appropriately named files.  Who knows what else we'll stick in the bucket later
        if re.match(DATA_FILE_NAME_PATTERN, name):
            # if a year is selected, only choose matching files
            if year is not None:
                # get data for the selected year
                if re.match(year_pattern, name):
                    names.append(name)
            else:
                # otherwise return all the data
                names.append(name)

    for name in names:
        blob = bucket.blob(name)
        try:
            with blob.open("r") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    data.append(dict(row))
        except Exception as e:
            pass  # silently skip files we can't open
    return data


def get_summary_data(summary_file=SUMMARY_FILE_NAME):
    """
    Get data from a summary file.
    This should be faster than having to read all observation files.
    """
    data = []
    storage_client = storage.Client()
    bucket_name = STORAGE_BUCKET_NAME
    # first try to read from an existing bucket
    bucket = storage_client.get_bucket(bucket_name)

    if bucket is None:
        # TODO: display error page on failure
        return data
    try:
        with bucket.blob(summary_file).open("r") as blob:
            reader = csv.DictReader(blob)
            for row in reader:
                data.append(dict(row))
    except Exception as e:
        pass

    return data


def load_station_coords():
    """
    Load prior station coordinates so we can sanity check the new station location
    """
    coords = {}
    with open("static/COHA-Station-Coordinates-v1.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            (quadrat, station, latitude, longitude, year) = \
                (row["Quadrat"], row["Station"], row["latitude"], row["longitude"], row["year taken"])
            if quadrat not in coords:
                coords[quadrat] = {}
            if station not in coords[quadrat]:
                coords[quadrat][station] = {}
            coords[quadrat][station] = {"latitude": latitude, "longitude": longitude, "year": year}
    return coords


def sanitize_text_input(untrusted, max_len=100):
    """
    This function attempts to render text input harmless by doing the following:
    - strip characters other than letters and harmless punctuation
    - limiting the string length
    """
    pattern = "[^A-Za-z.,:; ']"
    sanitized = re.sub(pattern, "", untrusted)
    sanitized = sanitized[:max_len] if len(sanitized) > max_len else sanitized
    return sanitized


def get_cookie_data():
    default_quadrat = "Choose"
    observers = request.cookies.get('observers')
    quadrat = request.cookies.get('quadrat')

    observers = "" if observers is None else sanitize_text_input(observers)
    quadrat = "Choose" if quadrat is None else quadrat
    quadrat = quadrat if quadrat in quadrats else default_quadrat
    return observers, quadrat


def is_iphone():
    """
    look for iPhone in the user-agent field of the HTTP request
    """
    agent = str(request.headers.get("user-agent"))
    return re.search('iPhone', agent) is not None


@app.route('/')
def collect_data():  # put application's code here
    (observers, quadrat) = get_cookie_data()
    # We have to use different font sizes for iPhone and Android, due to how they handle scaling.
    # Figure out the platform from the user-agent header.
    iphone = is_iphone()

    msg = "Select Station and conditions before starting the survey."
    return render_template('coha-ui.html',
                           observers=observers, quadrat=quadrat, message=msg, iphone=iphone,
                           quadrats=quadrats, stations=stations, coords=load_station_coords(),
                           maps_api_key=MAPS_API_KEY)


@app.route('/save/', methods=['GET', 'POST'])
def save_data():
    """
    handle the submitted data for a single station
    :return:
    """
    ok_to_save = True
    bad = "bad value"
    timestamp = datetime.datetime.now(tz=pytz.timezone("Canada/Pacific")).strftime("%Y-%m-%d.%H-%M-%S")
    form = request.form
    # Get the observers address and quadrat from a cookie, if available
    (observers, quadrat) = get_cookie_data()

    # get the form data
    fieldNames = FORM_FIELD_NAMES
    csvColumns = FILE_FIELD_NAMES
    fields = {"timestamp": timestamp}
    msg = ""
    for field in fieldNames:
        try:
            fields[field] = request.form[field]
            msg += " " + field + "=\"" + str(fields[field])
        except Exception as e:
            fields[field] = ""
            if field not in OPTIONAL_FIELDS:
                msg += " Missing value for field:" + field + ".  "

    # no point saving if we don't have location data
    latitude = fields["latitude"]
    longitude = fields["longitude"]
    errmsg = "ERROR: Failed to save observation.   "
    if latitude == "":
        errmsg += "Latitude must have a value.  "
        fields["latitude"] = bad
    else:
        try:
            latitude = float(latitude)
            if (latitude < (SURVEY_BOUNDS["south"] - 0.1)) or latitude > (SURVEY_BOUNDS["north"]+0.1):
                ok_to_save = False
                errmsg += "latitude out of bounds.  "
                fields["latitude"] = bad
            else:
                fields["latitude"] = str(latitude)  # yay, we have a good value!
        except Exception as e:
            ok_to_save = False
            fields["latitude"] = bad
            errmsg += "invalid value for latitude.  "
    if longitude == "":
        errmsg += "Longitude must have a value.  "
        fields["longitude"] = bad
    else:
        try:
            longitude = float(longitude)
            if (longitude < (SURVEY_BOUNDS["west"] - 0.1)) or longitude > (SURVEY_BOUNDS["east"]+0.1):
                ok_to_save = False
                fields["longitude"] = bad
                errmsg += "latitude out of bounds.  "
            else:
                fields["longitude"] = str(longitude)  # yay, we have a good value!
        except Exception as e:
            ok_to_save = False
            fields["longitude"] = bad
            errmsg += "invalid value for longitude."

    # sanitize the data, so the site is harder to exploit by bad actors
    fields["observers"] = sanitize_text_input(fields["observers"])
    fields["quadrat"] = fields["quadrat"] if fields["quadrat"] in quadrats else bad
    fields["station"] = fields["station"] if fields["station"] in stations else bad
    fields["cloud"] = fields["cloud"] if fields["cloud"] in cloudValues else bad
    fields["wind"] = fields["wind"] if fields["wind"] in windValues else bad
    fields["noise"] = fields["noise"] if fields["noise"] in noiseValues else bad
    fields["notes"] = html.escape(fields["notes"])[:2048]
    fields["detection"] = fields["detection"] if fields["detection"] in ["no", "yes"] else bad
    if "direction" in fields.keys() and fields["direction"] != "":
        fields["direction"] = re.sub("[^0-9]", "", fields["direction"])  # strip non-digits
        fields["direction"] = str(int(fields["direction"]))[:4]
    else:
        fields["direction"] = ""
    if "distance" in fields.keys() and fields["distance"] != "":
        fields["distance"] = re.sub("[^0-9]", "", fields["distance"])  # strip non-digits
        fields["distance"] = str(int(fields["distance"]))[:4]
    else:
        fields["distance"] = ""
    fields["detection_type"] = fields["detection_type"] if fields["detection_type"] in ["A", "V"] else ""
    fields["age_class"] = fields["age_class"] if fields["age_class"] in ["unknown", "juvenile", "adult"] else ""

    for field in FORM_FIELD_NAMES:
        if fields[field] == bad:
            ok_to_save = False
            break

    if ok_to_save:
        # save the data file
        filename = "{}.{:02d}.{}.csv".format(fields['quadrat'], int(fields['station']), timestamp)
        msg = csv_write_to_google_cloud(filename, csvColumns, [fields])
    else:
        msg = errmsg + msg

    # We have to use different font sizes for iPhone and Android, due to how they handle scaling.
    # Figure out the platform from the user-agent header.
    iphone = is_iphone()

    return render_template('coha-ui.html',
                           observers=observers, quadrat=quadrat, message=msg, iphone=iphone,
                           quadrats=quadrats, stations=stations, coords=load_station_coords(),
                           maps_api_key=MAPS_API_KEY)


@app.route('/map-regen-all/')
def show_map_regen_all():
    """
    Display a map of the datapoints received for the most recent year.
    Regenerate maps and summary files for all years if any data point is newer than the summary file.
    """
    # regenerate data files if needed
    need_regen = is_there_new_data()
    if need_regen:
        data, yearly_data = regenerate_data_summaries()
    else:
        data = get_summary_data()
        yearly_data = parse_data_by_year(data)

    # Get the current year
    year = datetime.date.today().year

    # look for files matching the current year.  If none found, look for previous year
    years = sorted(yearly_data.keys())
    if year in years:
        year = years[:-1]

    # Build a structure to pass to the web template.  The template will handle all the map stuff.
    return render_template('coha-map.html', yearly_data=yearly_data, year=year, years=years, maps_api_key=MAPS_API_KEY)


@app.route('/map/')
def show_map():
    """
    Display a map of the datapoints received for the most recent year.

    If a data point is newer than the summary file, first regenerate the data for the current year.
    """
    # regenerate data files if needed
    need_regen = is_there_new_data()
    if need_regen:
        data, yearly_data = regenerate_current_year()
    else:
        data = get_summary_data()
        yearly_data = parse_data_by_year(data)

    # Get the current year
    year = datetime.date.today().year

    # look for files matching the current year.  If none found, look for previous year
    years = sorted(yearly_data.keys())
    if year in years:
        year = years[:-1]

    # Build a structure to pass to the web template.  The template will handle all the map stuff.
    return render_template('coha-map.html', yearly_data=yearly_data, year=year, years=years, maps_api_key=MAPS_API_KEY)


@app.route('/data/')
def csv_data():
    """
    Return all the data as a csv file
    """
    # update the summary files if there is new data
    if is_there_new_data():
        (data, yearly_data) = regenerate_data_summaries()
    else:
        data = get_summary_data()
        yearly_data = parse_data_by_year(data)

    years = sorted(yearly_data.keys())
    yearly_summaries = {}
    for year in yearly_data.keys():
        year_file_name = "COHA-data-" + str(year) + ".csv"
        yearly_summaries[year] = STORAGE_BUCKET_PUBLIC_URL + "/" + year_file_name

    # return a redirect to the google cloud storage URL
    return render_template("coha-download.html",
                           all_years=SUMMARY_FILE_PUBLIC_URL,
                           years=years,
                           yearly_summaries=yearly_summaries)


@app.route('/helpmd/')
def show_help_md():
    """
    Serve the README.md file as HTML.

    NOTE: this  endpoint only works when deployed, not on the local test server
    TODO: make this work on the local test server.
    """
    # Dockerfile copies README.md into the correct location on deployment.
    # This is awkward, but we need the README.md file to be in the root directory for github
    # and we don't want to maintain two copies.  I could try adding a symlink in my local workspace, but
    # that would have to be repeated whenever the repo is cloned to a new machine and won't work on Windows.
    with open("static/HELP.md", "r") as f:
        mkd_text = f.read()
    return render_template('help.html', mkd_text=mkd_text)

@app.route('/help/')
def show_help():
    """
    Serve the help file from GitHub

    The Markdown version wasn't rendering correctly from Flask, hence this kludge to just link
    to the page on GitHub, which renders the markdown correctly.
    """
    return redirect('https://github.com/commonloon/coha-gcloud/blob/main/static/HELP.md')


if __name__ == '__main__':
    app.run()
