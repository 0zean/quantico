import ctypes
from math import isfinite

from utils.config import MOUSEEVENTF_MOVE
from utils.structs import INPUT, MOUSEINPUT

# ctypes function prototype
SendInput = ctypes.windll.user32.SendInput
SendInput.argtypes = (ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int)
SendInput.restype = ctypes.c_uint


def _make_relative_input(dx: int, dy: int) -> INPUT:
    """Build a relative-move INPUT struct (MOUSEEVENTF_MOVE = 0x0001)."""
    mi = MOUSEINPUT(
        dx=dx,
        dy=dy,
        mouseData=0,
        dwFlags=MOUSEEVENTF_MOVE,
        time=0,
        dwExtraInfo=0,
    )
    return INPUT(type=0, u=INPUT.INPUT_UNION(mi=mi))


def _send(inp: INPUT) -> None:
    SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


class RelativeMouse:
    """Emit relative mouse moves, carrying the sub-pixel remainder between calls.

    SendInput moves in whole pixels. `int()` truncation of each float delta throws away anything
    below one pixel; accumulating the remainder and spending it once it crosses a whole pixel keeps
    the total emitted motion equal to the total requested motion. int() truncates toward zero for
    both signs, so the carry stays symmetric for negative deltas.

    One instance per worker thread: the carry is per-thread state, not shared.
    """

    __slots__ = ("_carry_x", "_carry_y")

    def __init__(self) -> None:
        self._carry_x = 0.0
        self._carry_y = 0.0

    def _drain(self, dx: float, dy: float) -> tuple[int, int]:
        """Add a float delta to the carry and return the whole-pixel step to emit.

        A non-finite delta (NaN/Inf from a stale or garbage memory read) is ignored rather than
        added: once the carry became NaN/Inf, int() would raise on this and every later call, so a
        single bad tick would silently kill the mover until it was recreated.
        """
        if isfinite(dx):
            self._carry_x += dx
        if isfinite(dy):
            self._carry_y += dy
        step_x = int(self._carry_x)  # truncates toward zero for both signs, keeping the carry symmetric
        step_y = int(self._carry_y)
        self._carry_x -= step_x
        self._carry_y -= step_y
        return step_x, step_y

    def move(self, dx: float, dy: float) -> None:
        """Send the accumulated whole-pixel part of a relative move; keep the remainder."""
        step_x, step_y = self._drain(dx, dy)
        if step_x or step_y:
            _send(_make_relative_input(step_x, step_y))


def _selfcheck() -> None:
    # Core invariant: whatever is not emitted stays in the carry, so emitted + carry == requested to
    # float precision and the carry never exceeds one pixel. int()-per-move (the old behaviour) would
    # emit 0 for every sub-pixel stream and lose it all; here nothing is lost.
    for delta, n in ((0.6, 30), (-0.6, 30), (0.4, 100), (0.05, 200)):
        m = RelativeMouse()
        emitted = sum(m._drain(delta, 0.0)[0] for _ in range(n))
        requested = delta * n
        assert abs((emitted + m._carry_x) - requested) < 1e-6, (delta, n, emitted, m._carry_x)
        assert abs(m._carry_x) < 1.0, m._carry_x  # so emitted is always within one pixel of requested
    # A stream well under one pixel still eventually moves the cursor, rather than being dropped.
    m = RelativeMouse()
    assert sum(m._drain(0.05, 0.0)[0] for _ in range(200)) >= 9  # ~10px over 200 ticks, not 0
    # Truncation is toward zero, not floor(): -0.6 emits 0, and only the second tick (carry -1.2) emits -1.
    m = RelativeMouse()
    assert m._drain(-0.6, 0.0)[0] == 0 and m._drain(-0.6, 0.0)[0] == -1
    # A non-finite delta must not poison the carry: a normal move right after still works.
    m = RelativeMouse()
    m._drain(float("nan"), float("inf"))
    assert m._drain(1.7, -2.3) == (1, -2)
    print("mouse.RelativeMouse self-check OK")


if __name__ == "__main__":
    _selfcheck()
