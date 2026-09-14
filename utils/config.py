import contextlib
import io

with contextlib.redirect_stdout(io.StringIO()):
    from raylibpy import Color

TRIGGER_KEYS: tuple[str, ...] = (
    "shift", "x", "x2", "alt", "ctrl",
    "insert", "home", "page up", "delete", "end", "page down",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "up", "left", "down", "right",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "y", "z",
    "-", "=", "backspace", "tab", "[", "]", "caps lock",
    ";", "'", "enter", ",", ".", "/",
    "num lock", "*", "+", "scroll lock", "pause", "`",
)

CS2_WINDOW_TITLE = "Counter-Strike 2"

SLEEP_TICK = 0.005
SLEEP_INACTIVE = 0.1
SLEEP_PRESSED = 0.03
SLEEP_RELEASED = 0.1
CLICK_PRE_DELAY = (0.01, 0.03)
CLICK_POST_DELAY = (0.01, 0.05)

MOUSEEVENTF_MOVE = 0x0001

OVERLAY_FPS = 60  # ESP redraw rate; raise toward the monitor refresh rate if boxes visibly lag

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080

HP_HIGH = Color(0, 200, 0, 255)
HP_MED = Color(255, 140, 0, 255)
HP_LOW = Color(255, 0, 0, 255)
NAME_COLOR = Color(255, 255, 0, 255)
ENTITY_COLOR = Color(0, 180, 255, 255)
TRANSPARENT = Color(0, 0, 0, 0)
NAME_SZ = 16
HP_TEXT_SZ = 12

BONE_INDICES = {
    "waist": 1,
    "neck": 6,
    "head": 7,
    "shoulder_right": 13,
    "arm_right": 14,
    "hand_left": 11,
    "shoulder_left": 9,
    "arm_left": 10,
    "hand_right": 15,
    "knee_left": 18,
    "ankle_left": 19,
    "knee_right": 21,
    "ankle_right": 22,
}
