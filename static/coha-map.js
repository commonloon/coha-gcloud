let yearly_data = {};
let map;
let markers = [];

// Define initMap as async
async function initMap() {
  try {
    // Get the map ID from the hidden input
    const mapIdElement = document.getElementById('map-id-input');
    const mapId = mapIdElement ? mapIdElement.value : '';

    // Load the core Maps library
    const { Map } = await google.maps.importLibrary("maps");

    // Create the map
    map = new Map(document.getElementById("map"), {
      center: { lat: 49.2366675, lng: -123.0478035 },
      zoom: 12,
      mapTypeId: "terrain",
      ...(mapId ? { mapId: mapId } : {})  // Add mapId only if it exists
    });

    // Load the data after map initialization
    fetch('/map/data')
      .then(response => response.json())
      .then(data => {
        yearly_data = data;
        // Set default year if available
        const years = Object.keys(yearly_data);
        if (years.length > 0) {
          const selectElement = document.getElementById("select_year");
          if (selectElement) {
            selectElement.value = years[0];
            show_year();
          }
        }
      })
      .catch(error => {
        console.error('Error loading map data:', error);
      });

  } catch (error) {
    console.error("Error initializing map:", error);
  }
}

// Define show_year as async so we can use await
async function show_year() {
  try {
    let i = 0;
    let year = document.getElementById("select_year").value;

    // Check if data exists for the selected year
    if (!yearly_data || !yearly_data[year]) {
      console.error('No data available for year:', year);
      return;
    }

    let data = yearly_data[year];
    clear_markers();

    // Import the marker and infowindow libraries
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");
    const { InfoWindow } = await google.maps.importLibrary("maps");

    for (; i < data.length; ++i) {
      let row = data[i];
      const pos = {lat: parseFloat(row.latitude), lng: parseFloat(row.longitude)};
      if (isNaN(pos.lat) || isNaN(pos.lng)) {
        // skip points with no coordinates
        continue;
      }

      // Create the AdvancedMarkerElement
      const marker = new AdvancedMarkerElement({
        position: pos,
        map: map,
        title: row.quadrat + ":" + row.station
      });

      // Add info window with click handler
      marker.addEventListener("gmp-click", () => {
        const infoWindow = new InfoWindow({
          content: `<div>
                      <p><strong>Quadrat:</strong> ${row.quadrat}</p>
                      <p><strong>Station:</strong> ${row.station}</p>
                      <p><strong>Detection:</strong> ${row.detection}</p>
                    </div>`
        });
        infoWindow.open({
          anchor: marker,
          map
        });
      });

      markers.push(marker);

      if (row.detection === "yes" || row.detection === "Y") {
        let distance = parseFloat(row.distance);
        let bearing = parseInt(row.direction);

        if (!isNaN(distance) && !isNaN(bearing)) {
          distance /= 1000;  // convert m to km
          let terminus = llFromDistance(pos.lat, pos.lng, distance, bearing);
          let path = [
            {lat: pos.lat, lng: pos.lng},
            {lat: terminus[0], lng: terminus[1]}
          ];
          const stroke = new google.maps.Polyline({
            path: path,
            geodesic: true,
            strokeColor: "#8800ff",
            strokeOpacity: 1.0,
            strokeWeight: 8,
          });
          stroke.setMap(map);
          markers.push(stroke);
        }
      }
    }
  } catch (error) {
    console.error("Error displaying markers:", error);

    // Fallback to standard markers if there's an error with advanced markers
    fallbackToStandardMarkers(year);
  }
}

// Fallback function in case the Advanced Markers fail
function fallbackToStandardMarkers(year) {
  console.log("Falling back to standard markers");

  let i = 0;
  if (!yearly_data || !yearly_data[year]) {
    return;
  }

  let data = yearly_data[year];
  clear_markers();

  for (; i < data.length; ++i) {
    let row = data[i];
    const pos = {lat: parseFloat(row.latitude), lng: parseFloat(row.longitude)};
    if (isNaN(pos.lat) || isNaN(pos.lng)) {
      continue;
    }

    let m = new google.maps.Marker({
      position: pos,
      map: map,
      title: row.quadrat + ":" + row.station
    });
    markers.push(m);

    if (row.detection === "yes" || row.detection === "Y") {
      let distance = parseFloat(row.distance);
      let bearing = parseInt(row.direction);

      if (!isNaN(distance) && !isNaN(bearing)) {
        distance /= 1000;
        let terminus = llFromDistance(pos.lat, pos.lng, distance, bearing);
        let path = [
          {lat: pos.lat, lng: pos.lng},
          {lat: terminus[0], lng: terminus[1]}
        ];
        const stroke = new google.maps.Polyline({
          path: path,
          geodesic: true,
          strokeColor: "#8800ff",
          strokeOpacity: 1.0,
          strokeWeight: 8,
        });
        stroke.setMap(map);
        markers.push(stroke);
      }
    }
  }
}

function clear_markers() {
  for (let i = 0; i < markers.length; i++) {
    markers[i].setMap(null);
  }
  markers = [];
}

// ----------------------------------------
// Calculate new Lat/Lng from original points
// on a distance and bearing (angle)
// ----------------------------------------
let llFromDistance = function(latitude, longitude, distance, bearing) {
  // taken from: https://jsfiddle.net/kodisha/8a3hcjtd/
  // distance in KM, bearing in degrees

  const R = 6378.1; // Radius of the Earth
  const brng = bearing * Math.PI / 180; // Convert bearing to radian
  let lat = latitude * Math.PI / 180; // Current coords to radians
  let lon = longitude * Math.PI / 180;

  // Do the math magic
  lat = Math.asin(Math.sin(lat) * Math.cos(distance / R) + Math.cos(lat) * Math.sin(distance / R) * Math.cos(brng));
  lon += Math.atan2(Math.sin(brng) * Math.sin(distance / R) * Math.cos(lat), Math.cos(distance / R) - Math.sin(lat) * Math.sin(lat));

  // Coords back to degrees and return
  return [(lat * 180 / Math.PI), (lon * 180 / Math.PI)];
}

// Ensure window.initMap points to our function for the callback
window.initMap = initMap;