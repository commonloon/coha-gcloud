let map;

function initMap() {
  let lat = 49.2366675;
  let lng = -123.0478035;
  map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: lat, lng: lng },
    zoom: 12,
  });
  let i=0;
  for (; i < data.length; ++i) {
    let row = data[i];
    const pos = {lat: parseFloat(row.latitude), lng: parseFloat(row.longitude)};
    new google.maps.Marker({
      position: pos,
      map: map,
      title: row.quadrat + ":" + row.station
    });
    if (row.detection === "yes") {
      let distance = parseFloat(row.distance);
      let bearing = parseInt(row.direction);
      if (!isNaN(distance) && ! isNaN(bearing)) {
        distance /= 1000;  // convert m to km
        terminus = llFromDistance(pos.lat, pos.lng, distance, bearing);
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
      }
    }
  }
}

window.initMap = initMap;


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


