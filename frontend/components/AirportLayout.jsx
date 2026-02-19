"use client";

import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import L from "leaflet";
import { useEffect, useState } from "react";

const center = [47.458, 8.555];

export default function AirportLeafletMap({ schedule, currentTime }) {
  const [geoData, setGeoData] = useState(null);

  useEffect(() => {
    fetch("/lszh_airport.geojson")
      .then(res => res.json())
      .then(data => setGeoData(data));
  }, []);

  const styleFeature = (feature) => {
    const type = feature.properties?.aeroway;

    // Detect runway activity
    const runwayActive = schedule.some(flight =>
      (flight.landing_time <= currentTime &&
       flight.landing_time + 5 >= currentTime) ||
      (flight.takeoff_time <= currentTime &&
       flight.takeoff_time + 5 >= currentTime)
    );

    if (type === "runway") {
      return {
        color: runwayActive ? "red" : "#333",
        weight: 8,
      };
    }

    if (type === "taxiway") {
      return {
        color: "#999",
        weight: 2,
      };
    }

    if (type === "gate") {
      const gateId = feature.properties.ref || feature.properties.name;

      const gateActive = schedule.some(flight =>
        flight.gate === gateId &&
        flight.gate_arrival <= currentTime &&
        flight.gate_departure >= currentTime
      );

      return {
        color: "black",
        fillColor: gateActive ? "green" : "gray",
        fillOpacity: 0.8,
        radius: 5,
      };
    }

    return {};
  };

  return (
    <div className="h-[700px] rounded-xl shadow-lg overflow-hidden">
      <MapContainer
        center={center}
        zoom={14}
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {geoData && (
          <GeoJSON
            data={geoData}
            style={styleFeature}
            pointToLayer={(feature, latlng) => {
              if (feature.properties?.aeroway === "gate") {
                return L.circleMarker(latlng);
              }
            }}
          />
        )}
      </MapContainer>
    </div>
  );
}
