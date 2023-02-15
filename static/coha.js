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


// initialize the quadrat boundaries if quadrat is set by cookie
window.onload = () => {
    emailChanged();
    quadratChanged();
}



// Initialize audio on window load
var context = null;
var cohaBuffer;
var audioReady = false;
var audioSource = null;

//  TODO: improve validation of values in text fields, e.g. direction, distance

function getDistanceFromLatLonInKm(lat1, lon1, lat2, lon2) {
  var R = 6371; // Radius of the earth in km
  var dLat = deg2rad(lat2-lat1);  // deg2rad below
  var dLon = deg2rad(lon2-lon1);
  var a =
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
    Math.sin(dLon/2) * Math.sin(dLon/2)
    ;
  var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  var d = R * c; // Distance in km
  return d;
}

function deg2rad(deg) {
  return deg * (Math.PI/180)
}

function initAudio() {
    // load the audio into cohaBuffer
    let request = new XMLHttpRequest();
    request.open('GET', "/static/COHA.mp3", true);
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
var emailSet = false;
var quadratSet = false;
var stationSet = false;
var cloudSet = false;
var windSet = false;
var noiseSet = false;
var cohaDetected = false;

function isEmail(email) {
  let EmailRegex = /^([a-zA-Z0-9_.+-])+\@(([a-zA-Z0-9-])+\.)+([a-zA-Z0-9]{2,4})+$/;
  return EmailRegex.test(email);
}
function emailChanged() {
    const emailStr = document.getElementById("email").value
    if (isEmail(emailStr)) {
        emailSet = true;
        // save the email address as a browser cookie
        document.cookie = "email=" + emailStr;
    } else {
        emailSet = false;
        alert('Invalid email address');
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
    } else {
        document.cookie = 'quadrat=Choose';
    }

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

function stationChanged() {
    let val = document.getElementById("station").value;
    if (val === "Not selected" ) {
        stationSet = false;
    } else {
        // station must be in the range 1-16
        let n = Number.parseInt(val);
        stationSet = (0 < n) && (n < 17);
        if (stationSet) {
            let station = n.toString();
            let quadrat = document.getElementById("quadrat").value;

            // Try to set the location fields automatically.
            let latField = document.getElementById("latitude");
            let longField = document.getElementById("longitude");
            latField.disabled = false;
            longField.disabled = false;

            navigator.geolocation.getCurrentPosition(function (position) {
                let nominalLocation = stationCoordinates[quadrat][station];
                console.log("Latitude is :", position.coords.latitude);
                console.log("Longitude is :", position.coords.longitude);
                let lt = position.coords.latitude;
                let lo = position.coords.longitude;

                // update the position regardless, but warn the user if they're far from the station
                let d = getDistanceFromLatLonInKm(nominalLocation.latitude, nominalLocation.longitude, lt, lo);
                longField.value = lo;
                latField.value = lt;
                if (d > 0.4) {
                    alert(distanceFromStation(quadrat, station, lt, lo, nominalLocation));
                }
            });
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
}

function formChanged() {
    let submitButton = document.getElementById("submit");
    const emailStr = document.getElementById("email").value;

    if (context === null) {
        context = new AudioContext();
        initAudio();
    }

    // clear the message field
    document.getElementById("message").textContent = "unsaved changes";

    // Perform field validation and enable/disable form elements as required
    if (emailSet || (isEmail(emailStr))) {
        // special email address triggers debug mode
        if (emailStr === "debug@pacificloon.ca") {
            debug = true;
        }

        // Once we know the user, allow selection of the quadrat
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
                    // enable the start button
                    document.getElementById("startButton").disabled = false;

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
                } else {
                    // conditions must be specified before submitting form
                    submitButton.disabled = true;
                }
            }
        }
    }
}

function startTimer(seconds, container, oncomplete) {
    var startTime, timer, obj, ms = seconds*1000,
        display = document.getElementById(container);
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
            if( oncomplete) oncomplete();
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
    timer = startTimer(180, "timer", surveyFinished);
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
