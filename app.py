import os
from pathlib import Path

import pymem.exception
import pymem.process
import streamlit as st
import win32process
from pymem.ressources.structure import MODULEINFO

from utils.config import TRIGGER_KEYS
from utils.memory import ProcessMemory
from utils.thread_manager import ThreadManager

st.set_page_config(
    page_title="CORAL.py",
    page_icon="\U0001f420",
    layout="centered",
    initial_sidebar_state="collapsed",
)
state = st.session_state
_HERE = Path(__file__).resolve().parent
STILL_ACTIVE = 259  # GetExitCodeProcess result for a process that has not exited

try:  # utils.offsets parses output/*.json at import and raises RuntimeError if the dump is missing or stale
    from functions.esp import ESPController
    from functions.rcs import rcs
    from functions.trig import trig
except RuntimeError as e:
    st.error(str(e), icon="\U0001f6a8")
    st.stop()

if st.sidebar.button("Shut Down"):
    os._exit(0)  # daemon workers and the raylib window go down with the process


def _still_attached(res: tuple[ProcessMemory, int, ThreadManager]) -> bool:
    mem, _, mgr = res
    if win32process.GetExitCodeProcess(mem.pymem.process_handle) == STILL_ACTIVE:
        return True
    mgr.stop_all()  # cs2.exe exited: stop the old workers before re-attaching
    mem.pymem.close_process()
    return False


@st.cache_resource(validate=_still_attached)  # one attach per server process, shared by every tab and refresh
def _attach() -> tuple[ProcessMemory, int, ThreadManager]:
    mem = ProcessMemory("cs2.exe")  # ProcessNotFound propagates and is not cached
    module = pymem.process.module_from_name(mem.pymem.process_handle, "client.dll")
    if not isinstance(module, MODULEINFO):
        mem.pymem.close_process()
        raise LookupError("client.dll not found in cs2.exe!")
    return mem, module.lpBaseOfDll, ThreadManager()


try:
    mem, client, thread_mgr = _attach()
except pymem.exception.ProcessNotFound:
    st.error("cs2.exe not found!", icon="\U0001f6a8")
    st.stop()
except pymem.exception.CouldNotOpenProcess:
    st.error("Could not open cs2.exe for reading (try running CORAL as administrator).", icon="\U0001f6a8")
    st.stop()
except LookupError as e:
    st.error(str(e), icon="\U0001f6a8")
    st.stop()

if "loaded" not in state:
    st.toast("coral.py loaded", icon="\U0001f4af")
    st.balloons()
    state.loaded = True

# App design + layout
with open(_HERE / "assets" / "style.css", encoding="utf-8") as f:
    st.html(f"<style>{f.read()}</style>")

st.html(
    '<h1 class="title-font">'
    'C<span style="color:#fdc4b6;">o</span>'
    '<span style="color:#e59572;">r</span>'
    '<span style="color:#2694ab;">a</span>'
    '<span style="color:#4dbedf;">l</span>🐠'
    "</h1>"
)

tab_aim, tab_esp, tab_misc = st.tabs(["Aim", "ESP", "Misc"])

# Aim Tab
with tab_aim:
    col_toggle, col_control = st.columns(2)

    with col_toggle:
        # Trigger bot
        enable_trigger = st.toggle("Enable trigger bot")
        thread_mgr.config.enable_trigger = enable_trigger

        if enable_trigger and not thread_mgr.is_running("tbot"):
            thread_mgr.start_thread("tbot", trig, (mem, client))
        elif not enable_trigger and thread_mgr.is_running("tbot"):
            thread_mgr.stop_thread("tbot")

        # RCS
        enable_rcs = st.toggle("Enable RCS")
        thread_mgr.config.enable_rcs = enable_rcs

        if enable_rcs and not thread_mgr.is_running("rcs"):
            thread_mgr.start_thread("rcs", rcs, (mem, client))
        elif not enable_rcs and thread_mgr.is_running("rcs"):
            thread_mgr.stop_thread("rcs")

    with col_control:
        trigkey = st.selectbox(
            "Trigger key  (*x* / *x2* = mouse side-buttons)",
            TRIGGER_KEYS,
            placeholder="Choose a key",
            disabled=not enable_trigger,
        )
        thread_mgr.config.trigger_key = trigkey

        amt = st.slider(
            "RCS amount",
            min_value=0.0,
            max_value=2.0,
            value=2.0,
            step=0.1,
            disabled=not enable_rcs,
        )
        thread_mgr.config.rcs_amount = amt

# ESP Tab
with tab_esp:
    enable_esp = st.toggle("Enable ESP")
    thread_mgr.config.enable_esp = enable_esp

    if enable_esp and not thread_mgr.is_running("esp"):

        def _esp_thread(
            stop_event,
            cfg,
            _mem: ProcessMemory = mem,
            _client: int = client,
        ) -> None:
            controller = ESPController(_mem, _client)
            controller.run(stop_event, cfg)

        thread_mgr.start_thread("esp", _esp_thread, ())

    if not enable_esp and thread_mgr.is_running("esp"):
        thread_mgr.stop_thread("esp")
