# ============================================================
# messages.py - ระบบข้อความหลายภาษา (i18n)
#
# โหลดจาก plugins/essentials_be/messages/<lang>.yml
# เลือกภาษาใน config.yml (ค่าเริ่มต้น th) ถ้า key ไม่มีในภาษาที่เลือก
# จะ fallback ไปอังกฤษ และถ้าไม่มีอีกจะคืนชื่อ key ตรง ๆ (กัน error)
# ============================================================

from __future__ import annotations

import os
from typing import Any

from endstone_essentials_be.utils.storage import load_yaml


def _flatten(data: dict, prefix: str = "") -> dict:
    """แปลง YAML ซ้อนชั้นเป็น key แบบจุด เช่น home.set"""
    out = {}
    for key, value in (data or {}).items():
        full = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            out.update(_flatten(value, full))
        else:
            out[full] = str(value)
    return out


class Messages:
    """ตัวจัดการข้อความ - ใช้ msg.tr("home.set", home="base") ได้ทุกที่"""

    def __init__(self, plugin) -> None:
        self._plugin = plugin
        self._data: dict = {}
        self._fallback: dict = {}
        self.reload()

    def reload(self) -> None:
        """โหลดไฟล์ภาษาใหม่ตามค่า language ใน config"""
        lang = str(self._plugin.settings.get("language", "th"))
        base = os.path.join(self._plugin.data_folder, "messages")
        self._data = _flatten(load_yaml(os.path.join(base, f"{lang}.yml"), {}))
        self._fallback = _flatten(load_yaml(os.path.join(base, "en.yml"), {}))

    def raw(self, key: str) -> str:
        """ดึงข้อความดิบตาม key (ยังไม่แทน placeholder)"""
        return self._data.get(key) or self._fallback.get(key) or key

    def tr(self, key: str, **placeholders: Any) -> str:
        """ดึงข้อความ + แทนที่ placeholder เช่น {player}, {home}, {seconds}
        ใช้ replace ทีละตัว (ไม่ใช้ str.format) กันพังเมื่อข้อความมี { } หรือ §"""
        text = self.raw(key)
        for name, value in placeholders.items():
            text = text.replace("{" + name + "}", str(value))
        return text

    def send(self, sender, key: str, **placeholders: Any) -> None:
        """ส่งข้อความปกติให้ผู้เล่น/คอนโซล"""
        try:
            sender.send_message(self.tr(key, **placeholders))
        except Exception:
            pass

    def send_error(self, sender, key: str, **placeholders: Any) -> None:
        """ส่งข้อความ error (สีแดง)"""
        try:
            sender.send_error_message(self.tr(key, **placeholders))
        except Exception:
            pass

    def format_duration(self, seconds: int) -> str:
        """แปลงวินาทีเป็นข้อความอ่านง่าย เช่น '2 ชม. 5 นาที'"""
        seconds = max(0, int(seconds))
        units = [
            (86400, "time.day"),
            (3600, "time.hour"),
            (60, "time.minute"),
            (1, "time.second"),
        ]
        parts = []
        for size, key in units:
            if seconds >= size:
                amount, seconds = divmod(seconds, size)
                parts.append(f"{amount} {self.raw(key)}")
            if len(parts) >= 2:  # แสดงแค่ 2 หน่วยใหญ่สุดพออ่านง่าย
                break
        return " ".join(parts) if parts else f"0 {self.raw('time.second')}"
