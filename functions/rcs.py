import logging
import threading
import time

from win32gui import GetForegroundWindow, GetWindowText

from utils.config import CS2_WINDOW_TITLE, SLEEP_INACTIVE, SLEEP_TICK
from utils.memory import ProcessMemory
from utils.mouse import RelativeMouse
from utils.offsets import offsets
from utils.player import read_rcs_state
from utils.thread_manager import ThreadConfig

logger = logging.getLogger(__name__)

SOURCE_M_YAW = 0.022  # Source default m_yaw / m_pitch: degrees of view rotation per mouse count


def rcs(stop_event: threading.Event, thread_cfg: ThreadConfig, mem: ProcessMemory, client: int) -> None:
    """
    Recoil control system function.

    Args:
        stop_event (threading.Event): Event to signal stopping.
        thread_cfg (ThreadConfig): Shared configuration.
        mem (ProcessMemory): Process memory reader.
        client (int): Client module base address.
    """
    old_punch = (0.0, 0.0)
    mouse = RelativeMouse()  # owns the sub-pixel carry for this worker thread

    while not stop_event.is_set():
        try:
            if not thread_cfg.enable_rcs:
                old_punch = (0.0, 0.0)
                time.sleep(SLEEP_INACTIVE)
                continue

            amt = thread_cfg.rcs_amount

            if GetWindowText(GetForegroundWindow()) != CS2_WINDOW_TITLE:
                time.sleep(SLEEP_INACTIVE)
                continue

            player_addr = mem.read_ptr(client + offsets["dwLocalPlayerPawn"])

            if not player_addr:
                old_punch = (0.0, 0.0)
                time.sleep(SLEEP_INACTIVE)  # menus / between rounds: no need to poll at 200 Hz
                continue

            shots_fired, (punch_x, punch_y, _), sensitivity = read_rcs_state(mem, player_addr, client, offsets)

            if 1 < shots_fired < 999_999:
                delta_x = (punch_x - old_punch[0]) * -1.0
                delta_y = (punch_y - old_punch[1]) * -1.0

                # Relative move sent straight through: no cursor read-back, sub-pixel carry retained.
                mouse.move(
                    (delta_y * amt / sensitivity) / -SOURCE_M_YAW,
                    (delta_x * amt / sensitivity) / SOURCE_M_YAW,
                )
            old_punch = (punch_x, punch_y)
            time.sleep(SLEEP_TICK)

        except Exception as exc:
            logger.warning("RCS error: %s", exc)
            time.sleep(SLEEP_TICK)
