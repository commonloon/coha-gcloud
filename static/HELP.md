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
3. Enter your name in the Observers field.
   - also add the name of anyone who is helping you do the survey
   - The observer name(s) will be saved in your browser, so you should only have to do this the first time you use the website
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
      - if a COHA was detected, use the next several fields to record details such as direction and distance
   3. Optionally add notes to the notes field
   4. Press the "Save Observation" button to save your observation.
      - **NOTE: your data will be lost if you don't press "Save Observation"!**
8. Go to the next station and repeat steps 5-7 until you have surveyed the entire quadrat
   - **NOTE: the location is set when you select the station**, so don't select the station until you have arrived in the location where you plan to observe.
   - If you need to reset your location, pick a different station, then pick the correct station again.

## iPhone Users

1. Make sure location services are enabled for your phone.
2. Travel to the station where you will take your first observation
3. Enter your name in the Observers field.
   - also add the name of anyone who is helping you do the survey
   - The observer name(s) will be saved in your browser, so you should only have to do this the first time you use the website
4. Select the survey quadrat
   - the quadrat will also be saved in your browser.  You will only need to change it if you survey more than one quadrat.
5. Select the station (1-16)
   - other fields will be disabled until the station is selected
   - you can use the map at the bottom of the web page to help you pick the correct station
6. Select appropriate values for cloud cover, wind speed and noise at this station 
   - the browser will automatically fill in your current location (latituded and longitude) once you have entered values for all three conditions
7. When you are ready, begin the [survey protocol](http://wildresearch.ca/wp-content/uploads/2017/03/Coopers-Hawk-in-the-City-Survey-Protocol.pdf)
   1. Remember: stop playing audio at a station and record your detection as soon as you see or hear a COHA.  We don't want to drive them off their nest.
   2. Push the button to start the two minute timer 
   3. Look and listen for signs of COHA
   4. after two minutes if no COHA has been detected, use the audio playback control to play the COHA call for 20 seconds
   5. When the call playback finishes, start the 40s timer and look and listen for signs of COHA
   6. repeat the preceding steps three times (i.e. 3 cycles of play call for 20s, observe for 40s)
   7. After the 3rd playback/observe cycle, start the 2 minute timer and observe for two more minutes
   8. record whether you observed a COHA, adding details if yes.
   9. optionally add notes in the Notes field
   10. press the "Save Observation" button to save your results.  
       - ** your observation will be lost if you don't do this step **
ndicate its direction (0-360 degrees from North) and distance in metres from your location.

8. Go to the next station and repeat steps 5-7 until you have surveyed the entire quadrat
   - **NOTE: the location is set when you select the station**, so don't select the station until you have arrived in the location where you plan to observe.
   - If you need to reset your location, pick a different station, then pick the correct station again.

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

![map showing current location and nearby stations](/map_demo.jpg)
