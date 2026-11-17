"""
Plan structure model for internal simulation use
"""
from dataclasses import dataclass, field
from typing import Any, Optional

from plan_defs import Location


@dataclass
class SupplyReqDef:
    """Task supply requirement definition"""

    name: str
    """Supply requirement name"""
    description: str
    """Supply requirement description"""
    quantity: Optional[int] = None
    """Quantity required (optional)"""


@dataclass
class TaskDef:
    """Parameters for a task."""

    task_name: str
    """Task name (with substitutable arguments)"""
    task_type: str
    """Task type"""
    task_duration: int
    """Task duration (minutes)"""
    plan_start_offset: Optional[int] = None
    """
    Offset (minutes) from start of plan to start this task (runs concurrently with others; if
    not set, indicates the task starts immediately after the previous non-concurrent one)
    """
    planning_factors: bool = False
    """Flag to generate planning factors for the task"""
    has_equipment_requirements: bool = False
    """Flag to generate equipment requirements for the task"""
    equipment_requirements: list[str] = field(default_factory=list)
    """Names of equipment to create equipment requirements for"""
    has_supply_requirements: bool = False
    """Flag to generate supply requirements for the task"""
    supply_requirements: list[SupplyReqDef] = field(default_factory=list)
    """Supply requirements for this task"""
    destination: Optional[Location] = None
    """Location the performer will arrive at by the end of this task"""
    exclusion_ids: list[int] = field(default_factory=list)
    """IDs of subordinate entities this task should not be applied to"""

    def clone(self) -> "TaskDef":
        """Get a deep copy of this TaskDef"""
        return TaskDef(self.task_name,
                       self.task_type,
                       self.task_duration,
                       self.plan_start_offset,
                       self.planning_factors,
                       self.has_equipment_requirements,
                       list(self.equipment_requirements),
                       self.has_supply_requirements,
                       list(self.supply_requirements),
                       self.destination)

    def add_equipment_requirements(self,
                                   *equipment_names: str):
        """Add equipment requirements for this task"""
        for equipment in equipment_names:
            self.equipment_requirements.append(equipment)

    def add_supply_requirements(self,
                                *supply_requirements: SupplyReqDef):
        """Add supply requirements for this task"""
        for supply in supply_requirements:
            self.supply_requirements.append(supply)

    # TODO remove
    def get_task_types(self) -> str:
        return self.task_type

    @classmethod
    def recon_task(cls,
                   task_name: str,
                   task_duration: int,
                   plan_start_offset: Optional[int] = None) -> "TaskDef":
        """Create a recon task (configured with project-specific task types)"""
        return TaskDef(task_name=task_name,
                       task_type="RECON",
                       task_duration=task_duration,
                       plan_start_offset=plan_start_offset)


class MoveTask(TaskDef):
    """Task encompassing a movement action"""
    _default_name = "Move {0[platform_name]} from {0[start_location]} to {0[destination]} - {0[start_time_short]}"

    def __init__(self,
                 destination: Location,
                 duration: int,
                 offset: Optional[int] = None):
        super().__init__(
            task_name=self._default_name,
            task_type="MOVE",
            task_duration=duration,
            plan_start_offset=offset,
            destination=destination
        )


class PlanDef:
    """Common parameters for missions and plans of a particular type."""

    def __init__(self,
                 plan_name: str,
                 plan_type: str,
                 delay: int = 0,
                 platform_level_plan: bool = False,
                 tasks: list[TaskDef] = list(),
                 subordinate_tasks: dict[int, list[TaskDef]] = dict()):
        self.plan_name = plan_name
        """Plan name (with substitutable arguments)"""
        self.plan_type = plan_type
        """Plan type"""
        seq_task_durations = [task.task_duration for task in tasks if not task.plan_start_offset]
        offset_durations = [task.plan_start_offset + task.task_duration for task in tasks if task.plan_start_offset]
        if seq_task_durations and offset_durations:
            self.duration = max(sum(seq_task_durations), max(offset_durations))
            """Plan duration (minutes)"""
        elif seq_task_durations:
            self.duration = sum(seq_task_durations)
        elif offset_durations:
            self.duration = max(offset_durations)
        else:
            print("Creating PlanDef with 0 duration")
            self.duration = 0

        self.delay = delay
        """Delay before start of plan (minutes)"""
        self.platform_level_plan = platform_level_plan
        """Flag indicating whether they plan should be instantiated per-platform instead of per-unit"""
        self.tasks = tasks
        """Tasks nested under each plan (if platform_plan_name is present,
        indicates the tasks are performed by an individual platform, otherwise the unit as a whole)"""
        self.subordinate_tasks = subordinate_tasks
        """Tasks to be added only for the subordinate with matching ID"""

    def clone(self) -> "PlanDef":
        """Get a clone of this PlanDef"""
        return PlanDef(self.plan_name,
                       self.plan_type,
                       self.delay,
                       self.platform_level_plan,
                       [task.clone() for task in self.tasks])

    def add_task(self,
                 task: TaskDef,
                 index: Optional[int] = None):
        """Add a task"""
        if index is None:
            self.tasks.append(task)
        else:
            self.tasks.insert(index, task)
        self.duration += task.task_duration

    # TODO (old) need to make sure tasks are sorted chronologically
    def locations(self,
                  unit_id: Optional[int] = None) -> list[Location]:
        """Get a sequential list of all the locations visited over the represented Plan"""
        locs = [task.destination for task in self.tasks if task.destination]
        if unit_id and unit_id in self.subordinate_tasks:
            locs.extend(task.destination for task in self.subordinate_tasks[unit_id] if task.destination)
            pass
        return locs

    def customize(self, **kwargs) -> "PlanDef":
        """Customize the plan settings with the provided parameters"""
        if "name" in kwargs:
            self.plan_name = kwargs["name"]
        elif "plan_name" in kwargs:
            self.plan_name = kwargs["plan_name"]

        if "duration" in kwargs:
            self.duration = kwargs["duration"]
        if "delay" in kwargs:
            self.delay = kwargs["delay"]
        if "platform_level_plan" in kwargs:
            self.platform_level_plan = kwargs["platform_level_plan"]

        if "tasks" in kwargs:
            extra_tasks = kwargs["tasks"]
            if isinstance(extra_tasks, list):
                for task in extra_tasks:
                    if isinstance(task, TaskDef):
                        self.add_task(task)
            else:
                print("Unsupported value in customization 'tasks'")

        if "equipment_requirements" in kwargs:
            equipment: list[str] = kwargs["equipment_requirements"]
            for task in self.tasks:
                if task.has_equipment_requirements:
                    task.add_equipment_requirements(*equipment)

        # TODO this currently gets supply requirements only by core task type
        if "supply_requirements" in kwargs:
            supplies: dict[str, list[SupplyReqDef]] = kwargs["supply_requirements"]
            for task in self.tasks:
                if task.has_equipment_requirements and task.task_type in supplies:
                    supplies_for_type: list[SupplyReqDef] = supplies[task.get_task_types().default()]
                    task.add_supply_requirements(*supplies_for_type)

        return self


class MissionDef:
    """Parameters for a mission"""

    def __init__(self,
                 mission_name: str,
                 mission_type: Optional[str] = None,
                 actions: list[PlanDef] = [],
                 propagate: bool = True):
        self.mission_name = mission_name
        """Mission name (with substitutable arguments)"""
        self.mission_type = mission_type if mission_type else 'MOVE'
        """Mission type (default 'MOVE')"""
        self.actions = actions
        """Tasks planned for this unit or its subordinates"""
        self.propagate = propagate
        """Flag controlling whether to propagate tasks to the unit's subordinates"""

    def with_actions(self,
                     actions: list[PlanDef],
                     append_actions: bool = True) -> "MissionDef":
        """
        Return a copy of this MissionDef with the provided actions added. If the 'append_actions'
        flag is False, use only the provided actions instead.
        """
        new_actions = self.actions + actions if append_actions else actions
        return MissionDef(self.mission_name, self.mission_type, new_actions)


class MovePlan(PlanDef):
    """Movement plan plan that may incorporate multiple intermediate steps"""
    _default_plan_name = "Move {0[platform_name]} to {0[destination]} - {0[start_time_short]}"
    _default_plan_type = "MOVE"
    _default_task_name = "Move {0[platform_name]} from {0[start_location]} to {0[destination]} - {0[start_time_short]}"
    _default_tasks = [
        TaskDef.recon_task("{0[platform_name]} RECON - {0[start_time_short]}", 30)
    ]

    def __init__(self,
                 include_recon: bool = True):
        super().__init__(
            plan_name=self._default_plan_name,
            plan_type=self._default_plan_type,
            tasks=list(self._default_tasks) if include_recon else list()
        )
        self._include_recon = include_recon
        """Flag indicating whether this plan should include the recon task at the end"""
        
    def _add_location(self,
                      location: Location | MoveTask):
        if isinstance(location, Location):
            move_task = TaskDef(
                task_name=self._default_task_name,
                task_type="MOVE",
                task_duration=30,
                destination=location
            )
        else:
            move_task = location

        self.add_task(move_task, index=-1 if self._include_recon else None)

    def customize(self, **kwargs) -> PlanDef:
        if "locations" in kwargs:
            locations = kwargs["locations"]
            if isinstance(locations, list):
                for location in locations:
                    if isinstance(location, Location):
                        self._add_location(location)
                    elif isinstance(location, MoveTask):
                        self._add_location(location)
                    else:
                        print("Move plan has unknown variable in 'locations' list")
            elif isinstance(locations, Location):
                print("For consistency, 'locations' in Move plans should be a list of locations")
                self._add_location(locations)
            else:
                print("Unknown variable type in Move plan 'locations'")

        super().customize(**kwargs)
        self.duration = sum([task.task_duration for task in self.tasks])
        return self
    

class ScootPlan(PlanDef):
    """Scoot (small movement of a predefined vector) plan"""

    def __init__(self):
        super().__init__(
            plan_name="{0[platform_name]} Survivablity Move: {0[start_time_short]}",
            plan_type="OTHER",
            tasks=[
                TaskDef(
                    task_name="{0[platform_name]} Survivablity Move: {0[start_time_short]}",
                    task_type="MANEUVER",
                    task_duration=10)
            ]
        )


class PresetPlanFactory:
    """Factory for creating parameterized Plans from templates"""

    @classmethod
    def _customize(cls,
                   plan: PlanDef,
                   parameters: dict[str, Any]) -> PlanDef:
        return plan.customize(**parameters)

    @classmethod
    def move_plan(cls,
                  include_recon: bool = True,
                  parameters: dict[str, Any] = {}) -> PlanDef:
        return cls._customize(MovePlan(include_recon), parameters)

    @classmethod
    def scoot_plan(cls,
                   parameters: dict[str, Any] = {}) -> PlanDef:
        return cls._customize(ScootPlan(), parameters)

    @classmethod
    def move_task(cls,
                  destination: Location,
                  duration: int,
                  offset: Optional[int] = None) -> MoveTask:
        return MoveTask(destination, duration, offset)
