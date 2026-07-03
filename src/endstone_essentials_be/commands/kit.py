# ============================================================
# kit.py (commands) - /kit
#
# /kit ไม่ใส่ชื่อ: ฟอร์มแสดง kit ที่มีสิทธิ์ใช้ พร้อมสถานะ cooldown บนปุ่ม
# kit ที่ติด cooldown กดแล้วแจ้งเวลาที่เหลือแทนการแจกของ (เช็คใน give อีกชั้น)
# ============================================================

from __future__ import annotations

from endstone import Player
from endstone.command import CommandSender

from endstone_essentials_be.utils.forms import forms_enabled, open_menu


class KitCommands:
    def __init__(self, plugin) -> None:
        self._plugin = plugin

    def register(self) -> dict:
        return {"kit": self.kit}

    def kit(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            self._plugin.messages.send_error(sender, "general.player-only")
            return True
        player = sender
        msg = self._plugin.messages
        kits = self._plugin.kits

        # /kit <ชื่อ> - รับตรง ๆ
        if args:
            kits.give(player, args[0])
            return True

        usable = kits.usable_names(player)
        if not usable:
            msg.send_error(player, "kit.none")
            return True

        if not forms_enabled(self._plugin):
            msg.send(player, "kit.list", kits=", ".join(usable))
            return True

        # สร้างปุ่ม: ใส่เวลาที่เหลือต่อท้ายชื่อถ้าติด cooldown
        entries = []
        for name in usable:
            remaining = kits.remaining_cooldown(player, name)
            if remaining == -1:
                label = msg.tr("kit.button-once", kit=name)
            elif remaining > 0:
                label = msg.tr("kit.button-cooldown", kit=name,
                               time=msg.format_duration(remaining))
            else:
                label = name
            # กดปุ่มแล้วเรียก give ตรง ๆ - ถ้าติด cooldown จะแจ้งเวลาที่เหลือเอง
            entries.append((label, None, lambda p, n=name: kits.give(p, n)))

        open_menu(self._plugin, player, msg.tr("kit.form-title"),
                  msg.tr("kit.form-content"), entries)
        return True
