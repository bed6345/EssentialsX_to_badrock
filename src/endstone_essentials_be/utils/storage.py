# ============================================================
# storage.py - ตัวช่วยอ่าน/เขียนไฟล์ JSON, YAML และแปลง Location
#
# จุดสำคัญ: การเขียน JSON เป็นแบบ atomic (เขียนไฟล์ชั่วคราวก่อน
# แล้วค่อย rename ทับ) เพื่อป้องกันไฟล์พังถ้าเซิร์ฟเวอร์ดับกลางคัน
# ============================================================

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Optional

import yaml

from endstone.level import Location


def load_json(path: str, default: Any = None) -> Any:
    """อ่านไฟล์ JSON คืนค่า default ถ้าไฟล์ไม่มีหรืออ่านไม่ได้"""
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json_atomic(path: str, data: Any) -> None:
    """เขียน JSON แบบ atomic: เขียนลงไฟล์ชั่วคราวในโฟลเดอร์เดียวกัน
    ให้เสร็จก่อน แล้วค่อย os.replace ทับไฟล์จริง (rename เป็น atomic)"""
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except OSError:
        # เขียนไม่สำเร็จ - ลบไฟล์ชั่วคราวทิ้ง ไม่ให้ไฟล์ขยะค้าง
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def load_yaml(path: str, default: Any = None) -> Any:
    """อ่านไฟล์ YAML คืนค่า default ถ้าไฟล์ไม่มีหรือรูปแบบผิด"""
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if data is not None else default
    except (OSError, yaml.YAMLError):
        return default


# ---------- การแปลง Location <-> dict สำหรับเก็บลงไฟล์ ----------

# ชื่อมิติที่รองรับ (ค่าที่ Endstone ใช้: Overworld / Nether / TheEnd)
_DIMENSION_ALIASES = {
    "overworld": "Overworld",
    "nether": "Nether",
    "the_end": "TheEnd",
    "theend": "TheEnd",
    "end": "TheEnd",
}


def location_to_dict(loc: Location) -> dict:
    """แปลง Location เป็น dict สำหรับบันทึกลง JSON (เก็บมิติด้วย)"""
    return {
        "x": round(loc.x, 2),
        "y": round(loc.y, 2),
        "z": round(loc.z, 2),
        "pitch": round(loc.pitch, 2),
        "yaw": round(loc.yaw, 2),
        "dimension": loc.dimension.name,
    }


def dict_to_location(server, data: dict) -> Optional[Location]:
    """แปลง dict กลับเป็น Location - คืน None ถ้าข้อมูลไม่ครบหรือหามิติไม่เจอ"""
    if not isinstance(data, dict):
        return None
    try:
        dim_name = str(data.get("dimension", "Overworld"))
        dim_name = _DIMENSION_ALIASES.get(dim_name.lower(), dim_name)
        dimension = server.level.get_dimension(dim_name)
        if dimension is None:
            return None
        return Location(
            dimension,
            float(data["x"]),
            float(data["y"]),
            float(data["z"]),
            float(data.get("pitch", 0.0)),
            float(data.get("yaw", 0.0)),
        )
    except (KeyError, TypeError, ValueError, RuntimeError):
        return None
