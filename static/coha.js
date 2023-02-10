// coha.js - control and validate input from the COHA survey form

// We want shorter timers when debugging
var debug = false;

// Initialize audio on window load
var context = null;
var cohaBuffer;
var audioReady = false;
var audioSource = null;

# TODO: improve validation of values in text fields, e.g. direction, distance

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
    return quadrat.search("^[A-X]$") === 0
}
function quadratChanged() {
    let quadrat = document.getElementById("quadrat").value;
    quadratSet = isValidQuadrat(quadrat);

    // Save the quadrat as a browser cookie so the user doesn't have to constantly re-enter it
    if (quadratSet) {
        document.cookie = 'quadrat='+quadrat;
    } else {
        document.cookie = 'quadrat=Choose';
    }

}

function stationChanged() {
    let val = document.getElementById("station").value;
    if (val === "Not selected" ) {
        stationSet = false;
    } else {
        // station must be in the range 1-16
        let n = Number.parseInt(val);
        stationSet = (0 < n) && (n < 17);
    }
}

function cloudChanged() {
    cloudSet = true;
}

function windChanged() {
    windSet = true;
}

function noiseChanged() {
    noiseSet = true;
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
                    // once we know the survey conditions, get the current location
                    // and enable playing the recording
                    let latField = document.getElementById("latitude");
                    let longField = document.getElementById("longitude");
                    latField.disabled = false;
                    longField.disabled = false;

                    navigator.geolocation.getCurrentPosition(function(position) {
                        console.log("Latitude is :", position.coords.latitude);
                        console.log("Longitude is :", position.coords.longitude);
                        latField.value = position.coords.latitude;
                        longField.value = position.coords.longitude;


                    });
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
