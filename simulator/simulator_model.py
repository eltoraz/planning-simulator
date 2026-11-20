"""
Simulate defined actions for hierarchy of entities, outputting a JSON object of the plan
"""
import json
from datetime import datetime
from haversine import inverse_haversine
from typing import Any, Optional

from simulator.config import PlanSettings
from simulator.entity_model import Entity, EntityState
from simulator.output_model import EquipmentRequirement, Operation, Mission, Payload, Plan, PlanningFactor, SupplyRequirement, Task
from simulator.plan_model import MovePlan, PlanDef, ScootPlan, TaskDef
from simulator.spacetime_model import Location, _future_time

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

    def scoot_coords(self,
                     start_location: Location) -> Location:
        """Calculate the coordinates to scoot to from a start location"""
        lat, lon = inverse_haversine(start_location.coords(), self.config.scoot_distance, self.config.scoot_heading)
        return start_location.move_to(
            name="Offset Position",
            lat=lat,
            lon=lon
        )

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
                       entity_id: Optional[int] = None,
                       **kwargs) -> dict[str, Any]:
        """Create a context dict for f-string interpolation"""
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
        if entity_id is not None:
            context["entity_id"] = entity_id
        for key, value in kwargs.items():
            if value:
                context[key] = value

        return context

    def create_task(self,
                    task_def: TaskDef,
                    context: dict[str, Any]) -> Task:
        """Create a Task based on a Task definition"""
        task_name = task_def.task_name
        task = Task(task_name, task_def.get_task_types(), context, self.next_id())

        if task_def.planning_factors:
            start_time = datetime.fromisoformat(context["start_time"])
            planning_factor = PlanningFactor(
                task_name,
                self.config.get_environment_factors(start_time),
                context,
                self.next_id())
            task.add_planning_factor(planning_factor)
        if task_def.has_equipment_requirements:
            for platform in task_def.equipment_requirements:
                equipment_requirement = EquipmentRequirement(
                    task_name,
                    platform,
                    context,
                    self.next_id())
                equipment_id = self.lookup_equipment_id(platform)
                if equipment_id is not None:
                    equipment_requirement.set_equipment_id(equipment_id)
                task.add_equipment_requirement(equipment_requirement)
        if task_def.has_supply_requirements:
            for supply_req in task_def.supply_requirements:
                supply_requirement = SupplyRequirement(
                    task_name,
                    supply_req.name,
                    supply_req.description,
                    supply_req.quantity,
                    context,
                    self.next_id())
                task.add_supply_requirement(supply_requirement)
        return task

    def create_plan(self,
                    action: PlanDef,
                    context: dict[str, Any]) -> Plan:
        """Create a Plan for the given action"""
        plan = Plan(
            plan_name=action.plan_name,
            plan_type=action.plan_type,
            context=context,
            plan_id=self.next_id()
        )

        start_time = datetime.fromisoformat(context["start_time"])
        running_time = start_time
        start_location = Location(context["start_location"], context["start_coordinates"]) if "start_location" in context else None

        tasks: list[Task] = []
        task_defs = [task for task in action.tasks]
        focus_id: Optional[int] = None
        if "entity_id" in context:
            focus_id = context["entity_id"]
            entity_specific_tasks = action.subordinate_tasks[focus_id] if focus_id in action.subordinate_tasks else []
            for task in entity_specific_tasks:
                task_defs.append(task)

        for task in task_defs:
            if focus_id and focus_id in task.exclusion_ids:
                continue

            if task.plan_start_offset:
                task_start_time = _future_time(start_time, task.plan_start_offset)
                task_end_time = _future_time(task_start_time, task.task_duration)
            else:
                task_start_time = running_time
                task_end_time = _future_time(task_start_time, task.task_duration)
                running_time = task_end_time
            if isinstance(action, ScootPlan) and start_location:
                task_end_location = self.scoot_coords(start_location)
            elif task.destination:
                task_end_location = task.destination
            else:
                task_end_location = start_location

            task_context = self.create_context(
                name=context["platform_name"],
                start_time=task_start_time,
                end_time=task_end_time,
                start_location=start_location,
                end_location=task_end_location,
                entity_id=context["entity_id"] if "entity_id" in context else None,
                entity_name=context["entity_name"] if "entity_name" in context else None
            )
            start_location = task_end_location
            tasks.append(create_task(task, task_context))

        plan.add_tasks(*tasks)

        # clamp the start/end times to the duration of the contained tasks
        task_start_times = [task.get_start_time() for task in tasks if task.has_start_time()]
        task_end_times = [task.get_end_time() for task in tasks if task.has_end_time()]
        if task_start_times and task_end_times:
            plan.set_start_time(format_datetime(min(task_start_times)))
            plan.set_end_time(format_datetime(max(task_end_times)))
        return plan

    def create_plan_for_entity(self,
                               entity: Entity,
                               action: PlanDef) -> list[Plan]:
        """Create a Plan for a single action for an entity"""
        entity_state = self.entity_states[entity.entity_name]
        start_time = entity_state.current_time
        start_location = entity_state.current_location

        entity_state.advance_time(action.duration)
        if isinstance(action, ScootPlan):
            entity_state.scoot(self.config.scoot_distance, self.config.scoot_heading)
        elif action.locations(entity.entity_id):
            entity_state.move_to(action.locations(entity.entity_id)[-1])

        end_time = entity_state.current_time
        end_location = entity_state.current_location

        plans: list[Plan] = []
        if action.platform_level_plan:
            # create one plan per platform
            platforms = {platform: [platform] + related for platform, related in entity.platforms.items()}
            entities_for_platform: dict[str, Entity] = {platform: entity for platform in entity.platforms}
            queue: list[Entity] = [subordinate for subordinate in entity.subordinates]
            while len(queue) > 0:
                subordinate = queue.pop(0)
                platforms.update({platform: [platform] + related for platform, related in subordinate.platforms.items()})
                entities_for_platform.update({platform: subordinate for platform in subordinate.platforms})
                queue += [child for child in subordinate.subordinates]
            if not platforms:
                print(f"Warning: entity {entity.entity_name} has no platforms defined for platform-level planning")
            for platform, equipment in platforms.items():
                platform_action = action.clone()
                platform_action.customize(equipment_requirements=equipment)
                entity_for_platform = entities_for_platform[platform]
                context = self.create_context(
                    name=platform,
                    entity_id=entity_for_platform.entity_id,
                    start_time=start_time,
                    end_time=end_time,
                    start_location=start_location,
                    end_location=end_location,
                    entity_name=entity_for_platform.entity_name
                )
                plan = create_plan(platform_action, context)
                if (plan.has_tasks()):
                    plans.append(plan)
                else:
                    plan_name=plan.data["name"]
                    print(f"Plan {plan_name} has no tasks, skipping")
        else:
            # one plan for this entity
            equipment = [platform for platform in entity.platforms] + [related for all_related in entity.platforms.values() for related in all_related]
            action.customize(equipment_requirments=equipment)
            context = create_context(
                name=entity.entity_name,
                entity_id=entity.entity_id,
                start_time=start_time,
                end_time=end_time,
                start_location=start_location,
                end_location=end_location,
                entity_name=entity.entity_name
            )
            plan = create_plan(action, context)
            if (plan.has_tasks()):
                plans.append(plan)
            else:
                plan_name=plan.data["name"]
                print(f"Plan {plan_name} has no tasks, skipping")

        return plans

    def create_mission_for_entity(self,
                                  entity_state: EntityState) -> Mission:
        """Create a containing Mission for an entity"""
        entity = entity_state.entity
        mission_def = entity.mission
        if not mission_def:
            raise RuntimeError("Can't create Mission for entity with no mission parameters")
        actions = mission_def.actions

        entities_to_plan: list[Entity] = []
        if not entity.subordinates or not mission_def.propagate:
            # if no subordinates: plan for this entity only
            entities_to_plan = [entity]
        elif entity is self.entity_hierarchy:
            # if entity is root: plan for subordinates that don't have their own separately-defined mission
            entities_to_plan = [subordinate for subordinate in entity.subordinates if not subordinate.mission]
        else:
            # else create a plan for each action for each subordinate
            entities_to_plan = [subordinate for subordinate in entity.subordinates]

        mission_start_time = entity_state.current_time
        mission_start_location = entity_state.current_location
        plans: list[Plan] = []
        # if entity has its own non-cascading tasks, create plans for them first
        for action in actions:
            if entity.entity_id and entity.entity_id in action.subordinate_tasks:
                entity_plans = self.create_plan_for_entity(entity, action)
                plans += entity_plans

        for planning_entity in entities_to_plan:
            for action in actions:
                entity_plans = self.create_plan_for_entity(planning_entity, action)
                plans += entity_plans

        plan_start_times = [plan.get_start_time() for plan in plans if plan.has_start_time()]
        start_time = min(plan_start_times) if plan_start_times else mission_start_time
        end_time = max([plan.get_end_time() for plan in plans if plan.has_end_time()])
        end_locations = [action.locations(entity.entity_id)[-1] for action in actions if isinstance(action, MovePlan) and action.locations(entity.entity_id)]
        end_location = end_locations[-1] if end_locations else None

        context = self.create_context(
            name=entity.entity_name,
            entity_id=entity.entity_id,
            start_time=start_time,
            end_time=end_time,
            start_location=mission_start_location,
            end_location=end_location
        )
        mission = Mission(mission_def.mission_name, mission_def.mission_type, context, self.next_id())
        mission.add_plans(*plans)

        return mission

    def audit(self,
              payload: Payload):
        """Audit the plan to make sure the hierarchy is sane"""
        type_count: dict[str, int] = dict()
        total = 0
        queue: list[Payload] = [payload]
        while len(queue) > 0:
            next_payload = queue.pop(0)
            for related in next_payload.relationships.values():
                queue += [child for child in related if isinstance(child, Payload)]
            payload_type = next_payload.__name__
            type_count[payload_type] = type_count[payload_type] + 1 if payload_type in type_count else 1
            total += 1

        print(f"Created plan hierarchy with {total} payloads")
        for payload_type, count in type_count.items():
            print(f"'{payload_type}' count: {count}")

    def write_json(self,
                   operation: Operation):
        """Write the Plan hierarchy to file in JSON format"""
        plan_datetime = self.config.start_datetime.strftime('%m_%d_%Y')
        output_filename = self.config.output_file.format(plan_datetime)
        with open(output_filename, 'w+t') as json_file:
            print('Writing operations plan JSON to {}'.format(output_filename))
            json.dump(operation.to_serializable(project), json_file, indent=4)

    def run_simulation():
        """Step through the simulated actions and build the plan hierarchy"""
        missions = [create_mission_for_unit(unit_state) for unit_state in entity_states.values() if unit_state.unit.mission]
        mission_end_times = [mission.get_end_time() for mission in missions]
        end_time: Optional[datetime] = max(mission_end_times) if mission_end_times else None

        unit = entity_hierarchy
        context = create_context(
            unit.entity_name,
            config.start_datetime,
            end_time=end_time,
            unit_id=unit.unit_id)
        operation = Operation(
            config.operation_type,
            config.operation_name,
            config.operation_description,
            config.operation_id,
            context)
        for mission in missions:
            mission.set_parent_id(operation.get_id())

        operation.add_missions(*missions)

        audit(operation)
        write_json(operation)
