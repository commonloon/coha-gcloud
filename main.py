import string
import re
import datetime
import csv
from google.cloud import storage

from flask import Flask
from flask import render_template, request

app = Flask(__name__, template_folder="templates")

unselected: str = "Choose"
quadrats = list(string.ascii_uppercase)[:24]   # 24 Quadrats named A-X
stations = [str(i) for i in range(1, 17, 1)]   # 16 stations in each quadrat, numbered 1-16
quadrats.insert(0, unselected)
stations.insert(0, unselected)

def csvWriteToGoogleCloud(filename, columns, data):
    """
    Write a CSV file from an array of dicts (each array element is a dict with the relevant columnts)
    columns: list of column names in the order you would like them written
    data: array of dicts to write
    """
    data_bucket_name = "coha-data"
    storage_client = storage.Client()
    bucket_name = "coha-data"
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
    msg = "Select Station and conditions before starting the survey"
    return render_template('coha-ui.html',
                           email=email, quadrat=quadrat, message=msg,
                           quadrats=quadrats, stations=stations)


@app.route('/save/', methods=['GET', 'POST'])
def save_data():
    '''
    handle the submitted data for a single station
    :return:
    '''
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d.%H-%M-%S")
    form = request.form
    # Get the email address and quadrat from a cookie, if available
    (email, quadrat) = getCookieData()

    # get the form data
    fieldNames = [
        "quadrat", "station",
        "cloud", "wind", "noise", "latitude", "longitude",
        "detection", "direction", "distance",
        "email"
    ]
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

    # save the data file
    filename = "{}.{:02d}.{}.csv".format(fields['quadrat'], int(fields['station']), timestamp)
    msg = csvWriteToGoogleCloud(filename, csvColumns, fields)
    return render_template('coha-ui.html',
                           email=email, quadrat=quadrat, message=msg,
                           quadrats=quadrats, stations=stations)

if __name__ == '__main__':
    app.run()
