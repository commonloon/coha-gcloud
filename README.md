# Cooper's Hawk (COHA) in the City Survey

This project implements a web app intended for use by 
participants in the annual 
[WildResearch 
Cooper's Hawk in the City survey](https://wildresearch.ca/programs/raptor-monitoring/).

The app accepts the data requested the 
[survey form](http://wildresearch.ca/wp-content/uploads/2017/03/Coopers-Hawk-in-the-City-DataForm_v2.pdf)
and saves the data to a web bucket in Google Cloud Storage.

Each observation is saved as a CSV file with a name like "G.05.2023-02-10.00-19-59.csv". 
The first letter of the filename indicates the survey quadrat, the next two digits are the station,
followed by the observation date and time in YYYY-MM-DD.HH-MM-SS format.

The content of the CSV file looks like this:

      quadrat,station,cloud,wind,noise,latitude,longitude,detection,direction,distance,detection_type,age_class,observers,notes,timestamp
      S,6,4,2,2,49.2574664,-123.0419607,yes,66,100,V,juvenile,"Harvey Dueck, Michelle Baudais",Not a real observation: created for testing,2023-02-16.16-45-07

# User Instructions
 
Instructions describing [how to use coha.pacificloon.ca to record observations](static/HELP.md) are in a separate document.

# Website Endpoints

## [coha.pacificloon.ca/](https://coha.pacificloon.ca)

This is the url survey participants use when starting their survey.  It displays the data entry form and 
provides tools for playing the COHA call.  Clicking the "Save Observation" button on this form saves the data
in Google Cloud Storage, where it can be accessed by participants and researchers.

## [coha.pacificloon.ca/save](https://coha.pacificloon.ca/save)

This is the endpoint called to save the data when the "Save Observation" button is pressed.

A message near the bottom of the displayed form indicates whether the save was successful.

After saving the data, the endpoint displays the survey form so the participant can enter data 
for the next survey station.

## [coha.pacificloon.ca/map](https://coha.pacificloon.ca/map)

This endpoint plots the stations for which data has been saved in the current year.

For stations where a COHA was observed, it plots a line representing the distance and bearing to the bird.

It is just a demonstration of the kind of thing we can do if the data is online in a consistent format.

## [coha.pacificloon.ca/data](https://coha.pacifcloon.ca/data)

This endpoint updates the summary data files for each year and all time (since the app was developed 
in 2023).  It then displays a page with links to download the data files in CSV format.

The format looks like this (using uploaded 2022 data for quadrat E):

      quadrat,station,cloud,wind,noise,latitude,longitude,detection,direction,distance,detection_type,age_class,observers,notes,timestamp
      E,1,3,0,1,49.247804,-123.043471,N,,,,,Michelle Baudais Harvey Dueck,,2022-04-02.08-43-00
      E,2,3,2,1-2,49.247854,-123.03717,N,225,,,,Michelle Baudais Harvey Dueck,"maybe heard faint call in the distance, but might have been a flicker.  Call seemed slower.",2022-04-02.09-04-00
      E,3,3,3->1,1,49.247973,-123.03104,N,,,,,Michelle Baudais Harvey Dueck,"started breezy, then calmed down",2022-04-02.09-28-00
      E,4,3,2,3,49.247977,-123.023901,N,,,,,Michelle Baudais Harvey Dueck,,2022-04-02.09-40-00
      E,5,3,2,2,49.252378,-123.023873,N,,,,,Michelle Baudais Harvey Dueck,,2022-04-02.09-53-00
      E,6,3,1-2,2,49.252403,-123.031003,N,,,,,Michelle Baudais Harvey Dueck,,2022-04-02.10-33-00
      E,7,3,2,2,49.252443,-123.03732,N,,,,,Michelle Baudais Harvey Dueck,,2022-04-02.10-45-00
      E,8,3,0,2,49.252376,-123.043286,N,,,,,Michelle Baudais Harvey Dueck,"noise was on the quiet end of 2, maybe 1",2022-04-02.08-29-00
      E,9,3,1,3,49.257077,-123.044215,N,,,,,Michelle Baudais Harvey Dueck,,2022-04-02.10-56-00
      E,10,4,1,2,49.257242,-123.037976,N,,,,,Michelle Baudais Harvey Dueck,,2022-04-02.11-07-00
      E,11,4,1,3,49.256578,-123.031136,N,,,,,Michelle Baudais Harvey Dueck,,2022-04-02.11-20-00
      E,12,3,1,3,49.257376,-123.023897,N,,,,,Michelle Baudais Harvey Dueck,,2022-04-02.10-10-00
      E,13,3,1,3,49.261378,-123.02376,N,,,,,Michelle Baudais Harvey Dueck,,2022-04-02.08-02-00
      E,14,3,1,2,49.262143,-123.028832,N,,,,,Michelle Baudais Harvey Dueck,noise was at the quiet end of 2,2022-04-02.07-40-00
      E,15,2,1,2,49.261541,-123.037978,N,,,,,Michelle Baudais Harvey Dueck,flicker calling and drumming,2022-04-02.07-23-00
      E,16,3,1,2,49.261396,-123.044444,N,,,,,Michelle Baudais Harvey Dueck,,2022-04-02.07-08-00
      ... real file would have more lines with data from other quadrats and all fields would have valid values
          e.g. all wind fields emtered using the form will have only a single digit value
