import logging
import threading
import time
from random import uniform

import win32api
import win32con
from pynput.mouse import Button, Controller
from win32gui import GetForegroundWindow, GetWindowText

from utils.config import (
    CLICK_POST_DELAY,
    CLICK_PRE_DELAY,
    CS2_WINDOW_TITLE,
    SLEEP_INACTIVE,
    SLEEP_PRESSED,
    SLEEP_RELEASED,
)
from utils.entity import ENTITY_IDENTITY_STRIDE
from utils.memory import ProcessMemory
from utils.offsets import offsets
from utils.thread_manager import ThreadConfig

_mouse = Controller()
logger = logging.getLogger(__name__)

_KEY_DOWN = 0x8000  # high bit of GetAsyncKeyState: the key is currently held

# Named keys and mouse buttons -> virtual-key code. Single printable characters (letters, digits,
# and the OEM punctuation in TRIGGER_KEYS) are resolved by the OS via VkKeyScan instead.
_NAMED_VK: dict[str, int] = {
    "x": win32con.VK_XBUTTON1,
    "x2": win32con.VK_XBUTTON2,
    "shift": win32con.VK_SHIFT,
    "ctrl": win32con.VK_CONTROL,
    "alt": win32con.VK_MENU,
    "insert": win32con.VK_INSERT,
    "home": win32con.VK_HOME,
    "page up": win32con.VK_PRIOR,
    "delete": win32con.VK_DELETE,
    "end": win32con.VK_END,
    "page down": win32con.VK_NEXT,
    "up": win32con.VK_UP,
    "left": win32con.VK_LEFT,
    "down": win32con.VK_DOWN,
    "right": win32con.VK_RIGHT,
    "backspace": win32con.VK_BACK,
    "tab": win32con.VK_TAB,
    "caps lock": win32con.VK_CAPITAL,
    "enter": win32con.VK_RETURN,
    "num lock": win32con.VK_NUMLOCK,
    "*": win32con.VK_MULTIPLY,
    "+": win32con.VK_ADD,
    "scroll lock": win32con.VK_SCROLL,
    "pause": win32con.VK_PAUSE,
    **{f"f{i}": getattr(win32con, f"VK_F{i}") for i in range(1, 13)},
}


def _vk_for(key: str) -> int:
    """Virtual-key code for a TRIGGER_KEYS entry, or 0 if it cannot be mapped."""
    if key in _NAMED_VK:
        return _NAMED_VK[key]
    if len(key) == 1:
        vk = win32api.VkKeyScan(key) & 0xFF  # low byte is the VK; 0xFF means "unmapped"
        if vk != 0xFF:
            return vk
    return 0


def _key_down(key: str) -> bool:
    """True while the trigger key is held, via GetAsyncKeyState (no global hook)."""
    vk = _vk_for(key)
    return vk != 0 and bool(win32api.GetAsyncKeyState(vk) & _KEY_DOWN)


def _is_cs2_focused() -> bool:
    return GetWindowText(GetForegroundWindow()) == CS2_WINDOW_TITLE


def _click() -> None:
    """Simulate a left-click with randomised pre/post delays."""
    time.sleep(uniform(*CLICK_PRE_DELAY))
    _mouse.press(Button.left)
    time.sleep(uniform(*CLICK_POST_DELAY))
    _mouse.release(Button.left)


def _resolve_entity(mem: ProcessMemory, client: int, entity_id: int) -> int:
    """
    Resolve an entity index (e.g. m_iIDEntIndex) to its instance address via the entity list.

    Returns the address, or 0 if any pointer in the chain is invalid.
    """
    ent_list = mem.read_ptr(client + offsets["dwEntityList"])
    if not ent_list:
        return 0

    ent_entry = mem.read_ptr(ent_list + 0x8 * (entity_id >> 9) + 0x10)
    if not ent_entry:
        return 0

    return mem.read_ptr(ent_entry + ENTITY_IDENTITY_STRIDE * (entity_id & 0x1FF))


def trig(stop_event: threading.Event, thread_cfg: ThreadConfig, mem: ProcessMemory, client: int) -> None:
    """
    Trigger bot thread.

    Args:
        stop_event (threading.Event): Signals the thread to exit cleanly.
        thread_cfg (ThreadConfig): Shared mutable configuration (enable flag, trigger key).
        mem (ProcessMemory): Process memory handle.
        client (int): client.dll base address.
    """
    while not stop_event.is_set():
        try:
            if not thread_cfg.enable_trigger:
                time.sleep(SLEEP_INACTIVE)
                continue

            if not _is_cs2_focused():
                time.sleep(SLEEP_INACTIVE)
                continue

            if not _key_down(thread_cfg.trigger_key):
                time.sleep(SLEEP_RELEASED)
                continue

            # Only read memory once the trigger key is confirmed held
            player = mem.read_ptr(client + offsets["dwLocalPlayerPawn"])
            if not player:
                time.sleep(SLEEP_PRESSED)
                continue

            entity_id = mem.read_i32(player + offsets["m_iIDEntIndex"])
            if entity_id <= 0:
                time.sleep(SLEEP_PRESSED)
                continue

            local_team = mem.read_u8(player + offsets["m_iTeamNum"])

            entity = _resolve_entity(mem, client, entity_id)
            if not entity:
                time.sleep(SLEEP_PRESSED)
                continue

            entity_team = mem.read_u8(entity + offsets["m_iTeamNum"])
            if entity_team == local_team:
                time.sleep(SLEEP_PRESSED)
                continue

            if mem.read_i32(entity + offsets["m_iHealth"]) > 0:
                _click()

            time.sleep(SLEEP_PRESSED)

        except Exception as e:
            logger.warning("Triggerbot error: %s", e)
            time.sleep(0.1)
