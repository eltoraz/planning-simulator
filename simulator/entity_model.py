"""
Entity structure and state tracking for plans
"""
from dataclasses import dataclass, field
from datetime import datetime
from haversine import inverse_haversine
from typing import Any, Optional, Self

from simulator.plan_model import MissionDef
from simulator.spacetime_model import Location, _future_time


@dataclass
class Entity:
    """Movement and platform details for an entity."""

    entity_name: str
    """Name of unit"""
    entity_id: Optional[int]
    """ID of unit"""
    mission: Optional[MissionDef] = None
    """
    Details of a Mission to create for this unit. If not set, no mission will be created for it
    directly.
    """
    start_location: Optional[Location] = None
    """
    Details of a Mission to create for this unit. If not set, no mission will be created for it
    directly.
    """
    platforms: dict[str, list[str]] = field(default_factory=dict)
    """Names of platforms (equipment) under this unit"""
    subordinates: list[Self] = field(default_factory=list)
    """Units under this one in the force structure"""

    @classmethod
    def from_json(cls,
                  json: Any) -> "Entity":
        """Create an Entity object from a generic object parsed from JSON."""
        name = json['entity_name'] if 'entity_name' in json else 'Anonymous Entity'
        entity_id = json['entity_id'] if 'entity_id' in json else None
        mission = MissionDef.from_json(json['mission']) if 'mission' in json else None
        start_location = Location.from_json(json['start_location']) if 'start_location' in json else None
        platforms = json['platforms'] if 'platforms' in json else dict()
        subordinates = [Entity.from_json(child) for child in json['subordinates']] if 'subordinates' in json else []
        entity = cls(name, entity_id, mission, start_location, platforms, subordinates)

        return entity


class EntityState:
    """Current position and completion time of last task for an entity."""

    def __init__(self,
                 entity: Entity,
                 dt: datetime,
                 start_location: Optional[Location]):
        self.entity = entity
        """Entity definition"""
        self.current_time = dt
        """Datetime of last completed task"""
        self.previous_location = start_location
        """Entity location prior to last completed task"""
        self.current_location = start_location
        """Current location as of last completed task"""

    def future_time(self,
                    delta_minutes: int) -> datetime:
        """Get future time relative to the entity state's current time"""
        return _future_time(self.current_time, delta_minutes)
    
    def advance_time(self,
                     delta_minutes: int):
        """Advance time by the specified number of minutes"""
        self.current_time = self.future_time(delta_minutes)

    def _relative_position(self,
                           distance: float,
                           heading: float) -> tuple[float, float]:
         """
         Get the coordinates for the entity if it were to move the given distance (km) in
         the specified direction (degrees clockwise from north)
         """
         if self.current_location:
            return inverse_haversine(self.current_location.coords(), distance, heading)
         else:
             raise RuntimeError("No location defined")

    def relative_position(self,
                          distance: float,
                          heading: float,
                          position_name: Optional[str] = None) -> Location:
         """
         Get the coordinates for the entity if it were to move the given distance (km) in the
         specified direction (degrees clockwise from north)
         """
         if self.current_location:
            new_lat, new_lon = inverse_haversine(self.current_location.coords(), distance, heading)
            return self.current_location.move_to(name=position_name, lat=new_lat, lon=new_lon)
         else:
             raise RuntimeError("No location defined")
    
    def scoot(self,
              distance: float,
              heading: float):
        """Move the entity the given distance in the specified direction"""
        self.previous_location = self.current_location
        self.current_location = self.relative_position(distance, heading, "Survivability position")

    def move_to(self,
                destination: Location):
        """Move the entity to the specified coordinates"""
        self.previous_location = self.current_location
        self.current_location = destination
