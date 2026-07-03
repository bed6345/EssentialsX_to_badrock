# ============================================================
# kit.py - ระบบชุดไอเทม (นิยามใน kits.yml)
#
# ต่อ kit กำหนดได้: items (id/amount/name/lore/enchantments),
# cooldown วินาที (-1 = รับได้ครั้งเดียวตลอดกาล), auto-equip เกราะ
# - permission ต่อ kit: essentials.kits.<ชื่อ> (OP ผ่านเสมอ)
# - เวลารับล่าสุดเก็บใน userdata -> cooldown คงอยู่แม้รีสตาร์ต
# - ช่องเก็บของเต็ม: ดรอปของที่เหลือลงพื้น + แจ้งเตือน
# ============================================================

from __future__ import annotations

import os
import time
from typing import Optional

from endstone import Player
from endstone.inventory import ItemStack

from endstone_essentials_be.utils.storage import load_yaml

# ไอเทมเกราะ -> ช่องสวมใส่ (ใช้กับ auto-equip)
_ARMOR_SLOTS = ("helmet", "chestplate", "leggings", "boots")


class KitManager:
    def __init__(self, plugin) -> None:
        self._plugin = plugin
        self._kits: dict = {}
        self.reload()

    def reload(self) -> None:
        """โหลด kits.yml จากโฟลเดอร์ข้อมูลของปลั๊กอิน"""
        path = os.path.join(self._plugin.data_folder, "kits.yml")
        data = load_yaml(path, {}) or {}
        kits = data.get("kits", {})
        self._kits = {str(k).lower(): v or {} for k, v in kits.items()}
        self._plugin.logger.info(f"โหลด kit ทั้งหมด {len(self._kits)} ชุด")

    # ---------- สิทธิ์และ cooldown ----------

    def names(self) -> list[str]:
        return sorted(self._kits.keys())

    def exists(self, name: str) -> bool:
        return name.lower() in self._kits

    def can_use(self, player: Player, name: str) -> bool:
        """เช็ค permission ต่อ kit: essentials.kits.<ชื่อ>
        (permission แบบ dynamic: ถ้าไม่มีใครกำหนดให้ ใช้กติกา OP เท่านั้น
        ยกเว้น kit ตั้ง public: true ใน kits.yml = ทุกคนใช้ได้)"""
        kit = self._kits.get(name.lower())
        if kit is None:
            return False
        if bool(kit.get("public", True)):
            return True
        perm = f"essentials.kits.{name.lower()}"
        if player.is_permission_set(perm):
            return player.has_permission(perm)
        return player.is_op

    def usable_names(self, player: Player) -> list[str]:
        return [n for n in self.names() if self.can_use(player, n)]

    def remaining_cooldown(self, player: Player, name: str) -> int:
        """วินาทีที่ต้องรอก่อนรับ kit นี้ได้อีกครั้ง (-1 = ใช้ครั้งเดียวและใช้ไปแล้ว)"""
        kit = self._kits.get(name.lower(), {})
        cooldown = int(kit.get("cooldown", 0))
        last = int(self._plugin.playerdata.get(player).get("kits", {})
                   .get(name.lower(), 0))
        if last <= 0:
            return 0  # ยังไม่เคยรับ
        if cooldown < 0:
            return -1  # รับได้ครั้งเดียว และรับไปแล้ว
        remaining = last + cooldown - int(time.time())
        return max(0, remaining)

    # ---------- แจกของ ----------

    def give(self, player: Player, name: str) -> bool:
        """แจก kit ให้ผู้เล่น (เช็คสิทธิ์/cooldown แล้วเรียบร้อย) คืน True ถ้าแจกสำเร็จ"""
        msg = self._plugin.messages
        key = name.lower()
        kit = self._kits.get(key)
        if kit is None:
            msg.send_error(player, "kit.not-found", kit=name)
            return False
        if not self.can_use(player, key):
            msg.send_error(player, "kit.no-permission", kit=key)
            return False

        remaining = self.remaining_cooldown(player, key)
        if remaining == -1:
            msg.send_error(player, "kit.once", kit=key)
            return False
        if remaining > 0:
            msg.send_error(player, "kit.cooldown",
                           kit=key, time=msg.format_duration(remaining))
            return False

        auto_equip = bool(kit.get("auto-equip", False))
        dropped = False

        for entry in kit.get("items", []) or []:
            stack = self._build_item(entry)
            if stack is None:
                continue

            # auto-equip: ถ้าเป็นเกราะและช่องสวมว่าง ให้สวมทันที
            if auto_equip and self._try_equip(player, stack):
                continue

            leftovers = player.inventory.add_item(stack)
            # ของที่ใส่กระเป๋าไม่หมด -> ดรอปลงพื้นตรงตัวผู้เล่น
            for extra in (leftovers or {}).values():
                try:
                    player.dimension.drop_item(player.location, extra)
                    dropped = True
                except Exception as exc:
                    self._plugin.logger.error(f"ดรอปไอเทม kit ไม่สำเร็จ: {exc}")

        # บันทึกเวลารับลง userdata (คงอยู่หลังรีสตาร์ต)
        data = self._plugin.playerdata.get(player)
        data.setdefault("kits", {})[key] = int(time.time())
        self._plugin.playerdata.mark_dirty(player.xuid)

        msg.send(player, "kit.received", kit=key)
        if dropped:
            msg.send(player, "kit.dropped")
        return True

    def _build_item(self, entry: dict) -> Optional[ItemStack]:
        """สร้าง ItemStack จากรายการใน kits.yml (item/amount/name/lore/enchantments)"""
        try:
            item_id = str(entry.get("item", "")).strip()
            if not item_id:
                return None
            amount = max(1, int(entry.get("amount", 1)))
            stack = ItemStack(item_id, amount)

            custom_name = entry.get("name")
            lore = entry.get("lore")
            enchants = entry.get("enchantments") or {}
            if custom_name or lore or enchants:
                meta = stack.item_meta
                if custom_name:
                    meta.display_name = str(custom_name)
                if lore:
                    meta.lore = [str(line) for line in lore]
                for ench_id, level in enchants.items():
                    try:
                        meta.add_enchant(str(ench_id), int(level), force=True)
                    except Exception:
                        self._plugin.logger.warning(
                            f"เอนชานต์ '{ench_id}' ใส่ไม่ได้ - ข้าม")
                stack.set_item_meta(meta)
            return stack
        except Exception as exc:
            self._plugin.logger.error(f"สร้างไอเทม kit ไม่สำเร็จ ({entry}): {exc}")
            return None

    def _try_equip(self, player: Player, stack: ItemStack) -> bool:
        """สวมเกราะให้อัตโนมัติถ้าช่องนั้นว่าง คืน True ถ้าสวมแล้ว"""
        try:
            item_id = stack.type.id
            for slot in _ARMOR_SLOTS:
                if item_id.endswith(f"_{slot}"):
                    if getattr(player.inventory, slot) is None:
                        setattr(player.inventory, slot, stack)
                        return True
                    return False
        except Exception:
            pass
        return False
