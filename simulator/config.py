import math
from datetime import datetime, timedelta, timezone
from typing import Optional


class PlanSettings:
    """Configuration for plan generation."""

    def __init__(self,
                 output_file: str = "output/plan_{}.json",
                 operation_name: str = "Simulation Plan",
                 operation_id: int = 1,
                 auto_number_id: bool = False,
                 operation_description: Optional[str] = None,
                 start_datetime: Optional[str] = None,
                 scoot_distance: float = 1.0,
                 scoot_heading: float = 0.0,
                 environment_factors: dict[str, str] = {},
                 time_series_environment_factors: dict[str, dict[str, str]] = {}):
        self.output_file = output_file
        """Filename to write plan JSON to (includes one parameter interpolated with start datetime)"""
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
