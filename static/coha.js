// coha.js - control and validate input from the COHA survey form


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
    const emailStr = document.getElementById("email").value

    // clear the message field
    document.getElementById("message").textContent = "unsaved changes";

    // Perform field validation and enable/disable form elements as required
    if (emailSet || (isEmail(emailStr))) {
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

function stopSurvey() {
    let button = document.getElementById("startButton");
    button.disabled = true;
    button.textContent = "Start Survey";
    timer.pause();
}
function startSurvey() {
    let button = document.getElementById("startButton");
    button.textContent = "Stop Survey";
    button.onclick = stopSurvey;
    timer = startTimer(120, "timer", function() {alert("done")});

}
