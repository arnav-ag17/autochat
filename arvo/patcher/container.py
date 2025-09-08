from __future__ import annotations
from typing import List, Tuple


def generate_container_cmd(start_command: str, port: int) -> (List[str], List[str]):
    parts = start_command.split()
    notes = ["container cmd generated"]
    # Keep command minimal; task def can inject PORT env; avoid hardcoding HOST
    return parts, notes


def generate_container_entrypoint(start_command: str) -> (List[str], List[str]):
    # For simplicity, no separate entrypoint vs cmd split required in v1
    parts = []
    return parts, ["no custom entrypoint (using default image entrypoint)"]
