import string
import re
import datetime
import pytz
import csv
import html
import simplejson as json
from google.cloud import storage

from flask import Flask
from flask import render_template, request

STORAGE_BUCKET_NAME= "coha-data"
FIELD_NAMES = [
    "quadrat", "station",
    "cloud", "wind", "noise", "latitude", "longitude",
    "detection", "direction", "distance",
    "email", "notes"
]


app = Flask(__name__, template_folder="templates")

unselected: str = "not selected"
quadrats = list(string.ascii_uppercase)[:24]   # 24 Quadrats named A-X
stations = [str(i) for i in range(1, 17, 1)]   # 16 stations in each quadrat, numbered 1-16
cloudValues = [str(i) for i in range(0, 5, 1)] # valid values are 0-4
windValues  = [str(i) for i in range(0, 5, 1)] # valid values are 0-4
noiseValues = [str(i) for i in range(0, 4, 1)] # valid values are 0-3
quadrats.insert(0, unselected)
stations.insert(0, unselected)


def csvWriteToGoogleCloud(filename, columns, data):
    """
    Write a CSV file from an array of dicts (each array element is a dict with the relevant columnts)
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

    # files are basically all blobs in the google cloud
    blob = bucket.blob(filename)
    try:
        with blob.open('w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            writer.writerow(data)
        msg = "saved data to file {}".format(filename)
    except Exception as e:
        msg = "Failed to save data"

    return msg

def getDataFiles(year=2023):
    """
    Read all the data files for the specified year and return an array of dicts whose keys are the field names

    """
    data = []
    storage_client = storage.Client()
    bucket_name = STORAGE_BUCKET_NAME
    # first try to read from an existing bucket
    bucket = storage_client.get_bucket(bucket_name)

    if bucket is None:
        #TODO: display error page on failure
        return "Failed to open data bucket " + STORAGE_BUCKET_NAME + ", sorry"

    # check all blobs in the bucket, adding those from this year to the list
    year = str(year)  # need the year as a string
    pattern = "[A-X]\.[0-9][0-9]\." + year
    names = []
    for blob in storage_client.list_blobs(STORAGE_BUCKET_NAME):
        name = blob.name
        if re.match(pattern, name):
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



def loadStationCoords():
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


def isValidEmailFormat(s):
    s = s.strip();
    pat = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}$'
    return re.match(pat, s) is not None

def getCookieData():
    defaultEmail = ""
    defaultQuadrat = "Choose"
    email = request.cookies.get('email')
    quadrat = request.cookies.get('quadrat')
    email = "" if email is None else email
    email = email if isValidEmailFormat(email) else defaultEmail
    quadrat = "Choose" if quadrat is None else quadrat
    quadrat = quadrat if quadrat in quadrats else defaultQuadrat
    return (email, quadrat)

@app.route('/')
def collect_data():  # put application's code here
    (email, quadrat) = getCookieData()
    # We have to use different font sizes for iPhone and Android, due to how they handle scaling.
    # Figure out the platform from the user-agent header.
    agent = str(request.headers.get("user-agent"))
    iphone = re.search('iPhone', agent) is not None

    msg = "Select Station and conditions before starting the survey."
    return render_template('coha-ui.html',
                           email=email, quadrat=quadrat, message=msg, iphone=iphone,
                           quadrats=quadrats, stations=stations, coords=loadStationCoords())


@app.route('/save/', methods=['GET', 'POST'])
def save_data():
    '''
    handle the submitted data for a single station
    :return:
    '''
    timestamp = datetime.datetime.now(tz=pytz.timezone("Canada/Pacific")).strftime("%Y-%m-%d.%H-%M-%S")
    form = request.form
    # Get the email address and quadrat from a cookie, if available
    (email, quadrat) = getCookieData()

    # get the form data
    fieldNames = FIELD_NAMES
    csvColumns = fieldNames.copy()
    csvColumns.append("timestamp")
    fields = {"timestamp": timestamp}
    msg = ""
    for field in fieldNames:
        try:
            fields[field] = request.form[field]
            msg += " " + field + "=\"" + str(fields[field])
        except Exception as e:
            fields[field] = ""
            msg += " Missing value for field:" + field
            pass

    # sanitize the data, so the site is harder to exploit by bad actors
    bad = "bad value"
    fields["email"] = fields["email"][:40] if isValidEmailFormat(fields["email"]) else html.escape(fields["email"])[:20]
    fields["quadrat"] = fields["quadrat"] if fields["quadrat"] in quadrats else bad
    fields["station"] = fields["station"] if fields["station"] in stations  else bad
    fields["cloud"] = fields["cloud"] if fields["cloud"] in cloudValues else bad
    fields["wind"] = fields["wind"] if fields["wind"] in windValues else bad
    fields["noise"] = fields["noise"] if fields["noise"] in noiseValues else bad
    fields["notes"] = html.escape(fields["notes"])[:2048]
    fields["latitude"] = str(float(fields["latitude"]))[:15]
    fields["longitude"] = str(float(fields["longitude"]))[:15]
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

    # save the data file
    filename = "{}.{:02d}.{}.csv".format(fields['quadrat'], int(fields['station']), timestamp)

    # We have to use different font sizes for iPhone and Android, due to how they handle scaling.
    # Figure out the platform from the user-agent header.
    agent = str(request.headers.get("user-agent"))
    iphone = re.search('iPhone', agent) is not None

    msg = csvWriteToGoogleCloud(filename, csvColumns, fields)
    return render_template('coha-ui.html',
                           email=email, quadrat=quadrat, message=msg, iphone=iphone,
                           quadrats=quadrats, stations=stations, coords=loadStationCoords())


@app.route('/map/')
def show_map():
    """
    Display a map of the datapoints received for the most recent year
    """
    # Get the current year
    year = datetime.date.today().year

    # look for files matching the current year.  If none found, look for previous year
    data = getDataFiles(year)

    # Build a structure to pass to the web template.  The template will handle all the map stuff.
    return render_template('coha-map.html', data=data, year=year)



if __name__ == '__main__':
    app.run()
