from mcp.server.fastmcp import FastMCP
import httpx

def register_geo_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def geocode_location(place: str) -> dict:
        """
        Convert a place name (e.g., 'Seattle') into coordinates (lat/lon).
        Uses OpenStreetMap Nominatim.
        """
        url = "https://nominatim.openstreetmap.org/search"
        r = httpx.get(
            url,
            params={"q": place, "format": "json", "limit": 1},
            headers={"User-Agent": "mcp-weather-agent/1.0"},
            timeout=20.0,
        )
        if r.status_code != 200:
            return {"error": f"Geocoding failed: HTTP {r.status_code}"}

        data = r.json()
        if not data:
            return {"error": f"No results found for '{place}'"}

        item = data[0]
        return {
            "place": place,
            "display_name": item.get("display_name", ""),
            "latitude": float(item["lat"]),
            "longitude": float(item["lon"]),
        }
