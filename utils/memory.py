from ctypes import Structure, sizeof
from typing import TypeVar

import pymem
import pymem.exception
import pymem.process
from pymem.ressources.structure import PROCESS

T = TypeVar("T", bound=Structure)

READ_ONLY_ACCESS = PROCESS.PROCESS_VM_READ.value | PROCESS.PROCESS_QUERY_INFORMATION.value


def _open_read_only(process_name: str) -> pymem.Pymem:
    """Attach with a read-only handle and WITHOUT SeDebugPrivilege.

    `pymem.Pymem(process_name)` opens the target with `PROCESS_ALL_ACCESS` and enables SeDebugPrivilege.
    Neither is required to only *read* an unprotected process, so we skip pymem's attach and open the
    handle ourselves with `READ_ONLY_ACCESS` and `debug=False`. The features then runs through a handle 
    that carries no write or inject capability which is the point of the read-only showcase, and a
    concrete artifact (handle rights + absence of the debug privilege) for anti-cheat work.
    """
    entry = pymem.process.process_from_name(process_name)
    if entry is None:
        raise pymem.exception.ProcessNotFound(process_name)

    pm = pymem.Pymem()  # no process_name: do not let pymem take a full-access handle / debug privilege
    pm.process_id = entry.th32ProcessID
    pm.process_handle = pymem.process.open(pm.process_id, debug=False, process_access=READ_ONLY_ACCESS)
    if not pm.process_handle:
        raise pymem.exception.CouldNotOpenProcess(pm.process_id)
    pm.check_wow64()
    return pm


class ProcessMemory:
    """Typed wrapper around pymem.

    Error contract:
    - read_i32 / read_u8 / read_f32 raise pymem.exception.MemoryReadError: a 0 sentinel would be
      indistinguishable from real data (0 is LIFE_ALIVE and a valid team; 0.0 sensitivity is a divisor).
    - read_ptr returns 0; read_struct / read_bytes / read_region return None.
    Pointer-chain walks must catch MemoryReadError per entity (see EntityManager.get_entities).
    """

    __slots__ = ("_pm",)

    def __init__(self, process_name: str, pm: pymem.Pymem | None = None) -> None:
        # pm lets tests inject a fake backend and still exercise the real read_* contract above
        self._pm = pm if pm is not None else _open_read_only(process_name)

    def read_i32(self, address: int) -> int:
        return self._pm.read_int(address=address)

    def read_u8(self, address: int) -> int:
        """Read a single unsigned byte.

        Source 2 declares m_iTeamNum / m_lifeState as uint8 and packs the next
        field immediately after them, so read_i32 on those offsets silently
        drags in up to three neighbouring bytes.
        """
        return self._pm.read_uchar(address=address)

    def read_f32(self, address: int) -> float:
        return self._pm.read_float(address=address)

    def read_ptr(self, address: int) -> int:
        try:
            return self._pm.read_longlong(address=address)
        except pymem.exception.MemoryReadError:
            return 0

    def read_struct(self, address: int, struct_type: type[T]) -> T | None:
        try:
            raw = self._pm.read_bytes(address=address, length=sizeof(struct_type))
            return struct_type.from_buffer_copy(raw)
        except pymem.exception.MemoryReadError:
            return None

    def read_bytes(self, address: int, size: int) -> bytes | None:
        try:
            return self._pm.read_bytes(address=address, length=size)
        except pymem.exception.MemoryReadError:
            return None

    def read_region(self, base: int, size: int) -> memoryview | None:
        raw = self.read_bytes(address=base, size=size)
        return memoryview(raw) if raw else None

    @property
    def pymem(self) -> pymem.Pymem:
        return self._pm
