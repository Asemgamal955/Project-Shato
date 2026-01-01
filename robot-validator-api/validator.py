from pydantic import BaseModel
from typing import Optional, Literal

# ====== Constants ======
ALLOWED_ROUTES = ["first_floor", "bedrooms", "second_floor"]
ALLOWED_SPEEDS = ["slow", "medium", "fast"]

# ====== Pydantic Models for Each Command ======

class MoveToParams(BaseModel):
    x: float
    y: float

class RotateParams(BaseModel):
    angle: float
    direction: Literal["clockwise", "counter-clockwise"]

class StartPatrolParams(BaseModel):
    route_id: Literal["first_floor", "bedrooms", "second_floor"]
    speed: Optional[Literal["slow", "medium", "fast"]] = "medium"
    repeat_count: Optional[int] = 1

class Command(BaseModel):
    command: Literal["move_to", "rotate", "start_patrol"]
    command_params: dict


# ====== Validation Logic ======

def validate_command(cmd: Command):
    """
    Validate and parse command parameters based on command type.
    Returns parsed params (dict) if valid, raises ValueError if invalid.
    """
    if cmd.command == "move_to":
        params = MoveToParams(**cmd.command_params)
        return params.dict()

    elif cmd.command == "rotate":
        params = RotateParams(**cmd.command_params)
        return params.dict()

    elif cmd.command == "start_patrol":
        params = StartPatrolParams(**cmd.command_params)
        return params.dict()

    else:
        raise ValueError(f"Unknown command {cmd.command}") 