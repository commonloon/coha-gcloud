let yearly_data = {};
let map;
let markers = [];

function initMap() {
  try {
    map = new google.maps.Map(document.getElementById("map"), {
      center: { lat: 49.2366675, lng: -123.0478035 },
      zoom: 12,
      mapTypeId: "terrain"
    });

    // Load the data after map initialization
    fetch('/map/data')
      .then(response => response.json())
      .then(data => {
        yearly_data = data;
        // Set default year if available
        const years = Object.keys(yearly_data);
        if (years.length > 0) {
          document.getElementById("select_year").value = years[0];
          show_year();
        }
      })
      .catch(error => {
        console.error('Error loading map data:', error);
      });

  } catch (error) {
    console.error("Error initializing map:", error);
  }
}

function show_year() {
  let i = 0;
  let year = document.getElementById("select_year").value;

  // Check if data exists for the selected year
  if (!yearly_data || !yearly_data[year]) {
    console.error('No data available for year:', year);
    return;
  }

  let data = yearly_data[year];
  clear_markers();

  for (; i < data.length; ++i) {
    let row = data[i];
    const pos = {lat: parseFloat(row.latitude), lng: parseFloat(row.longitude)};
    if (isNaN(pos.lat) || isNaN(pos.lng)) {
      // skip points with no coordinates
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


