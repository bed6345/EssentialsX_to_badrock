# ============================================================
# warp.py - จัดการ warp สาธารณะ (warps.json) และจุด spawn (spawn.json)
#
# per-warp-permission ใน config:
#   - false (ค่าเริ่มต้น): ทุกคนที่มี essentials.warp ใช้ได้ทุก warp
#   - true: ต้องมี essentials.warps.<ชื่อ> เพิ่ม (OP ผ่านเสมอ)
# ============================================================

from __future__ import annotations

import os
from typing import Optional

from endstone import Player
from endstone.level import Location

from endstone_essentials_be.utils.storage import (
    dict_to_location,
    load_json,
    location_to_dict,
    save_json_atomic,
)


class WarpManager:
    def __init__(self, plugin) -> None:
        self._plugin = plugin
        self._warps_path = os.path.join(plugin.data_folder, "warps.json")
        self._spawn_path = os.path.join(plugin.data_folder, "spawn.json")
        self._warps: dict = load_json(self._warps_path, {}) or {}
        self._spawn: Optional[dict] = load_json(self._spawn_path, None)

    # ---------- warp ----------

    def names(self) -> list[str]:
        return sorted(self._warps.keys())

    def get_warp(self, name: str) -> Optional[Location]:
        data = self._warps.get(name.lower())
        if data is None:
            return None
        return dict_to_location(self._plugin.server, data)

    def set_warp(self, name: str, location: Location) -> None:
        self._warps[name.lower()] = location_to_dict(location)
        self._save_warps()

    def del_warp(self, name: str) -> bool:
        if name.lower() not in self._warps:
            return False
        del self._warps[name.lower()]
        self._save_warps()
        return True

    def _save_warps(self) -> None:
        try:
            save_json_atomic(self._warps_path, self._warps)
        except OSError as exc:
            self._plugin.logger.error(f"บันทึก warps.json ไม่สำเร็จ: {exc}")

    def can_use(self, player: Player, name: str) -> bool:
        """เช็คสิทธิ์ใช้ warp รายตัว (เมื่อเปิดโหมด per-warp-permission)"""
        if not bool(self._plugin.settings.get("per-warp-permission", False)):
            return True
        perm = f"essentials.warps.{name.lower()}"
        # permission แบบ dynamic ไม่ได้ประกาศไว้ล่วงหน้า:
        # ถ้ามีการ set มาจากปลั๊กอิน permission ให้ใช้ค่านั้น ไม่งั้น OP เท่านั้น
        if player.is_permission_set(perm):
            return player.has_permission(perm)
        return player.is_op

    def usable_names(self, player: Player) -> list[str]:
        """รายชื่อ warp ที่ผู้เล่นคนนี้มีสิทธิ์ใช้ (ไว้ทำปุ่มในฟอร์ม)"""
        return [n for n in self.names() if self.can_use(player, n)]

    # ---------- spawn ----------

    def get_spawn(self) -> Optional[Location]:
        if self._spawn is None:
            return None
        return dict_to_location(self._plugin.server, self._spawn)

    def set_spawn(self, location: Location) -> None:
        self._spawn = location_to_dict(location)
        try:
            save_json_atomic(self._spawn_path, self._spawn)
        except OSError as exc:
            self._plugin.logger.error(f"บันทึก spawn.json ไม่สำเร็จ: {exc}")
