"""
Common data structures and config
"""
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

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

    # TODO rename to str_tuple
    def srf_format(self) -> str:
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


class PlanSettings:
    """Configuration for plan generation."""

    def __init__(self,
                 operation_name: str,
                 operation_id: int,
                 auto_number_id: bool = False,
                 operation_description: Optional[str] = None,
                 start_datetime: Optional[str] = None,
                 scoot_distance: float = 1.0,
                 scoot_heading: float = 0.0,
                 environment_factors: dict[str, str] = {},
                 time_series_environment_factors: dict[str, dict[str, str]] = {}):
        self.operation_name = operation_name
        """Name of operation"""
        self.operation_id = operation_id
        """Plan ID to use for operation"""
        self.operation_description = operation_description if operation_description else operation_name
        """Operation summary"""
        if start_datetime:
            self.start_datetime = datetime.fromisoformat(start_datetime)
            """Operation start date/time"""
        else:
            today = datetime.today()
            self.start_datetime = datetime(today.year, today.month, today.day, tzinfo=timezone.utc) + timedelta(days=7, hours=6)

        self.scoot_distance = scoot_distance
        """Distance to move platforms for short "scoot" maneuvers (kilometers, default 1.0)"""
        self.scoot_heading = math.radians(scoot_heading)
        """Heading to direct "scoot" maneuvers (degrees clockwise from north, default 0.0)"""

        if len(time_series_environment_factors) > 0:
            self._time_series_environment_factors: dict[datetime, dict[str, str]] = {datetime.fromisoformat(key): value for key, value in time_series_environment_factors.items()}
        elif len(environment_factors) > 0:
            self._time_series_environment_factors = {self.start_datetime: environment_factors}
        else:
            self._time_series_environment_factors = {self.start_datetime: _default_environment_factors}

        self.auto_number_id = auto_number_id
        """Flag indicating whether to generate IDs for nested vertices"""
        self._next_id = operation_id + 1

    def next_id(self) -> int:
        """Get next ID for autonumbering"""
        if self.auto_number_id:
            next_available = self._next_id
            self._next_id += 1
            return next_available
        else:
            raise RuntimeError("Auto ID numbering not enabled")

    def get_environment_factors(self,
                                dt: datetime) -> dict[str, str]:
        """Get environment factors corresponding to the specified start time."""
        sorted_factors = dict(sorted(self._time_series_environment_factors.items()))
        env_factor_match: dict[str, str] = [factor for factor in sorted_factors.values()][0]
        for factor_dt, factors in sorted_factors.items():
            if factor_dt > dt:
                break
            env_factor_match = factors

        return env_factor_match
