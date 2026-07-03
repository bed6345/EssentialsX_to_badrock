# ============================================================
# home.py - จัดการ home ของผู้เล่น (เก็บใน userdata ต่อคน)
#
# จำนวน home สูงสุด: ดูจาก permission essentials.sethome.multiple.<n>
# (เอาค่ามากสุดที่ผู้เล่นมี) ถ้าไม่มีเลยใช้ default-homes ใน config
# ============================================================

from __future__ import annotations

import re
from typing import Optional

from endstone import Player
from endstone.level import Location

from endstone_essentials_be.utils.storage import dict_to_location, location_to_dict

# รูปแบบ permission กำหนดจำนวน home เช่น essentials.sethome.multiple.5
_MULTIPLE_RE = re.compile(r"^essentials\.sethome\.multiple\.(\d+|unlimited)$")


class HomeManager:
    def __init__(self, plugin) -> None:
        self._plugin = plugin

    # ---------- อ่านข้อมูล ----------

    def get_homes(self, player: Player) -> dict:
        """คืน dict {ชื่อ home: location dict} ของผู้เล่น"""
        return self._plugin.playerdata.get(player).get("homes", {})

    def get_home(self, player: Player, name: str) -> Optional[Location]:
        """คืน Location ของ home ตามชื่อ (None ถ้าไม่มีหรือมิติหาย)"""
        data = self.get_homes(player).get(name.lower())
        if data is None:
            return None
        return dict_to_location(self._plugin.server, data)

    def max_homes(self, player: Player) -> int:
        """หาจำนวน home สูงสุด: สแกน permission .multiple.<n> ที่ได้รับจริง"""
        best = 0
        try:
            for info in player.effective_permissions:
                if not info.value:
                    continue
                match = _MULTIPLE_RE.match(info.permission.lower())
                if match:
                    value = match.group(1)
                    if value == "unlimited":
                        return 10_000
                    best = max(best, int(value))
        except Exception as exc:
            self._plugin.logger.error(f"อ่าน permission จำนวน home ไม่สำเร็จ: {exc}")
        if best > 0:
            return best
        return int(self._plugin.settings.get("default-homes", 3))

    # ---------- แก้ไขข้อมูล ----------

    def set_home(self, player: Player, name: str) -> tuple[bool, str]:
        """ตั้ง home ที่ตำแหน่งปัจจุบัน คืน (สำเร็จ?, เหตุผลถ้าไม่สำเร็จ)"""
        name = name.lower()
        homes = self.get_homes(player)
        # ตั้งทับชื่อเดิมได้เสมอ แต่เพิ่มใหม่ต้องไม่เกินโควตา
        if name not in homes and len(homes) >= self.max_homes(player):
            return False, "limit"
        homes[name] = location_to_dict(player.location)
        self._plugin.playerdata.get(player)["homes"] = homes
        self._plugin.playerdata.mark_dirty(player.xuid)
        return True, ""

    def del_home(self, player: Player, name: str) -> bool:
        """ลบ home ตามชื่อ คืน True ถ้าลบได้"""
        name = name.lower()
        homes = self.get_homes(player)
        if name not in homes:
            return False
        del homes[name]
        self._plugin.playerdata.mark_dirty(player.xuid)
        return True
