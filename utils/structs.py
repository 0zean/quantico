from ctypes import Structure, Union, c_float, c_long, c_uint64, c_ulong, c_void_p
from dataclasses import dataclass


class Vec3(Structure):
    _fields_ = [("x", c_float), ("y", c_float), ("z", c_float)]


class Vec2(Structure):
    _fields_ = [("x", c_float), ("y", c_float)]


class C_UTL_VECTOR(Structure):
    _fields_ = [("Count", c_uint64), ("Data", c_uint64)]


class MOUSEINPUT(Structure):
    _fields_ = [
        ("dx", c_long),
        ("dy", c_long),
        ("mouseData", c_ulong),
        ("dwFlags", c_ulong),
        ("time", c_ulong),
        ("dwExtraInfo", c_void_p),  # ULONG_PTR: pointer-sized integer, not a pointer
    ]


class INPUT(Structure):
    class INPUT_UNION(Union):
        _fields_ = [("mi", MOUSEINPUT)]

    _anonymous_ = ("u",)
    _fields_ = [("type", c_ulong), ("u", INPUT_UNION)]


@dataclass(slots=True)
class EntitySnapshot:
    """Game-state snapshot for a single entity"""

    address: int
    team: int
    health: int
    name: str
    bones: dict[str, tuple[float, float, float]]


@dataclass(slots=True, frozen=True)
class ScreenSize:
    width: int
    height: int
