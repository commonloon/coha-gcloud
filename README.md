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
folloed by the observation date and time in YYYY-MM-DD.HH-MM-SS format.

The content of the CSV file looks like this:
   quadrat,station,cloud,wind,noise,latitude,longitude,detection,direction,distance,email,notes,timestamp
   G,5,4,1,1,49.2476815,-123.0678571,no,,,debug@pacificloon.ca,"This is a test, not a real observation.",2023-02-10.00-19-59


# Instructions for Survey Participants
The main goal of the [coha.pacificloon.ca website](https://coha.pacificloon.ca) is to make the data entry easier 
for participants. 
The web form is intended to be used from a cellphone or tablet in the field to 
record observations as they are made.  The website will automatically get location data from the participant's cell 
phone, provided location services are enabled on the phone or tablet used.  Clicking the "Save Observation" button
saves the observation data (including conditions and location and time of observation) in the cloud.

Basic instructions on how to use the website are given below.  Participants should also read the 
[survey protocol](http://wildresearch.ca/wp-content/uploads/2017/03/Coopers-Hawk-in-the-City-Survey-Protocol.pdf)
and it's helpful to be familiar with the 
[paper data entry forms](http://wildresearch.ca/wp-content/uploads/2017/03/Coopers-Hawk-in-the-City-DataForm_v2.pdf)
the coha.pacificloon.ca website is intended to replace.

## Android Users

1. Make sure location services are enabled for your phone.
2. Travel to the station where you will take your first observation
3. Enter your email address in the first field.
   - The email address will be saved in your browser, so you should only have to do this the first time you use the website
4. Select the survey quadrat
   - the quadrat will also be saved in your browser.  You will only need to change it if you survey more than one quadrat.
5. Select the station (1-16)
   - other fields will be disabled until the station is selected
6. Select appropriate values for cloud cover, wind speed and noise at this station 
   - the browser will automatically fill in your current location (latituded and longitude) once you have entered values for all three conditions
7. When you are ready, begin the [survey protocol](http://wildresearch.ca/wp-content/uploads/2017/03/Coopers-Hawk-in-the-City-Survey-Protocol.pdf)
   1. the "Start Survey" button automates the audio part of the survey protocol
      1. pushing the button starts a two minute timer.  
         1. Use this time to look for hawks in the area
         2. if you see a COHA, press the button again to stop the audio playback
      2. after two minutes, the web app will play a recorded COHA call for 20 seconds, then pause for 40 seconds
         - if you see or hear a COHA, press "Stop Survey" to stop the audio playback
      3. the app repeats the call playback/pause three times
      4. the final timer counts down an additional two minutes, during which time you should continue to look and listen for COHAs
   2. When you have finished your observation at this station (at the end of the protocol or immediately on detecting a COHA), use the "Was COHA detected" dropdown to record whether you observed a COHA.
      - if a COHA was detected, use the next two fields to indicate its direction (0-360 degrees from North) and distance in metres from your location.
   3. Optionally add notes to the notes field
   4. Press the "Save Observation" button to save your observation.
      - **NOTE: your data will be lost if you don't press "Save Observation"!**
8. Go to the next station and repeat steps 5-7 until you have surveyed the entire quadrat
   - **NOTE: the location is set when you select the station, so don't select the station until you have arrived in the location where you plan to observe.

## iPhone Users

The procedure for iPhone users is very similar to Android, except iOS won't let me automate the audio playback.
This means iPhone and iPad users will need to manually time the two minute intervals and 40 second pauses in step 7.
iOS users can still use the web page to play the call: pressing play on the audio controls at the bottom of the form 
will play a 20 second clip of COHA call.  The bottom of the web page also includes 40 second and two minute timers,
so you don't have to switch to another timer app.  However, the timers are only visual, because *reasons*

# Useful Tips for Survey Participants
## Report Problems in github
Please report any problems or feature requests in the 
[github issue tracker](https://github.com/commonloon/coha-gcloud/issues)

## Use the map to find the correct station
Once you select the quadrat, the map at the bottom of the page displays an approximate location of all stations in 
the quadrat.  For most quadrats, the station location displayed is from the original 2016 survey package.  
For a few quadrats, the station locations were taken from more recent surveys.

When you select a station, the map updates to show a 400m radius circle centred on your current position.
You can also see the nominal location of nearby stations.  An message box appears if your current position is more than 
400m from the nominal location of the station you selected.  You should look at the map to make sure the web
broswer reported your current location correctly.  If it did, you probably want to select a station that's within
400m of your location.  If the map does NOT show your location correctly, please use some other method to get your
latitude and longitude and enter the correct values into the form.

Here's a screenshot of the map showing a current location as a blue circle, with yellow circles marking the
nominal station locations.  In this example, the participant should probably choose station 3 for this observation
(and consider whether to move closer to the nominal station location before taking their observation).

NOTE: *the current location does NOT update in real time.  It only updates when you change the station selection.
e.g. if you move after selecting your desired station, you will need to temporarily select a different station,
then select the correct station again to update your location.*

![map showing current location and nearby stations](map_demo.jpg)

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

The format looks like this (these are NOT real data: they were created for testing):

      quadrat,station,cloud,wind,noise,latitude,longitude,detection,direction,distance,email,notes,timestamp
      D,3,1,1,3,49.2466815,-123.0578571,yes,,1,debug@pacificloon.ca,,2023-02-14.08-26-23
      D,3,3,2,3,49.2466815,-123.0578571,yes,300,250,debug@pacificloon.ca,,2023-02-14.08-29-58
      D,3,2,3,2,49.2466815,-123.0578571,yes,44,50,debug@pacificloon.ca,,2023-02-14.14-49-11
      F,8,0,1,1,49.2542552,-123.0484187,no,,,debug@pacificloon.ca,,2023-02-10.04-57-15
      G,3,3,1,1,49.2466815,-123.0578571,no,,,debug@pacificloon.ca,,2023-02-10.04-54-19
      G,4,0,1,1,49.2466815,-123.0578571,no,,,debug@pacificloon.ca,,2023-02-10.03-29-25
      G,5,4,1,1,49.2466815,-123.0578571,no,,,debug@pacificloon.ca,"This is a test, not a real observation.",2023-02-10.00-19-59