import argparse
import json
from typing import Any

from simulator.config import PlanSettings
from simulator.entity_model import Entity
from simulator.simulator_model import Simulator

def _simulator_args() -> argparse.Namespace:
    """Define and parse arguments to configure simulator if running module directly"""
    parser = argparse.ArgumentParser(
            prog='Entity Plan Simulator',
            description='Simulate actions for a hierarchy of entities')
    parser.add_argument('-i', '--input',
            dest='input_file',
            default='input/entities.json',
            help='Path to input file containing entity/action definitions; default="input/entities.json')
    parser.add_argument('-o', '--output',
            dest='output_file',
            default='output/plan_{}.json',
            help='Path to output file (includes one parameter interpolated with start datetime, denoted with "{}"); default="output/plan_{}.json"')
    parser.add_argument('--name',
            dest='operation_name',
            default='Simulation Plan',
            help='Name of top-level plan element in output hierarchy; default="Simulation Plan"')
    parser.add_argument('--id',
            dest='operation_id',
            type=int,
            default=1,
            help='ID to assign to top-level plan element, and to use as start for auto-numbering; default=1')
    parser.add_argument('--auto-number',
            dest='auto_number_id',
            action='store_true',
            help='Enable auto-numbering of nested plan objects; disabled if omitted')
    parser.add_argument('--description',
            dest='operation_description',
            help='Description for top-level plan element (optional)')
    parser.add_argument('--start-time',
            dest='start_datetime',
            help='ISO 8601 datetime string of plan start; if omitted, defaults to current system time')
    parser.add_argument('--scoot-distance',
            type=float,
            help='Distance (in kilometers) to use for small scoot actions; default=1.0')
    parser.add_argument('--scoot-heading',
            type=float,
            help='Heading (degrees clockwise from north) to direct scoot actions; default=0.0')
    parser.add_argument('--environment-factors-file',
            help='Filename of JSON-formatted environment factors to apply to plan')
    parser.add_argument('--time-series-environment-factors',
            action='store_true',
            help='Flag indicating whether environment factors are provided with timestamps (i.e., change over the course of the simulation)')
    return parser.parse_args()

def _read_json(input_filename: str) -> Any:
    json_contents = {}
    with open(input_filename, 'rt') as input_file:
        print(f'Importing JSON from input file {input_filename}')
        json_contents = json.load(input_file)
    return json_contents

args = _simulator_args()

environment_factors_file = args.environment_factors_file
environment_factors = dict()
time_series_environment_factors = dict()
if environment_factors_file:
    if args.time_series_environment_factors:
        time_series_environment_factors = _read_json(environment_factors_file)
    else:
        environment_factors = _read_json(environment_factors_file)

entity_hierarchy = Entity.from_json(_read_json(args.input_file))

settings = PlanSettings(args.output_file,
        args.operation_name,
        args.operation_id,
        args.auto_number_id,
        args.operation_description,
        args.start_datetime,
        args.scoot_distance,
        args.scoot_heading,
        environment_factors,
        time_series_environment_factors)
# TODO handle equipment loading
simulator = Simulator(settings, entity_hierarchy, None)
simulator.run_simulation()
