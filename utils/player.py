from ctypes import sizeof

from utils.memory import ProcessMemory
from utils.structs import C_UTL_VECTOR, Vec3

AIM_PUNCH_VECTOR_OFFSET = 0x88  # m_pAimPunchServices -> CUtlVector<QAngle> (not in client_dll.json)


def _read_aim_punch(mem: ProcessMemory, player_addr: int, offsets: dict[str, int]) -> tuple[float, float, float]:
    services_ptr = mem.read_ptr(player_addr + offsets["m_pAimPunchServices"])
    if not services_ptr:
        return (0.0, 0.0, 0.0)

    utlvec = mem.read_struct(services_ptr + AIM_PUNCH_VECTOR_OFFSET, C_UTL_VECTOR)
    if utlvec is None or not (0 < utlvec.Count < 0xFFFF) or not utlvec.Data:
        return (0.0, 0.0, 0.0)

    raw = mem.read_bytes(utlvec.Data + (utlvec.Count - 1) * sizeof(Vec3), sizeof(Vec3))
    if raw is None:
        return (0.0, 0.0, 0.0)

    v = Vec3.from_buffer_copy(raw)
    return (v.x, v.y, v.z)


def read_rcs_state(
    mem: ProcessMemory, player_addr: int, client: int, offsets: dict[str, int]
) -> tuple[int, tuple[float, float, float], float]:
    shots_fired = mem.read_i32(player_addr + offsets["m_iShotsFired"])
    sens_ptr = mem.read_ptr(client + offsets["dwSensitivity"])
    sensitivity = mem.read_f32(sens_ptr + offsets["dwSensitivity_sensitivity"]) if sens_ptr else 1.0
    return shots_fired, _read_aim_punch(mem, player_addr, offsets), sensitivity
