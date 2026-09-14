import json
from pathlib import Path

_OUTPUT = Path(__file__).resolve().parent.parent / "output"


def _load_json(name: str) -> dict:
    path = _OUTPUT / name
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise RuntimeError(f"Offset file not found: {path} (run start.bat to dump offsets)") from e
    except Exception as e:
        raise RuntimeError(f"Failed to load {path}: {e}") from e


def _build_offsets() -> dict[str, int]:
    offsets_json = _load_json("offsets.json")
    client_dll = _load_json("client_dll.json")

    def offset(key: str) -> int:
        try:
            return offsets_json["client.dll"][key]
        except KeyError as e:
            raise RuntimeError(f"Offset '{key}' not found in offsets.json") from e

    def field(class_name: str, field_name: str) -> int:
        try:
            return client_dll["client.dll"]["classes"][class_name]["fields"][field_name]
        except KeyError as e:
            raise RuntimeError(f"Field '{field_name}' not found in class '{class_name}' in client_dll.json") from e

    return {
        "dwEntityList": offset("dwEntityList"),
        "dwLocalPlayerPawn": offset("dwLocalPlayerPawn"),
        "dwSensitivity": offset("dwSensitivity"),
        "dwSensitivity_sensitivity": offset("dwSensitivity_sensitivity"),
        "m_iIDEntIndex": field("C_CSPlayerPawn", "m_iIDEntIndex"),
        "m_iTeamNum": field("C_BaseEntity", "m_iTeamNum"),
        "m_iHealth": field("C_BaseEntity", "m_iHealth"),
        "m_iShotsFired": field("C_CSPlayerPawn", "m_iShotsFired"),
        "m_pAimPunchServices": field("C_CSPlayerPawn", "m_pAimPunchServices"),
        "dwViewMatrix": offset("dwViewMatrix"),
        "m_lifeState": field("C_BaseEntity", "m_lifeState"),
        "m_pGameSceneNode": field("C_BaseEntity", "m_pGameSceneNode"),
        "m_modelState": field("CSkeletonInstance", "m_modelState"),
        "m_hPlayerPawn": field("CCSPlayerController", "m_hPlayerPawn"),
        "m_iszPlayerName": field("CBasePlayerController", "m_iszPlayerName"),
    }


offsets: dict[str, int] = _build_offsets()
