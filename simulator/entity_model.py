"""
Entity structure and state tracking for plans
"""
from dataclasses import dataclass, field
from datetime import datetime
from haversine import inverse_haversine
from typing import Optional, Self

from plan_defs import Location, _future_time
