"use client";

import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import L from "leaflet";
import { useEffect, useMemo, useState } from "react";

const center = [47.458, 8.555];

const normalizeId = (value) =>
  String(value ?? "")
    .trim()
    .toUpperCase();

const runwayFromIndex = (idx) => {
  const n = Number(idx);
  if (!Number.isFinite(n)) return "";
  if (n === 0) return "16/34";
  if (n === 1) return "10/28";
  if (n === 2) return "14/32";
  return "";
};

const isRunwayActiveNow = (flight, currentTime) => {
  const landingTime = Number(flight?.landing_time);
  const takeoffTime = Number(flight?.takeoff_time);

  const inLandingWindow =
    Number.isFinite(landingTime) &&
    landingTime <= currentTime &&
    landingTime + 5 >= currentTime;

  const inTakeoffWindow =
    Number.isFinite(takeoffTime) &&
    takeoffTime <= currentTime &&
    takeoffTime + 5 >= currentTime;

  return inLandingWindow || inTakeoffWindow;
};

const isGateActiveNow = (flight, currentTime) => {
  const gateArrival = Number(flight?.gate_arrival);
  const gateDeparture = Number(flight?.gate_departure);

  return (
    Number.isFinite(gateArrival) &&
    Number.isFinite(gateDeparture) &&
    gateArrival <= currentTime &&
    gateDeparture >= currentTime
  );
};

export default function AirportLeafletMap({ schedule, currentTime }) {
  const [geoData, setGeoData] = useState(null);

  useEffect(() => {
    fetch("/lszh_airport.geojson")
      .then((res) => res.json())
      .then((data) => setGeoData(data));
  }, []);

  // Highlight only one active runway at a time to avoid visual ambiguity.
  const activeRunwayId = useMemo(() => {
    const activeFlights = (schedule || []).filter((f) => isRunwayActiveNow(f, currentTime));
    if (activeFlights.length === 0) return "";

    activeFlights.sort((a, b) => {
      const aT = Math.min(
        Number.isFinite(Number(a?.landing_time)) ? Number(a.landing_time) : Number.MAX_SAFE_INTEGER,
        Number.isFinite(Number(a?.takeoff_time)) ? Number(a.takeoff_time) : Number.MAX_SAFE_INTEGER
      );
      const bT = Math.min(
        Number.isFinite(Number(b?.landing_time)) ? Number(b.landing_time) : Number.MAX_SAFE_INTEGER,
        Number.isFinite(Number(b?.takeoff_time)) ? Number(b.takeoff_time) : Number.MAX_SAFE_INTEGER
      );
      return aT - bT;
    });

    const flight = activeFlights[0];
    const byName = normalizeId(flight?.runway);
    if (byName) return byName;
    return normalizeId(runwayFromIndex(flight?.runway_index));
  }, [schedule, currentTime]);

  const activeGateIds = useMemo(() => {
    const ids = new Set();
    for (const flight of schedule || []) {
      if (!isGateActiveNow(flight, currentTime)) continue;
      const gateId = normalizeId(flight?.gate);
      if (gateId) ids.add(gateId);
    }
    return ids;
  }, [schedule, currentTime]);

  const styleFeature = (feature) => {
    const type = feature?.properties?.aeroway;
    const featureId = normalizeId(feature?.properties?.ref || feature?.properties?.name);

    if (type === "runway") {
      return {
        color: activeRunwayId && activeRunwayId === featureId ? "red" : "#333",
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
      return {
        color: "black",
        fillColor: activeGateIds.has(featureId) ? "green" : "gray",
        fillOpacity: 0.8,
        radius: 5,
      };
    }

    return {};
  };

  return (
    <div className="h-[580px] rounded-xl shadow-lg overflow-hidden">
      <MapContainer center={center} zoom={14} style={{ height: "100%", width: "100%" }}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

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



