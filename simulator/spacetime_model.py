"""
Common data structures and config
"""
from datetime import datetime, timedelta
from typing import Any, Optional

_default_environment_factors: dict[str, str] = {
    "terrain": "DEFAULT",
    "weather": "DEFAULT"
}

def _format_position(lat: float,
                     lon: float,
                     alt: float) -> str:
    """Format the coordinates in a "(lat,lon,alt)" string"""
    return f'({lat},{lon},{alt})'

def _future_time(dt: datetime,
                 delta_minutes: int) -> datetime:
    """Get the future time the specified number of minutes later than the datetime"""
    return dt + timedelta(minutes=delta_minutes)
    

class Location:
    """Location used in planning"""

    def __init__(self,
                 name: str,
                 coordinates: str,
                 description: str = ""):
        self.name = name
        """Location name, for display in plan element names/descriptions"""
        lat, lon, alt = coordinates.replace('(', '').replace(')', '').replace(' ', '').split(',')
        self.lat, self.lon, self.alt = float(lat), float(lon), float(alt)
        """Location coordinates and altitude"""
        self.description = description
        """Location long description"""

    def coords(self) -> tuple[float, float]:
        """Get the location's latitude/longitude as a tuple"""
        return self.lat, self.lon

    def str_tuple(self) -> str:
        """Format the location's coordintes in a "(lat,lon,alt)" string"""
        return _format_position(self.lat, self.lon, self.alt)

    def move_to(self,
                name: Optional[str] = None,
                lat: Optional[float] = None,
                lon: Optional[float] = None,
                alt: Optional[float] = None) -> "Location":
        """Return a new Location representing a move from the current coordinates to the specified ones."""
        new_name = name if name else self.name
        new_lat = lat if lat else self.lat
        new_lon = lon if lon else self.lon
        new_alt = alt if alt else self.alt
        return Location(new_name, _format_position(new_lat, new_lon, new_alt))

    @classmethod
    def from_json(cls,
                  json: Any) -> "Location":
        """Create a Location object from a generic object parsed from JSON."""
        name = json['name'] if 'name' in json else 'Anonymous Location'
        coordinates = json['coordinates'] if 'coordinates' in json else '(0.0,0.0,0.0)'
        description = json['description'] if 'description' in json else ''
        return cls(name, coordinates, description)

