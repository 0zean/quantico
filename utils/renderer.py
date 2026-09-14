import logging

from raylibpy import Color, Font, Vector2, draw_circle_lines, draw_line, draw_rectangle_lines, draw_text, draw_text_ex

from utils.config import HP_HIGH, HP_LOW, HP_MED, HP_TEXT_SZ, NAME_COLOR, NAME_SZ
from utils.structs import EntitySnapshot, ScreenSize, Vec3
from utils.visuals import world_to_screen

logger = logging.getLogger(__name__)
_logged: set[type[Exception]] = set()


def _hp_color(hp: int) -> Color:
    if hp >= 70:
        return HP_HIGH
    if hp > 30:
        return HP_MED
    return HP_LOW


def draw_entity(
    entity: EntitySnapshot, view_matrix: tuple[float, ...], screen: ScreenSize, font: Font | None, color: Color
) -> None:
    bones = entity.bones

    def proj(bone: str) -> list[float] | None:
        b = bones.get(bone)
        return world_to_screen(view_matrix, Vec3(*b), screen) if b else None

    try:
        head = proj("head")
        neck = proj("neck")
        shoulder_right = proj("shoulder_right")
        shoulder_left = proj("shoulder_left")
        arm_right = proj("arm_right")
        arm_left = proj("arm_left")
        hand_right = proj("hand_right")
        hand_left = proj("hand_left")
        waist = proj("waist")
        knee_right = proj("knee_right")
        knee_left = proj("knee_left")
        ankle_right = proj("ankle_right")
        ankle_left = proj("ankle_left")

        bone_connections = (
            (neck, shoulder_right),
            (neck, shoulder_left),
            (shoulder_left, arm_left),
            (shoulder_right, arm_right),
            (arm_right, hand_right),
            (arm_left, hand_left),
            (neck, waist),
            (waist, knee_right),
            (waist, knee_left),
            (knee_left, ankle_left),
            (knee_right, ankle_right),
        )

        valid_x: list[float] = []
        valid_y: list[float] = []

        for a, b in bone_connections:
            if a is not None and b is not None:
                draw_line(int(a[0]), int(a[1]), int(b[0]), int(b[1]), color)
                valid_x.extend((a[0], b[0]))
                valid_y.extend((a[1], b[1]))

        if head is not None:
            valid_x.append(head[0])
            valid_y.append(head[1])

        if not valid_y:
            return

        min_y = min(valid_y) - 10.0
        max_y = max(valid_y) + 5.0
        box_h = max_y - min_y
        box_w = box_h / 2.0
        lx = (min(valid_x) + max(valid_x) - box_w) / 2.0

        draw_rectangle_lines(int(lx), int(min_y), int(box_w), int(box_h), color)

        if head is not None and neck is not None:
            draw_circle_lines(int(head[0]), int(head[1]), abs(head[1] - neck[1]) * 1.125, color)

        hp = max(0, min(100, entity.health))
        bar_top = min_y + (1.0 - hp / 100.0) * box_h
        draw_line(int(lx - 5), int(bar_top), int(lx - 5), int(max_y), _hp_color(hp))

        if font:
            draw_text_ex(font, entity.name or "?", Vector2(lx, min_y - NAME_SZ - 2), float(NAME_SZ), 1.0, NAME_COLOR)
            draw_text_ex(font, f"HP: {hp}", Vector2(lx, max_y + 2), float(HP_TEXT_SZ), 1.0, NAME_COLOR)
        else:
            draw_text(entity.name or "?", int(lx), int(min_y - NAME_SZ - 2), NAME_SZ, NAME_COLOR)
            draw_text(f"HP: {hp}", int(lx), int(max_y + 2), HP_TEXT_SZ, NAME_COLOR)

    except Exception as exc:
        if type(exc) not in _logged:  # one traceback per exception type, not one per frame
            _logged.add(type(exc))
            logger.warning("Error drawing entity %s", entity.name, exc_info=True)
