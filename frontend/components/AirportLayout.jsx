"use client";

import { MapContainer, TileLayer, GeoJSON, Marker, Tooltip } from "react-leaflet";
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

const activeRunwayActivityForFlightNow = (flight, currentTime) => {
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

  if (inTakeoffWindow) {
    const byTakeoffName = normalizeId(flight?.takeoff_runway);
    if (byTakeoffName) return { runwayId: byTakeoffName, phase: "takeoff" };
    return {
      runwayId: normalizeId(runwayFromIndex(flight?.takeoff_runway_index)),
      phase: "takeoff",
    };
  }

  if (inLandingWindow) {
    const byLandingName = normalizeId(flight?.landing_runway || flight?.runway);
    if (byLandingName) return { runwayId: byLandingName, phase: "landing" };
    return {
      runwayId: normalizeId(runwayFromIndex(flight?.landing_runway_index ?? flight?.runway_index)),
      phase: "landing",
    };
  }

  return { runwayId: "", phase: "" };
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

const getRunwayDirectionBadge = (runwayId, phase) => {
  const text = String(runwayId || "").trim();
  if (!text.includes("/")) return "--";
  const [endA, endB] = text.split("/");
  return phase === "takeoff" ? (endB || "--") : (endA || "--");
};

const getMidpointFromCoords = (coords) => {
  if (!Array.isArray(coords) || coords.length === 0) return null;
  const mid = Math.floor(coords.length / 2);
  const point = coords[mid];
  if (!Array.isArray(point) || point.length < 2) return null;
  return [point[1], point[0]];
};

const getRunwayMidpoint = (feature) => {
  const geometry = feature?.geometry;
  if (!geometry) return null;

  if (geometry.type === "LineString") {
    return getMidpointFromCoords(geometry.coordinates);
  }

  if (geometry.type === "MultiLineString") {
    const firstLine = Array.isArray(geometry.coordinates) ? geometry.coordinates[0] : null;
    return getMidpointFromCoords(firstLine);
  }

  if (geometry.type === "Polygon") {
    const outerRing = Array.isArray(geometry.coordinates) ? geometry.coordinates[0] : null;
    return getMidpointFromCoords(outerRing);
  }

  return null;
};

const makeArrowIcon = (phase) => {
  const isTakeoff = phase === "takeoff";
  const bg = isTakeoff ? "#22c55e" : "#ef4444";
  const arrow = isTakeoff ? "➜" : "➤";
  return L.divIcon({
    className: "",
    html: `<div style="width:18px;height:18px;border-radius:50%;background:${bg};color:#101010;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;box-shadow:0 0 0 2px #111;">${arrow}</div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
};

export default function AirportLeafletMap({ schedule, currentTime }) {
  const [geoData, setGeoData] = useState(null);

  useEffect(() => {
    fetch("/lszh_airport.geojson")
      .then((res) => res.json())
      .then((data) => setGeoData(data));
  }, []);

  // Highlight only one active runway at a time to avoid visual ambiguity.
  const activeRunway = useMemo(() => {
    const activeFlights = (schedule || []).filter((f) => isRunwayActiveNow(f, currentTime));
    if (activeFlights.length === 0) return { runwayId: "", phase: "" };

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
    return activeRunwayActivityForFlightNow(flight, currentTime);
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

  const activeRunwayFeature = useMemo(() => {
    if (!geoData || !Array.isArray(geoData?.features) || !activeRunway?.runwayId) return null;
    return (
      geoData.features.find((feature) => {
        if (feature?.properties?.aeroway !== "runway") return false;
        const featureId = normalizeId(feature?.properties?.ref || feature?.properties?.name);
        return featureId === activeRunway.runwayId;
      }) || null
    );
  }, [geoData, activeRunway]);

  const activeRunwayMidpoint = useMemo(() => {
    if (!activeRunwayFeature) return null;
    return getRunwayMidpoint(activeRunwayFeature);
  }, [activeRunwayFeature]);

  const styleFeature = (feature) => {
    const type = feature?.properties?.aeroway;
    const featureId = normalizeId(feature?.properties?.ref || feature?.properties?.name);

    if (type === "runway") {
      const isActive = activeRunway.runwayId && activeRunway.runwayId === featureId;
      const activeColor = activeRunway.phase === "takeoff" ? "#22c55e" : "#ef4444";
      return {
        color: isActive ? activeColor : "#333",
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
        fillColor: activeGateIds.has(featureId) ? "#ffeb3b" : "gray",
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
            key={`${activeRunway.runwayId}-${activeRunway.phase}`}
            data={geoData}
            style={styleFeature}
            onEachFeature={(feature, layer) => {
              if (feature?.properties?.aeroway !== "runway") return;
              const featureId = normalizeId(feature?.properties?.ref || feature?.properties?.name);
              const isActive =
                activeRunway.runwayId && activeRunway.runwayId === featureId && activeRunway.phase;

              const badge = isActive
                ? `${activeRunway.phase === "takeoff" ? "Takeoff" : "Landing"}: ${getRunwayDirectionBadge(
                    featureId,
                    activeRunway.phase
                  )}`
                : "Direction: --";

              const tooltip = `<div style="font-size:12px;line-height:1.3;"><strong>Runway ${featureId || "--"}</strong><br/>${badge}</div>`;
              layer.bindTooltip(tooltip, { sticky: true });
            }}
            pointToLayer={(feature, latlng) => {
              if (feature.properties?.aeroway === "gate") {
                return L.circleMarker(latlng);
              }
            }}
          />
        )}

        {activeRunwayMidpoint && activeRunway?.phase && (
          <Marker position={activeRunwayMidpoint} icon={makeArrowIcon(activeRunway.phase)}>
            <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
              {activeRunway.phase === "takeoff" ? "Takeoff" : "Landing"}:{" "}
              {getRunwayDirectionBadge(activeRunway.runwayId, activeRunway.phase)}
            </Tooltip>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}



