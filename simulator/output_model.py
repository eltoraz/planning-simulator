"""
Output payload model.
"""

from datetime import datetime
from typing import Any, Optional

def _create_span(start_time: Optional[str], end_time: Optional[str]) -> dict[str, str]:
    """Create a serializable dict for a timespan"""
    if start_time and end_time:
        return {"startsAt": start_time, "endsAt": end_time}
    elif start_time:
        return {"startsAt": start_time, "endsAt": start_time}
    elif end_time:
        return {"startsAt": end_time, "endsAt": end_time}
    else:
        return {}


class Payload:
    """Base class for payloads."""
    start_time: Optional[str] = None
    """Plan element start time"""
    end_time: Optional[str] = None
    """Plan element end time"""

    def __init__(self,
                 root: bool,
                 data: dict,
                 focus_id: Optional[int] = None,
                 context: dict[str, Any] = {}):
        self.metadata: dict[str, Any] = {"root": root}

        self.data: dict[str, Any] = dict()
        if focus_id is not None:
            self.data["ID"] = focus_id

        self.data.update(data)

        self.relationships: dict[str, list[Payload]] = dict()

    def to_serializable(self) -> dict[str, Any]:
        """Return serializable dict of this payload"""
        metadata = {key: value for key, value in self.metadata.items()}
        data = {key: value for key, value in self.data.items()}

        payload: dict[str, Any] = {
            "metadata": metadata,
            "data": data
        }

        for relationship, nested in self.relationships.items():
            payload[relationship] = [child.to_serializable(project) for child in nested]

        return payload

    def has_start_time(self) -> bool:
        """Return whether the plan element has a start time set"""
        return self.start_time is not None

    def get_start_time(self) -> datetime:
        """Return the plan element's start time, if defined"""
        if self.start_time is not None:
            return datetime.fromisoformat(self.start_time)
        else:
            raise RuntimeError("Start time not set")

    def set_start_time(self,
                       new_start_time: str):
        """Set the plan element's start time"""
        self.start_time = new_start_time

    def has_end_time(self) -> bool:
        """Return whether the plan element has an end time set"""
        return self.end_time is not None
    
    def get_end_time(self) -> datetime:
        """Return the plan element's end time, if defined"""
        if self.end_time is not None:
            return datetime.fromisoformat(self.end_time)
        else:
            raise RuntimeError("End time not set")

    def set_end_time(self,
                     new_end_time: str):
        """Set the plan element's end time"""
        self.end_time = new_end_time

    def add_start_end_spatio_temporals(self,
                                       context: dict[str, Any]):
        """Add start/end times and locations to payload if present in context"""
        if "start_time" in context:
            self.set_start_time(context["start_time"])
        if "end_time" in context:
            self.set_end_time(context["end_time"])

        if "start_coordinates" in context:
            self.data["startLocation"] = context["start_coordinates"]
        if "destination_coordinates" in context:
            self.data["endLocation"] = context["destination_coordinates"]

    def add_related(self,
                    relationship: str,
                    *related: "Payload"):
        """Add vertices nested under this one."""
        if relationship not in self.relationships:
            self.relationships[relationship] = []
        for relative in related:
            self.relationships[relationship].append(relative)

    def get_related(self,
                    relationship: str) -> list["Payload"]:
        """Get related vertices"""
        if relationship in self.relationships:
            return self.relationships[relationship]
        else:
            return []

    def get_id(self) -> Optional[int]:
        """If the plan element has an ID set, return it, else return None"""
        return self.data["ID"] if "ID" in self.data else None


class PlanningFactor(Payload):
    """PlanningFactor payload representation."""

    def __init__(self,
                 task_name: str,
                 environment_factors: dict[str, str],
                 context: dict[str, Any],
                 focus_id: Optional[int] = None):
        name = "Environmental factors for Task: " + task_name.format(context)
        data: dict[str, Any] = {
            "name": name
        }
        for key, value in environment_factors.items():
            data[key] = value
        super().__init__(False,
                         data,
                         focus_id=focus_id,
                         context=context)


class SupplyRequirement(Payload):
    """SupplyRequirement payload representation."""

    def __init__(self,
                 task_name: str,
                 model: str,
                 description: str,
                 quantity: Optional[int],
                 context: dict[str, Any],
                 focus_id: Optional[int] = None):
        name = f"Supply Requirement for Task: {task_name.format(context)} : {model} : {description}"
        data: dict[str, Any] = {
            "name": name,
            "model": model,
            "description": description
        }

        super().__init__(False,
                         data,
                         focus_id=focus_id,
                         context=context)

        if quantity is not None:
            self.data["quantity"] = quantity

        requirement_schedule = _create_span(context["start_time"], context["end_time"])
        if requirement_schedule:
            self.data["requirementSchedule"] = requirement_schedule


class EquipmentRequirement(Payload):
    """EquipmentRequirement payload representation."""

    def __init__(self,
                 task_name: str,
                 platform: str,
                 context: dict[str, Any],
                 focus_id: Optional[int] = None):
        name = f"Equipment Requirement for Task: {task_name.format(context)} : {platform}"
        data = {"name": name}

        super().__init__(False,
                         data,
                         focus_id=focus_id,
                         context=context)

        requirement_schedule = _create_span(context["start_time"], context["end_time"])
        if requirement_schedule:
            self.data["requirementSchedule"] = requirement_schedule


class Task(Payload):
    """Task payload representation."""

    def __init__(self,
                 task_name: str,
                 task_type: str,
                 context: dict[str, Any],
                 focus_id: Optional[int] = None):
        name = "Task: " + task_name.format(context)
        # TODO use actual URN when available
        if "entity_id" in context:
            description = "{0[entity_id]} :: " + task_name
        else:
            description = task_name
        data: dict[str, Any] = {
            "name": name,
            "taskType": task_type
        }

        super().__init__(False,
                         data,
                         focus_id=focus_id,
                         context=context)
        self._task_type = task_type
        """Variable task type per project"""
        self.add_start_end_spatio_temporals(context)
        description = description.format(context)
        self.data["description"] = description

    def add_planning_factor(self,
                            planning_factor: PlanningFactor):
        """Add planning factor nested under this Task."""
        self.add_related("PlanningFactors", planning_factor)

    def add_supply_requirement(self,
                               supply_requirement: SupplyRequirement):
        """Add supply requirement nested under this Task."""
        self.add_related("SupplyRequirements", supply_requirement)

    def add_equipment_requirement(self,
                                  equipment_requirement: EquipmentRequirement):
        """Add equipment requirement nested under this Task."""
        self.add_related("EquipmentRequirements", equipment_requirement)


class Plan(Payload):
    """Plan payload representation."""

    def __init__(self,
                 plan_name: str,
                 context: dict[str, Any],
                 plan_type: Optional[str] = None,
                 focus_id: Optional[int] = None):
        name = "Plan: " + plan_name.format(context)
        data: dict[str, Any] = {
            "name": name,
            "planType": plan_type if plan_type else "UNKNOWN"
        }

        super().__init__(False,
                         data,
                         focus_id=focus_id,
                         context=context)
        self.add_start_end_spatio_temporals(context)
    
    def add_tasks(self,
                  *tasks: Task):
        """Add tasks nested under this Plan.
        """
        self.add_related("Tasks", *tasks)

    def has_tasks(self) -> bool:
        """Return true iff this Plan has nested Tasks."""
        if self.get_related("Tasks"):
            return True
        else:
            return False


class Mission(Payload):
    """Mission payload representation."""

    def __init__(self,
                 mission_name: str,
                 mission_type: str,
                 context: dict[str, Any],
                 focus_id: Optional[int] = None):
        name = "Mission: " + mission_name.format(context)
        data: dict[str, Any] = {
            "name": name,
            "missionType": mission_type
        }

        super().__init__(False,
                         data,
                         focus_id=focus_id,
                         context=context)
        self.add_start_end_spatio_temporals(context)

    def add_plans(self,
                  *plans: Plan):
        """Add plans nested under this Mission."""
        self.add_related("Plans", *plans)


class Operation(Payload):
    """Operation payload representation."""

    def __init__(self,
                 operation_type: str,
                 operation_name: str,
                 operation_description: str,
                 focus_id: int,
                 context: dict[str, Any]):
        data: dict[str, Any] = {
            "name": operation_name.format(context),
            "operationType": operation_type,
        }

        super().__init__(True,
                         data,
                         focus_id=focus_id,
                         context=context)
        self.add_start_end_spatio_temporals(context)

        description = operation_description.format(context)
        self.data["description"] = description

    def add_missions(self,
                     *missions: Mission):
        """Add missions nested under this Operation."""
        self.add_related("Missions", *missions)
