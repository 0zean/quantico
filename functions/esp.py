# ruff: noqa: E402
import contextlib
import ctypes
import io
import logging
import os
import struct
import threading

import win32api

logger = logging.getLogger(__name__)

# raylibpy prints a loading banner to stdout on first import; stderr is left alone so warnings survive
with contextlib.redirect_stdout(io.StringIO()):
    from raylibpy import (
        FLAG_WINDOW_TOPMOST,
        FLAG_WINDOW_TRANSPARENT,
        FLAG_WINDOW_UNDECORATED,
        LOG_NONE,
        begin_drawing,
        clear_background,
        close_window,
        end_drawing,
        get_window_handle,
        init_window,
        load_font_ex,
        set_config_flags,
        set_target_fps,
        set_trace_log_level,
        unload_font,
        window_should_close,
    )

    try:
        from raylibpy import FLAG_WINDOW_MOUSE_PASSTHROUGH

        _HAS_PASSTHROUGH = True
    except ImportError:
        _HAS_PASSTHROUGH = False

from utils.config import (
    BONE_INDICES,
    ENTITY_COLOR,
    GWL_EXSTYLE,
    OVERLAY_FPS,
    TRANSPARENT,
    WS_EX_TOOLWINDOW,
    WS_EX_TRANSPARENT,
)
from utils.entity import EntityManager
from utils.memory import ProcessMemory
from utils.offsets import offsets
from utils.renderer import draw_entity
from utils.structs import ScreenSize
from utils.thread_manager import ThreadConfig


class ESPController:
    __slots__ = ("_mem", "_client", "_screen", "_entity_mgr")

    def __init__(self, mem: ProcessMemory, client: int) -> None:
        self._mem = mem
        self._client = client
        # Re-query live screen metrics so overlay stays correct if the user
        # changed resolution or moved to a different display.
        self._screen = ScreenSize(
            width=win32api.GetSystemMetrics(0),
            height=win32api.GetSystemMetrics(1),
        )
        self._entity_mgr = EntityManager(mem, client, offsets, BONE_INDICES)

    def _get_view_matrix(self) -> tuple[float, ...] | None:
        raw = self._mem.read_bytes(self._client + offsets["dwViewMatrix"], 64)
        return struct.unpack("16f", raw) if raw else None

    @staticmethod
    def _apply_win32_styles(hwnd: int) -> None:
        """
        Apply WS_EX_TRANSPARENT (click-through) and WS_EX_TOOLWINDOW (hide
        from taskbar/Alt-Tab) to the overlay window.
        """
        if not hwnd:
            logger.warning("get_window_handle() returned NULL; click-through not applied")
            return
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW)

    def run(self, stop_event: threading.Event, thread_cfg: ThreadConfig) -> None:
        set_trace_log_level(LOG_NONE)

        # window flags before creation
        flags = FLAG_WINDOW_UNDECORATED | FLAG_WINDOW_TRANSPARENT | FLAG_WINDOW_TOPMOST
        if _HAS_PASSTHROUGH:
            flags |= FLAG_WINDOW_MOUSE_PASSTHROUGH
        set_config_flags(flags)

        # create window
        init_window(self._screen.width, self._screen.height, b"ESP Overlay")
        set_target_fps(OVERLAY_FPS)

        # obtain HWND
        hwnd = get_window_handle()

        # Apply Win32 styles before the sentinel frame
        self._apply_win32_styles(hwnd)

        # sentinel frame
        begin_drawing()
        clear_background(TRANSPARENT)
        end_drawing()

        # load font
        windir = os.environ.get("WINDIR", r"C:\Windows")
        font_path = os.path.join(windir, "Fonts", "calibri.ttf").encode()
        font = load_font_ex(font_path, 20, None, 0)

        # render loop
        logged: set[type[Exception]] = set()
        while not window_should_close() and not stop_event.is_set():
            begin_drawing()
            clear_background(TRANSPARENT)

            if thread_cfg.enable_esp:
                try:
                    vm = self._get_view_matrix()
                    if vm is not None:
                        for entity in self._entity_mgr.get_entities():
                            draw_entity(entity, vm, self._screen, font, ENTITY_COLOR)
                except Exception as exc:
                    if type(exc) not in logged:  # one traceback per exception type, not one per frame
                        logged.add(type(exc))
                        logger.warning("ESP render error", exc_info=True)

            end_drawing()

        unload_font(font)
        close_window()
