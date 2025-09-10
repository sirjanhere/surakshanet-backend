"""
SurakshaNet – Hybrid Navigation API: Google Maps + OpenStreetMap (with Risk-Aware Routing)
------------------------------------------------------------------------------------------

Features:
- Users can input EITHER:
    1. Latitude/longitude coordinates (from, to), OR
    2. Google Maps-style place names/addresses (from, to)
- If risk zones (crowded, blocked, or unsafe areas) are given, routing will try to avoid them using OSMnx/NetworkX (OpenStreetMap custom logic).
- If no risk zones are given, or user prefers, Google Maps Directions API is used for fast, accurate routing.
- Returns route coordinates, distance, step-by-step instructions, and safety advisories.
- Real-time integration: designed for Simhastha 2028's smart safety needs.

Dependencies:
- pip install fastapi uvicorn geopy networkx osmnx numpy pydantic requests

Requirements:
- GOOGLE_MAPS_API_KEY in your environment (for Google Maps directions).
- For OSMnx, internet access is needed to fetch map data.
- This code does NOT store or process user data—privacy first!

Note:
- For hackathons, you may use a placeholder key for Google Maps, or mock the requests if needed.
"""

import os
import requests
from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import osmnx as ox
import networkx as nx
import numpy as np
from geopy.geocoders import Nominatim

router = APIRouter()

# --- Models ---
class RiskZone(BaseModel):
    lat: float
    lon: float

class NavigationRequest(BaseModel):
    # User can provide either coordinates OR place names/addresses for from/to
    from_lat: float = None
    from_lon: float = None
    to_lat: float = None
    to_lon: float = None
    from_place: str = None
    to_place: str = None
    risk_zones: list[RiskZone] = []  # List of locations to avoid

class NavigationMode(BaseModel):
    mode: str = "auto"  # "osm", "google", or "auto" (auto = best-fit logic)

# --- Config ---
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "YOUR_GOOGLE_MAPS_API_KEY")  # Replace for demo

# --- Geocoding ---
def geocode_address(address: str):
    """
    Uses Nominatim (OpenStreetMap) to geocode a place/address to coordinates.
    """
    geolocator = Nominatim(user_agent="surakshanet_nav")
    location = geolocator.geocode(address)
    if location:
        return float(location.latitude), float(location.longitude)
    else:
        return None, None

# --- Google Maps Directions API routing ---
def google_maps_route(from_lat, from_lon, to_lat, to_lon):
    """
    Fetches walking directions from Google Maps Directions API.
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{from_lat},{from_lon}",
        "destination": f"{to_lat},{to_lon}",
        "mode": "walking",  # or "driving"
        "key": GOOGLE_MAPS_API_KEY
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        raise Exception(f"Google Maps API error: {resp.status_code}")
    data = resp.json()
    if data['status'] != "OK":
        raise Exception(f"Google Maps error: {data.get('status')} - {data.get('error_message')}")
    # Parse route
    steps = []
    route_coords = []
    distance = 0
    for leg in data['routes'][0]['legs']:
        distance += leg['distance']['value']  # in meters
        for step in leg['steps']:
            # Instruction and end location
            steps.append(step['html_instructions'])
            loc = step['end_location']
            route_coords.append({"lat": loc['lat'], "lon": loc['lng']})
    return route_coords, distance, steps

# --- OSMnx/NetworkX custom routing ---
def osmnx_route(from_lat, from_lon, to_lat, to_lon, risk_zones):
    """
    Uses OpenStreetMap graph and custom logic to avoid risk zones.
    """
    # 1. Build map area
    lat_points = [from_lat, to_lat] + [z.lat for z in risk_zones]
    lon_points = [from_lon, to_lon] + [z.lon for z in risk_zones]
    lat_min, lat_max = min(lat_points) - 0.01, max(lat_points) + 0.01
    lon_min, lon_max = min(lon_points) - 0.01, max(lon_points) + 0.01
    G = ox.graph_from_bbox(lat_max, lat_min, lon_max, lon_min, network_type="walk")

    # 2. Find nearest nodes
    orig_node = ox.nearest_nodes(G, X=from_lon, Y=from_lat)
    dest_node = ox.nearest_nodes(G, X=to_lon, Y=to_lat)

    # 3. Penalize or remove nodes near risk_zones
    risk_nodes = set()
    for zone in risk_zones:
        node = ox.nearest_nodes(G, X=zone.lon, Y=zone.lat)
        risk_nodes.add(node)
        # Remove nodes in 30m radius for hackathon (can be tuned)
        nearby_nodes = [
            n for n, d in nx.single_source_dijkstra_path_length(G, node, cutoff=30).items()
        ]
        risk_nodes.update(nearby_nodes)
    G_safe = G.copy()
    G_safe.remove_nodes_from(risk_nodes)

    # 4. Route
    try:
        route = nx.shortest_path(G_safe, orig_node, dest_node, weight="length")
        route_type = "safe"
    except Exception:
        route = nx.shortest_path(G, orig_node, dest_node, weight="length")
        route_type = "risky"

    route_coords = [
        {"lat": float(G.nodes[n]["y"]), "lon": float(G.nodes[n]["x"])}
        for n in route
    ]
    instructions = [
        f"Proceed to ({pt['lat']:.5f}, {pt['lon']:.5f})"
        for pt in route_coords
    ]
    instructions[0] = "Start here"
    instructions[-1] = "You have arrived at your destination"
    route_length = int(sum(
        ox.utils_geo.great_circle_vec(
            route_coords[i]['lat'], route_coords[i]['lon'],
            route_coords[i+1]['lat'], route_coords[i+1]['lon']
        ) for i in range(len(route_coords)-1)
    ))
    return route_coords, route_length, instructions, route_type

@router.post("/route")
async def get_route(request: NavigationRequest, mode: NavigationMode = NavigationMode()):
    """
    Returns the safest or fastest route (user chooses). Accepts either lat/lon or Google Maps place names.
    If risk_zones are given, uses OpenStreetMap custom routing to avoid them.
    Otherwise, defaults to Google Maps Directions API.
    """
    try:
        # --- Normalize input: Get coordinates from place names if needed ---
        # If from_lat/lon not given but from_place is, geocode it.
        if (request.from_lat is None or request.from_lon is None) and request.from_place:
            lat, lon = geocode_address(request.from_place)
            if lat is None or lon is None:
                return JSONResponse(content={"status": "error", "message": f"Could not geocode source: {request.from_place}"}, status_code=400)
            request.from_lat, request.from_lon = lat, lon
        if (request.to_lat is None or request.to_lon is None) and request.to_place:
            lat, lon = geocode_address(request.to_place)
            if lat is None or lon is None:
                return JSONResponse(content={"status": "error", "message": f"Could not geocode destination: {request.to_place}"}, status_code=400)
            request.to_lat, request.to_lon = lat, lon

        # Check if coordinates are present after normalization
        if (request.from_lat is None or request.from_lon is None or request.to_lat is None or request.to_lon is None):
            return JSONResponse(content={"status": "error", "message": "Source and destination must be provided as coordinates or valid place names."}, status_code=400)

        # --- Routing logic selection ---
        # If risk_zones present, or mode is "osm", use OSMnx custom routing
        if (request.risk_zones and len(request.risk_zones) > 0) or mode.mode == "osm":
            route_coords, route_length, instructions, route_type = osmnx_route(
                request.from_lat, request.from_lon,
                request.to_lat, request.to_lon,
                request.risk_zones
            )
            msg = ("Safe route found avoiding risk zones." if route_type == "safe"
                   else "Warning: No safe route available, passing through risk zones!")
            return JSONResponse(content={
                "status": "success",
                "engine": "osmnx",
                "route_type": route_type,
                "distance_meters": route_length,
                "route": route_coords,
                "instructions": instructions,
                "risk_zones": [zone.dict() for zone in request.risk_zones],
                "message": msg
            })
        # Otherwise, use Google Maps Directions API
        elif mode.mode == "google" or mode.mode == "auto":
            route_coords, route_length, steps = google_maps_route(
                request.from_lat, request.from_lon,
                request.to_lat, request.to_lon
            )
            return JSONResponse(content={
                "status": "success",
                "engine": "google",
                "distance_meters": route_length,
                "route": route_coords,
                "instructions": steps,
                "risk_zones": [zone.dict() for zone in request.risk_zones],
                "message": "Google Maps route calculated. Check for risk overlays on the frontend!"
            })
        else:
            return JSONResponse(content={"status": "error", "message": "Invalid routing mode."}, status_code=400)

    except Exception as e:
        return JSONResponse(content={
            "status": "error",
            "message": f"Navigation failed: {str(e)}"
        }, status_code=500)