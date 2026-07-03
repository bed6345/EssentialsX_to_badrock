# ============================================================
# playerdata.py - เก็บข้อมูลผู้เล่นเป็น JSON ต่อคน
#
# ไฟล์: plugins/essentials_be/userdata/<xuid>.json
# เก็บ: homes, จุด /back, cooldown ของ kit, สถานะ tptoggle, cooldown rtp
# โหลดตอน join / เซฟตอน quit / autosave ทุก 5 นาที (สั่งจาก plugin หลัก)
# ============================================================

from __future__ import annotations

import copy
import os
from typing import Optional

from endstone import Player

from endstone_essentials_be.utils.storage import load_json, save_json_atomic

# โครงข้อมูลเริ่มต้นของผู้เล่นแต่ละคน
_DEFAULT_DATA = {
    "name": "",        # ชื่อล่าสุด (ไว้ดูไฟล์ง่าย ๆ)
    "homes": {},       # {ชื่อ home: location dict}
    "back": None,      # จุดล่าสุดก่อนวาร์ป/จุดตาย (location dict)
    "kits": {},        # {ชื่อ kit: เวลาที่รับล่าสุด (epoch วินาที)}
    "tptoggle": True,  # เปิดรับคำขอ tpa หรือไม่
    "rtp_last": 0,     # เวลาที่ใช้ /rtp ล่าสุด
    "tp_last": 0,      # เวลาที่วาร์ปล่าสุด (teleport-cooldown)
}


class PlayerDataManager:
    """แคชข้อมูลผู้เล่นในหน่วยความจำ + บันทึกลงดิสก์แบบ atomic"""

    def __init__(self, plugin) -> None:
        self._plugin = plugin
        self._folder = os.path.join(plugin.data_folder, "userdata")
        os.makedirs(self._folder, exist_ok=True)
        self._cache: dict[str, dict] = {}
        self._dirty: set[str] = set()

    def _path(self, xuid: str) -> str:
        return os.path.join(self._folder, f"{xuid}.json")

    # ---------- โหลด / ดึงข้อมูล ----------

    def load(self, player: Player) -> dict:
        """โหลดข้อมูลผู้เล่นเข้าแคช (เรียกตอน join)"""
        xuid = player.xuid
        data = load_json(self._path(xuid), None)
        merged = copy.deepcopy(_DEFAULT_DATA)
        if isinstance(data, dict):
            merged.update(data)
        merged["name"] = player.name
        self._cache[xuid] = merged
        return merged

    def get(self, player: Player) -> dict:
        """ดึงข้อมูลผู้เล่นจากแคช (โหลดให้อัตโนมัติถ้ายังไม่มี เช่นหลัง /reload)"""
        return self._cache.get(player.xuid) or self.load(player)

    def get_by_xuid(self, xuid: str) -> Optional[dict]:
        return self._cache.get(xuid)

    # ---------- บันทึก ----------

    def mark_dirty(self, xuid: str) -> None:
        """ทำเครื่องหมายว่าข้อมูลเปลี่ยน รอ autosave/quit ค่อยเขียนลงดิสก์"""
        self._dirty.add(xuid)

    def save(self, xuid: str) -> None:
        """บันทึกข้อมูลของผู้เล่นคนเดียวลงดิสก์"""
        data = self._cache.get(xuid)
        if data is None:
            return
        try:
            save_json_atomic(self._path(xuid), data)
            self._dirty.discard(xuid)
        except OSError as exc:
            self._plugin.logger.error(f"บันทึก userdata {xuid} ไม่สำเร็จ: {exc}")

    def save_all(self, only_dirty: bool = True) -> int:
        """บันทึกทุกคน (autosave จะเซฟเฉพาะที่เปลี่ยน) คืนจำนวนที่เซฟ"""
        targets = list(self._dirty) if only_dirty else list(self._cache.keys())
        for xuid in targets:
            self.save(xuid)
        return len(targets)

    def unload(self, player: Player) -> None:
        """เซฟแล้วเอาออกจากแคช (เรียกตอน quit)"""
        xuid = player.xuid
        self.save(xuid)
        self._cache.pop(xuid, None)
        self._dirty.discard(xuid)
