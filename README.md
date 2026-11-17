# Introduction

Proof-of-concept reimplementation of an entity action simulator originally written for a proprietary planning engine. The tool takes as input a hierarchy of entities (and optionally, their equipment) along with associated actions they are desired to take over the course of the simulation; output is a nested JSON structure of plans and tasks assigned to each entity platform. The primary use case is tracking movement of multiple entities over time; these entities may move individually or in groups.

# Third-party libraries

[haversine](https://pypi.org/project/haversine/) (latitude/longitude distance calculation)

# Setup

Setup a venv and install dependencies before first use:
```shell
python3 -m venv .venv/
source .venv/bin/activate
pip install -r requirements.txt
```

In subsequent sessions, re-activating the venv is sufficient:
```shell
source .venv/bin/activate
```