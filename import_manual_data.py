"""
import_manual_data.py - create data files from old data that has been entered into csv files

The Cooper's Hawk in the City Survey used paper forms to collect all data prior to 2023.

It would be convenient to be able to upload that data to google cloud storage.

It's a lot of work to create individual files for each observation.  This script supports a somewhat simpler process:
- enter data into a properly formatted spreadsheet
- export the data as a csv file
- run this script to generate the csv files for individual observations
- upload the generated files to the cloud storage bucket

The first row of the input CSV file must be the following:
quadrat,date,observers,station,latitude,longitude,start_time,cloud,wind,noise,detection,detection_type,age,distance,direction,notes

Field order isn't important, but capitalization and spelling is.  Subsequent rows must contain the appropriate
data for each column.

The expected date format is DD/MM/YYYY
The expected time format is HH:MM
"""

import re
import datetime
import csv

FORM_FIELD_NAMES = [
    "quadrat", "station",
    "cloud", "wind", "noise", "latitude", "longitude",
    "detection", "direction", "distance", "detection_type", "age_class",
    "observers", "notes"
]
FILE_FIELD_NAMES = FORM_FIELD_NAMES.copy()
FILE_FIELD_NAMES.append("timestamp")
OPTIONAL_FIELDS = ["direction", "distance", "detection_type", "age_class"]

if __name__ == '__main__':
    #  Get the input file name
    # TODO: get the input file name from the command line
    input_filename = "2022-E-F.csv"

    # import the data
    data = []
    with open(input_filename, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(dict(row))

    # construct the timestamp field from the date and start_time fields
    p = re.compile("\d\d")
    for row in data:
        o_date = row["date"]
        start_time = row["start_time"]
        timestamp = "{} {}".format(o_date, start_time)
        try:
            timestamp = datetime.datetime.strptime(timestamp, "%d/%m/%Y %H:%M").strftime("%Y-%m-%d.%H-%M-00")
        except Exception:
            print("ERROR: bad time or date value in row: {}".format(str(row)))
        row["timestamp"] = timestamp

    pass

    # TODO: validate the data

    # write the output files
    for row in data:
        filename = "{}.{:02d}.{}.csv".format(row['quadrat'], int(row['station']), row["timestamp"])
        with open(filename, "w") as f:
            try:
                writer = csv.DictWriter(f, fieldnames=FILE_FIELD_NAMES, extrasaction="ignore")
                writer.writeheader()
                writer.writerow(row)
            except Exception as e:
                print("Error writing file for row {}".format(str(row)))



    pass