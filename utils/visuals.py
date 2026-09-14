from utils.structs import ScreenSize, Vec3


def world_to_screen(matrix: tuple[float, ...], pos: Vec3 | None, screen: ScreenSize) -> list[float] | None:
    """
    World to screen function.

    Args:
        matrix (tuple[float, ...]): View matrix.
        pos (Vec3 | None): x, y, z position.
        screen (ScreenSize): screen height and width.

    Returns:
        list[float] | None: Screen position [x, y].
    """
    if pos is None:
        return None

    x = matrix[0] * pos.x + matrix[1] * pos.y + matrix[2] * pos.z + matrix[3]
    y = matrix[4] * pos.x + matrix[5] * pos.y + matrix[6] * pos.z + matrix[7]
    w = matrix[12] * pos.x + matrix[13] * pos.y + matrix[14] * pos.z + matrix[15]

    if w < 0.1:
        return None

    inv_w = 1.0 / w

    x = screen.width / 2 + (x * inv_w) * screen.width / 2
    y = screen.height / 2 - (y * inv_w) * screen.height / 2
    return [x, y]
