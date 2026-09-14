import struct

import pymem.exception

from utils.memory import ProcessMemory
from utils.structs import EntitySnapshot

LIFE_ALIVE = 0
MAX_PLAYERS = 64
INVALID_HANDLE = -1  # CHandle 0xFFFFFFFF read as signed i32
ENTITY_IDENTITY_STRIDE = 0x70  # sizeof(CEntityIdentity): last field m_pNextByClass at 0x68, 8 bytes
BONE_STRIDE = 0x20  # bytes per bone entry; only the leading xyz floats are read
BONE_ARRAY_PTR_OFFSET = 0x80  # m_modelState -> bone array pointer (not in client_dll.json; recheck after game updates)


class EntityManager:
    """Reads all visible entities at once"""

    __slots__ = ("_mem", "_client", "_offsets", "_bone_indices")

    def __init__(self, mem: ProcessMemory, client: int, offsets: dict[str, int], bone_indices: dict[str, int]) -> None:
        self._mem = mem
        self._client = client
        self._offsets = offsets
        self._bone_indices = bone_indices

    def _local_team(self) -> tuple[int, int]:
        pawn = self._mem.read_ptr(self._client + self._offsets["dwLocalPlayerPawn"])
        if not pawn:
            return 0, -1
        return pawn, self._mem.read_u8(pawn + self._offsets["m_iTeamNum"])

    def _batch_bones(self, bone_matrix: int) -> dict[str, tuple[float, float, float]]:
        indices = self._bone_indices
        if not indices:
            return {}

        min_idx = min(indices.values())
        max_idx = max(indices.values())
        base_offset = min_idx * BONE_STRIDE
        total_bytes = (max_idx - min_idx + 1) * BONE_STRIDE

        region = self._mem.read_region(bone_matrix + base_offset, total_bytes)
        if region is None:
            return {}

        bones: dict[str, tuple[float, float, float]] = {}
        for name, idx in indices.items():
            off = (idx - min_idx) * BONE_STRIDE
            x, y, z = struct.unpack_from("fff", region, off)
            bones[name] = (x, y, z)
        return bones

    def get_entities(self) -> list[EntitySnapshot]:
        mem = self._mem
        off = self._offsets
        snapshots: list[EntitySnapshot] = []

        ent_list = mem.read_ptr(self._client + off["dwEntityList"])
        if not ent_list:
            return snapshots

        try:
            local_addr, local_team = self._local_team()
        except pymem.exception.MemoryReadError:
            return snapshots
        if not local_addr:
            # main menu / between rounds: no local pawn means no team to filter against
            return snapshots

        # every entity index < 512 lives in chunk 0 of the entity list
        chunk0 = mem.read_ptr(ent_list + 0x10)
        if not chunk0:
            return snapshots

        for i in range(1, MAX_PLAYERS + 1):  # index 0 is the world entity; player controllers are 1..64
            try:
                controller = mem.read_ptr(chunk0 + ENTITY_IDENTITY_STRIDE * i)
                if not controller:
                    continue

                pawn_handle = mem.read_i32(controller + off["m_hPlayerPawn"])
                if pawn_handle in (0, INVALID_HANDLE):
                    continue

                pawn_chunk = mem.read_ptr(ent_list + 0x10 + 8 * ((pawn_handle & 0x7FFF) >> 9))
                if not pawn_chunk:
                    continue

                pawn = mem.read_ptr(pawn_chunk + ENTITY_IDENTITY_STRIDE * (pawn_handle & 0x1FF))
                if not pawn or pawn == local_addr:
                    continue

                if mem.read_u8(pawn + off["m_lifeState"]) != LIFE_ALIVE:
                    continue

                team = mem.read_u8(pawn + off["m_iTeamNum"])
                if team == local_team:
                    continue

                raw_name = mem.read_bytes(controller + off["m_iszPlayerName"], 64)
                name = raw_name.split(b"\x00")[0].decode("utf-8", "ignore") if raw_name else "?"
                health = mem.read_i32(pawn + off["m_iHealth"])

                scene = mem.read_ptr(pawn + off["m_pGameSceneNode"])
                bone_matrix = mem.read_ptr(scene + off["m_modelState"] + BONE_ARRAY_PTR_OFFSET) if scene else 0
                bones = self._batch_bones(bone_matrix) if bone_matrix else {}
            except pymem.exception.MemoryReadError:
                continue  # entity torn down mid-walk: drop this slot, keep the rest of the frame

            snapshots.append(EntitySnapshot(address=pawn, team=team, health=health, name=name, bones=bones))

        return snapshots
