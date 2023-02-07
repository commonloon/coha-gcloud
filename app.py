import string
import re
import datetime
import csv

from flask import Flask
from flask import render_template, request

app = Flask(__name__, template_folder="templates")

unselected: str = "Choose"
quadrats = list(string.ascii_uppercase)[:24]   # 24 Quadrats named A-X
stations = [str(i) for i in range(1, 17, 1)]   # 16 stations in each quadrat, numbered 1-16
quadrats.insert(0, unselected)
stations.insert(0, unselected)

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
    msg = "Complete Station Data before starting Survey"
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
    try:
        with open(filename, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csvColumns)
            writer.writeheader()
            writer.writerow(fields)
        msg = "saved data to file {}".format(filename)
    except Exception as e:
        msg = "Failed to save data"

    return render_template('coha-ui.html',
                           email=email, quadrat=quadrat, message=msg,
                           quadrats=quadrats, stations=stations)

if __name__ == '__main__':
    app.run()
