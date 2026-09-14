import threading
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class ThreadConfig:
    """Shared configuration for worker threads.

    Written by Streamlit script threads and read by workers without a lock. That is safe only
    because every field is an immutable scalar (atomic attribute read/write under the GIL).
    """

    trigger_key: str = "shift"
    rcs_amount: float = 0.0
    enable_trigger: bool = False
    enable_rcs: bool = False
    enable_esp: bool = False


class ThreadManager:
    """Manages specific threads with stop events."""

    def __init__(self) -> None:
        self.threads: dict[str, threading.Thread] = {}
        self.stop_events: dict[str, threading.Event] = {}
        self.config = ThreadConfig()
        # one manager is shared by every Streamlit session (app._attach), so start/stop from two tabs must not interleave
        self._lock = threading.Lock()

    def start_thread(self, name: str, target: Callable, args: tuple = ()) -> None:
        """Starts a thread if it's not already running."""
        with self._lock:
            if name in self.threads and self.threads[name].is_alive():
                return

            stop_event = threading.Event()
            self.stop_events[name] = stop_event

            # Pass stop_event and config to the target function
            thread = threading.Thread(target=target, args=(stop_event, self.config) + args, daemon=True)
            self.threads[name] = thread
            thread.start()

    def stop_thread(self, name: str) -> None:
        """Signals a thread to stop and waits for it to join."""
        with self._lock:
            event = self.stop_events.get(name)
            if event is not None:
                event.set()

            thread = self.threads.get(name)
            if thread is None:
                self.stop_events.pop(name, None)
                return

            if thread.is_alive():
                # first attempt is short so toggling ESP off doesn't freeze the UI;
                # a second longer join catches hung workers on shutdown.
                thread.join(timeout=0.2)
                if thread.is_alive():
                    thread.join(timeout=2.0)

            if thread.is_alive():
                return

            self.threads.pop(name, None)
            self.stop_events.pop(name, None)

    def stop_all(self) -> None:
        """Stops all managed threads."""
        for name in list(self.threads.keys()):
            self.stop_thread(name)

    def is_running(self, name: str) -> bool:
        return name in self.threads and self.threads[name].is_alive()
