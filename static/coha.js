// coha.js - control and validate input from the COHA survey form

// We want shorter timers when debugging
var debug = false;

// Bounds of the survey area
var quadrats = [
    "A", "B", "C", "D", "E", "F", "G", "H",
    "I", "J", "K", "L", "M", "N", "O", "P",
    "Q", "R", "S", "T", "U", "V", "W", "X",
];
var surveyBounds = {
    west: -123.157770,
    north: 49.263912,
    south: 49.209423,
    east: -122.937837
};

// We need to keep a record of google maps markers so we can erase them
var mapMarkers = [];
var positionMarker = null;

// initialize the quadrat boundaries if quadrat is set by cookie
window.onload = () => {
    observersChanged();
    quadratChanged();
}

const protocol_msg =
"- Observe for two minutes<br>" +
"- play call 20s / observe 40s<br>" +
"- play call 20s / observe 40s<br>" +
"- play call 20s / observe 40s<br>" +
"- Observe for two minutes<br>" +
"- Record result and save observation";


// Initialize audio on window load
var context = null;
var cohaBuffer;
var audioReady = false;
var audioSource = null;

//  TODO: improve validation of values in text fields, e.g. direction, distance

function getDistanceFromLatLonInKm(lat1, lon1, lat2, lon2) {
  let R = 6371; // Radius of the earth in km
  let dLat = deg2rad(lat2-lat1);  // deg2rad below
  let dLon = deg2rad(lon2-lon1);
  let a =
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
    Math.sin(dLon/2) * Math.sin(dLon/2)
    ;
  let c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  let d = R * c; // Distance in km
  return d;
}

function deg2rad(deg) {
  return deg * (Math.PI/180)
}

function initAudio() {
    // load the audio into cohaBuffer
    let request = new XMLHttpRequest();
    request.open('GET', "/COHA.modified.mp3", true);
    request.responseType = 'arraybuffer';

    // Decode asynchronously
    request.onload = function() {
    context.decodeAudioData(request.response,
        function(buffer) {
            cohaBuffer = buffer;
        },
        () => {
            alert('failed to load COHA audio');
            audioReady = false;
        });
    }
    request.send();
}


// UI state
var timer = null;

// Form state
var observersSet = false;
var quadratSet = false;
var stationSet = false;
var cloudSet = false;
var windSet = false;
var noiseSet = false;
var cohaDetected = false;

function sanitizeObservers(untrusted) {
    const replacementPattern = "[^A-Za-z .:;,']";  // replace all but a few characters
    return untrusted.replaceAll(replacementPattern, "").trim()
}


function observersChanged() {
    let observersStr = sanitizeObservers(document.getElementById("observers").value);


    if (observersStr !== "") {
        observersSet = true;
        // save the observer name(s) as a browser cookie
        document.cookie = "observers=" + observersStr;
    } else {
        observersSet = false;
        alert('Please use at least a few letters to identify the observer(s)');
    }
}

// put an individual station marker on the map
function stationMarker(row, station, quadrat) {
    const pos = {lat: parseFloat(row.latitude), lng: parseFloat(row.longitude)};
    const title = quadrat + ":" + station.toString();
    const marker = new google.maps.Marker({
        position: pos,
        map: map,
        title: title,
        label: station.toString()
    });
    mapMarkers.push(marker);
    const c = new google.maps.Circle({
      strokeColor: "#FF0000",
      strokeOpacity: 0.8,
      strokeWeight: 2,
      fillColor: "#FFFF00",
      fillOpacity: 0.35,
      map,
      center: pos,
      radius: 250,
    });
    mapMarkers.push(c);
}

// mark all stations of a quadrat on the map
function mapStations(quadrat) {
    let coords = stationCoordinates[quadrat];
    let station=1;
    for(; station < 17; ++station) {
        stationMarker(coords[station], station, quadrat);
    }
}

function isValidQuadrat(quadrat) {
    return quadrats.indexOf(quadrat) != -1;
}
function quadratChanged() {
    let quadrat = document.getElementById("quadrat").value;
    quadratSet = isValidQuadrat(quadrat);

    if (quadratSet) {
        // Save the quadrat as a browser cookie so the user doesn't have to constantly re-enter it
        document.cookie = 'quadrat='+quadrat;
        // erase existing map markers
        mapMarkers.forEach((marker) => {
            marker.setMap(null);
        });
        mapMarkers = [];
        // show this quadrat's stations on the map
        mapStations(quadrat);
    } else {
        document.cookie = 'quadrat=Choose';
    }

}

function mapMarker(latitude, longitude, label) {
    const pos = {lat: parseFloat(latitude), lng: parseFloat(longitude)};
    const marker = new google.maps.Marker({
        position: pos,
        map: map,
        title: label,
        label: "YOU"
    });
    if (positionMarker != null) {
        // clear the old marker
        positionMarker.setMap(null);
    }
    positionMarker = marker;
    const c = new google.maps.Circle({
      strokeColor: "#0000FF",
      strokeOpacity: 0.8,
      strokeWeight: 2,
      fillColor: "#00FFFF",
      fillOpacity: 0.35,
      map,
      center: pos,
      radius: 400,
    });
    mapMarkers.push(c);
}

function distanceFromStation(quadrat, station, lat, long, nominalLocation) {
    let lt = nominalLocation.latitude;
    let lo = nominalLocation.longitude;

    dNorthSouth = getDistanceFromLatLonInKm(lt, lo, lat, lo);
    dEastWest = getDistanceFromLatLonInKm(lt, lo, lt, long);

    nsDir = lat > lt ?  "north" : "south";
    ewDir = lo < long ? "east" : "west";

    let message = dNorthSouth.toFixed(2) + "km " + nsDir + " and " + dEastWest.toFixed(2) + "km " + ewDir;
    message = "Current location is " + message + " from the nominal location of ";
    message += "quadrat " + quadrat + " station " + station + ". ";
    message += "Did you select the correct station? If so, please double-check the latitude/longitude values below";
    return message
}

function geolocationError(error) {
  let msg;
  switch(error.code) {
    case error.PERMISSION_DENIED:
      msg = "User denied the request for Geolocation. ";
      break;
    case error.POSITION_UNAVAILABLE:
      msg =  "Location information is unavailable.";
      break;
    case error.TIMEOUT:
      msg= "The request to get user location timed out."
      break;
    case error.UNKNOWN_ERROR:
      msg = "An unknown error occurred."
      break;
  }
  msg += "  Please manually enter latitude and longitude.";
  alert(msg);
}

function updateLocation() {
    navigator.geolocation.getCurrentPosition(function (position) {
        console.log("Latitude is :", position.coords.latitude);
        console.log("Longitude is :", position.coords.longitude);
        console.log("accuracy is :", position.coords.accuracy);
        let lt = position.coords.latitude;
        let lo = position.coords.longitude;

        // map the current location
        mapMarker(lt, lo, "Current Position")

        // center the map on our current location and zoom appropriately
        map.setCenter({lat: lt, lng: lo});
        map.setZoom(14);

        if (stationSet) {
            let station = document.getElementById("station").value;
            let quadrat = document.getElementById("quadrat").value;
            let latField = document.getElementById("latitude");
            let longField = document.getElementById("longitude");
            let nominalLocation = stationCoordinates[quadrat][station];

            if (position.coords.accuracy > 50) {
                // warn user if position accuracy is worse than 50 metres
                alert("This GPS position is not accurate.  Double-check the latitude and longitude values");
            }

            // enable the latitude and longitude fields
            latField.disabled = false;
            longField.disabled = false;

            // update the position regardless, but warn the user if they're far from the station
            let d = getDistanceFromLatLonInKm(nominalLocation.latitude, nominalLocation.longitude, lt, lo);
            longField.value = lo;
            latField.value = lt;
            if (d > 0.4) {
                alert(distanceFromStation(quadrat, station, lt, lo, nominalLocation));
            }
        }

    }, geolocationError, {maximumAge:10000, timeout:5000, enableHighAccuracy: true});
}

function stationChanged() {
    let val = document.getElementById("station").value;
    if (val === "Not selected" ) {
        stationSet = false;
    } else {
        // station must be in the range 1-16
        let n = Number.parseInt(val);
        stationSet = (0 < n) && (n < 17);
        if (stationSet) {
            updateLocation();
        }
    }
}

function cloudChanged() {
    let val = document.getElementById("cloud").value;
    cloudSet = val in ["0", "1", "2", "3", "4"];
}

function windChanged() {
    let val = document.getElementById("wind").value;
    windSet = val in ["0", "1", "2", "3", "4"];
}

function noiseChanged() {
    let val = document.getElementById("noise").value;
    noiseSet = val in ["0", "1", "2", "3"];
}

function detectionChanged() {
    let val = document.getElementById("detection").value;

    cohaDetected = val === "yes";
    if (cohaDetected) {
        let detectionTypeElement = document.getElementById("detection_type");

        detectionTypeElement.hidden = false;
    }
}

function detectionTypeChanged() {
    let detectionTypeElement = document.getElementById("detection_type");

    const detection_type = detectionTypeElement.value;

    if (detection_type === "V") {
        let ageElement = document.getElementById("age_class");
        ageElement.hidden = false;
    }
}

function formChanged() {
    let submitButton = document.getElementById("submit");
    let observersStr = document.getElementById("observers").value;

    if (context === null) {
        context = new AudioContext();
        initAudio();
    }

    // clear the message field
    document.getElementById("message").textContent = "unsaved changes";

    if (!observersSet && observersStr.length > 0) {
        observersStr = sanitizeObservers(observersStr);
    }

    // Perform field validation and enable/disable form elements as required
    if (observersSet || observersStr !== "") {
        // special observer name triggers debug mode that shortens some countdown timers
        if (observersStr === "debug") {
            debug = true;
        }

        // Once we know the observer(s), allow selection of the quadrat
        document.getElementById("quadrat").disabled = false;

        if (quadratSet || isValidQuadrat(document.getElementById("quadrat").value)) {
            // given the quadrat, allow selection of station within the quadrat
            document.getElementById("station").disabled = false;

            if (stationSet) {
                // given the station, require selection of survey conditions
                document.getElementById("wind").disabled = false;
                document.getElementById("cloud").disabled = false;
                document.getElementById("noise").disabled = false;
                document.getElementById("detection").disabled = false;

                if (windSet && cloudSet && noiseSet) {
                    // enable the start button, if it exists (i.e. not an iPhone)
                    let startButton = document.getElementById("startButton");
                    if (startButton) startButton.disabled = false;

                    if (cohaDetected) {
                        // if we detected a COHA, then we want to know where
                        document.getElementById("distance").disabled = false;
                        document.getElementById("direction").disabled = false;
                    } else {
                        // if we didn't detect a COHA, there's no point recording where
                        document.getElementById("distance").disabled = true;
                        document.getElementById("direction").disabled = true;
                    }
                    // Enable the submit button once a detection has been indicated and all the
                    // other required fields have been assigned values.
                    let detectionValue = document.getElementById("detection").value;
                    submitButton.disabled = !(detectionValue === "yes" || detectionValue === "no");

                    if (iphone) {
                        // Display the protocol in the message container.
                        // iPhone users need to run the protocol manually, so they need instructions
                        let messageContainer = document.getElementById("message");
                        messageContainer.innerHTML = protocol_msg;
                        messageContainer.style.fontSize = "16px";
                    }
                } else {
                    // conditions must be specified before submitting form
                    submitButton.disabled = true;
                }
            }
        }
    }
}

function enableTimerButtons(enable=true) {
    let fortySecondButton = document.getElementById("fortySecondTimer");
    let twoMinuteButton = document.getElementById("twoMinuteTimer");
    fortySecondButton.disabled = !enable;
    twoMinuteButton.disabled = !enable;
}

function fortySecondTimer() {
    // we call clearTimer() to re-enable the buttons when the countdown completes
    timer = startTimer(40, "timer", clearTimer);
    // we have to disable the start buttons during countdown, because we're using a global variable
    // to access our timer and we don't want to replace it until the countdown is finished
    enableTimerButtons(false);  // disable buttons during countdown
}

function twoMinuteTimer() {
    // we call clearTimer() to re-enable the buttons when the countdown completes
    timer = startTimer(120, "timer", clearTimer);
    // we have to disable the start buttons during countdown, because we're using a global variable
    // to access our timer and we don't want to replace it until the countdown is finished
    enableTimerButtons(false);  // disable buttons during countdown
}

function clearTimer() {
    timer.pause();
    container = document.getElementById("timer");
    container.innerHTML = "00:00";
    enableTimerButtons(true);
}

function startTimer(seconds, container, oncomplete=null) {
    let startTime, timer, obj, ms = seconds*1000,
        display = document.getElementById(container);
    let completed = false;
    obj = {};
    obj.resume = function() {
        startTime = new Date().getTime();
        timer = setInterval(obj.step,250); // adjust this number to affect granularity
        // lower numbers are more accurate, but more CPU-expensive
    };
    obj.pause = function() {
        ms = obj.step();
        clearInterval(timer);
    };
    obj.step = function() {
        var now = Math.max(0,ms-(new Date().getTime()-startTime)),
            m = Math.floor(now/60000), s = Math.floor(now/1000)%60;
        s = (s < 10 ? "0" : "")+s;
        display.innerHTML = m+":"+s;
        if( now === 0) {
            clearInterval(timer);
            obj.resume = function() {};
            if( !completed && oncomplete != null ) {
                completed = true;
                oncomplete();
            }
        }
        return now;
    };
    obj.resume();
    return obj;
}

function playCall() {
    // connect the audio source if we haven't done so before
    audioSource = context.createBufferSource(); // create a sound source
    audioSource.buffer = cohaBuffer;                // tell the source to use our buffer
    audioSource.connect(context.destination);       // connect the source to something, hopefully the speakers
    audioSource.start(0, 0, 20);   // play the source for 20 seconds starting at the beginning
    audioReady = true;
}

function stopAudio() {
    if (audioReady) {
        audioSource.stop();
    }
}

function firstCall() {
    let messageField = document.getElementById("message")
    let timeout = 60;  // 20 seconds of call playback plus 40 seconds of observation time
    if (debug) {
        timeout = 22;  // shorter timeout when debugging
    }
    messageField.textContent =
        "Look and listen for COHA. Stop the survey if heard or spotted. Call 2 will play when countdown reaches 0.";
    playCall();
    timer = startTimer(timeout, "timer", secondCall);
}
function secondCall() {
    let messageField = document.getElementById("message")
    let timeout = 60;  // 20 seconds of call playback plus 40 seconds of observation time
    if (debug) {
        timeout = 22;  // shorter timeout when debugging
    }
    messageField.textContent =
        "Look and listen for COHA. Stop the survey if heard or spotted. Call 3 will play when countdown reaches 0.";
    timer = startTimer(timeout, "timer", thirdCall);
    playCall();
}
function thirdCall() {
    let messageField = document.getElementById("message");
    let timeout = 180;  // length of the final survey period in seconds
    if (debug) {
        timeout = 22;  // shorter timeout for debugging
    }
    messageField.textContent =
        "Look and listen for COHA.  Stop the survey if heard or spotted.  Survey ends when  countdown reaches 0.";
    timer = startTimer(timeout, "timer", surveyFinished);
    playCall();
}
function surveyFinished() {
    let messageField = document.getElementById("message")
    messageField.textContent =
        "Survey complete.  Record whether COHA was detected, then press \"Save Observation\" to save results.";
}

function stopSurvey() {
    let button = document.getElementById("startButton");
    let messageField = document.getElementById("message")
    messageField.textContent =
        "Survey stopped. Record whether COHA was detected, then press \"Save Observation\" to save results.";
    button.disabled = true;
    button.textContent = "Start Survey";
    timer.pause();
    stopAudio();
}
function startSurvey() {
    let button = document.getElementById("startButton");
    let messageField = document.getElementById("message")
    let timeout = 120;  // length of the initial survey period, when no call is played

    if (debug) {
        timeout = 3;  // seconds, shorter timeout for debugging the web app
    }

    button.textContent = "Stop Survey";
    button.onclick = stopSurvey;
    messageField.textContent =
        "Look and listen for COHA.  Stop the survey if heard or spotted.  Call will play when countdown reaches 0.";

    timer = startTimer(timeout, "timer", firstCall); // should be 120 seconds, fix if shorter
}


///////////
// Map
///////////
let map;

function initMap() {
  let lat = 49.2366675;
  let lng = -123.0478035;
  map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: lat, lng: lng },
    zoom: 12,
  });
}

window.initMap = initMap;




