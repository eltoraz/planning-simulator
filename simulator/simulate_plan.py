"""
Simulate defined actions for hierarchy of entities, outputting a JSON object of the plan
"""
import json
from datetime import datetime
from haversine import inverse_haversine
from typing import Any, Optional

from config import PlanSettings
from entity_model import Entity, EntityState
from output_model import EquipmentRequirement, Operation, Mission, Payload, Plan, PlanningFactor, SupplyRequirement, Task
from plan_model import MovePlan, PlanDef, ScootPlan, TaskDef
from spacetime_model import Location, _future_time

# TODO get config overrides from command-line args

def short_datetime(dt: datetime) -> str:
    """Return a string of a datetime's hour and minute fields concatenated together"""
    return dt.strftime('%H%M')

def format_datetime(dt: datetime) -> str:
    """Return an ISO format string representation of the datetime"""
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')


# TODO refactor equipment_ids
class Simulator:
    """Main simulator class"""

    def __init__(self,
                 config: PlanSettings,
                 entity_hierarchy: Entity,
                 equipment_ids: Optional[dict[str, int]]):
        self.config = config
        """Simulator configuration"""
        self.entity_states: dict[str, EntityState] = dict()
        """Tracker of entity states by unique entity names"""
        self.entity_hierarchy = entity_hierarchy
        """Original hierarchy of entities with their assigned actions"""
        self.equipment_ids: dict[str, int] = equipment_ids if equipment_ids else dict()
        """Mapping of equipment names to IDs"""

        self.init_entity_states()

    def recurse_over_entities(self,
                              entity: Entity,
                              parent_location: Optional[Location]):
        """Recursively traverse entity hierarchy to initialize their state in the tracker"""
        start_location = entity.start_location if entity.start_location else parent_location
        if not start_location:
            print(f"Warning: no start location defined or inherited for entity {entity.entity_name}")

        entity_states[entity.entity_name] = EntityState(entity, self.config.start_datetime, start_location)
        for subordinate in entity.subordinates:
            recurse_over_entities(subordinate, start_location)

    def init_entity_states(self):
        """Initialize entity hierarchy"""
        recurse_over_entities(self.entity_hierarchy, None)

    def next_id(self) -> int | None:
        """Get next autonumber ID if enabled"""
        return self.config.next_id() if self.config.auto_number_id else None

    def lookup_equipment_id(self,
                            platform_name: str) -> Optional[int]:
        """Return the ID of the equipment corresponding to the named platform, or None if not defined in the mapping"""
        return self.equipment_ids[platform_name] if platform_name in self.equipment_ids else None

    def create_context(self,
                       name: str,
                       start_time: datetime,
                       end_time: Optional[datetime] = None,
                       start_location: Optional[Location] = None,
                       end_location: Optional[Location] = None,
                       unit_id: Optional[int] = None,
                       **kwargs) -> dict[str, Any]:
        context: dict[str, Any] = {
            "platform_name": name,
            "start_time_short": short_datetime(start_time),
            "start_time": format_datetime(start_time)
        }
        if end_time:
            context["end_time"] = format_datetime(end_time)
        if start_location:
            context["start_location"] = start_location.name
            context["start_coordinates"] = start_location.srf_format()
        if end_location:
            context["destination"] = end_location.name
            context["destination_coordinates"] = end_location.srf_format()
        if unit_id is not None:
            context["unit_id"] = unit_id
        for key, value in kwargs.items():
            if value:
                context[key] = value

        return context
