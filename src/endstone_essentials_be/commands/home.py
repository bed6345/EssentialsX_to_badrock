# ============================================================
# home.py (commands) - /home /sethome /delhome /homes
#
# /home ไม่ใส่ชื่อ: มี home เดียว = วาร์ปเลย, หลายอัน = เปิด ActionForm
# /delhome ไม่ใส่ชื่อ: ฟอร์มเลือก + MessageForm ยืนยันก่อนลบ
# การวาร์ปทุกทาง (พิมพ์/ฟอร์ม) ผ่าน TeleportManager เสมอ
# ============================================================

from __future__ import annotations

from endstone import Player
from endstone.command import CommandSender

from endstone_essentials_be.utils.forms import forms_enabled, open_confirm, open_menu


class HomeCommands:
    def __init__(self, plugin) -> None:
        self._plugin = plugin

    def register(self) -> dict:
        return {
            "home": self.home,
            "sethome": self.sethome,
            "delhome": self.delhome,
            "homes": self.homes,
        }

    # ---------- ตัวช่วย ----------

    def _as_player(self, sender: CommandSender):
        """คำสั่งหมวดนี้ใช้ได้เฉพาะผู้เล่นในเกม"""
        if isinstance(sender, Player):
            return sender
        self._plugin.messages.send_error(sender, "general.player-only")
        return None

    def _teleport_home(self, player: Player, name: str) -> None:
        """วาร์ปไป home ตามชื่อ (จุดเดียวที่ใช้ทั้งจากคำสั่งและปุ่มฟอร์ม)"""
        msg = self._plugin.messages
        loc = self._plugin.homes.get_home(player, name)
        if loc is None:
            msg.send_error(player, "home.not-found", home=name.lower())
            return
        self._plugin.teleport.request_teleport(
            player, loc, "home.teleported", {"home": name.lower()})

    # ---------- /home ----------

    def home(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        msg = self._plugin.messages

        # /home <ชื่อ> - วาร์ปตรงโดยไม่เปิดฟอร์ม
        if args:
            self._teleport_home(player, args[0])
            return True

        homes = self._plugin.homes.get_homes(player)
        if not homes:
            msg.send_error(player, "home.none")
            return True

        names = sorted(homes.keys())
        # มี home เดียว -> วาร์ปเลยไม่ต้องเปิดฟอร์ม
        if len(names) == 1:
            self._teleport_home(player, names[0])
            return True

        # ปิดระบบฟอร์ม -> แสดงรายชื่อเป็นข้อความแทน
        if not forms_enabled(self._plugin):
            msg.send(player, "home.list", homes=", ".join(names))
            return True

        entries = [
            (name, None, lambda p, n=name: self._teleport_home(p, n))
            for name in names
        ]
        open_menu(self._plugin, player, msg.tr("home.form-title"),
                  msg.tr("home.form-content"), entries)
        return True

    # ---------- /sethome ----------

    def sethome(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        msg = self._plugin.messages

        name = (args[0] if args else "home").lower()
        ok, reason = self._plugin.homes.set_home(player, name)
        if not ok and reason == "limit":
            msg.send_error(player, "home.set-limit",
                           max=self._plugin.homes.max_homes(player))
            return True
        msg.send(player, "home.set", home=name)
        return True

    # ---------- /delhome ----------

    def _confirm_delete(self, player: Player, name: str) -> None:
        """เปิด MessageForm ยืนยันก่อนลบ home"""
        msg = self._plugin.messages

        def do_delete(p: Player) -> None:
            if self._plugin.homes.del_home(p, name):
                msg.send(p, "home.deleted", home=name)
            else:
                msg.send_error(p, "home.not-found", home=name)

        open_confirm(
            self._plugin, player,
            msg.tr("home.delete-form-title"),
            msg.tr("home.confirm-delete", home=name),
            msg.tr("form.yes"), msg.tr("form.no"),
            on_yes=do_delete,
        )

    def delhome(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        msg = self._plugin.messages

        # /delhome <ชื่อ> - ลบตรง ๆ ไม่ต้องยืนยัน
        if args:
            name = args[0].lower()
            if self._plugin.homes.del_home(player, name):
                msg.send(player, "home.deleted", home=name)
            else:
                msg.send_error(player, "home.not-found", home=name)
            return True

        homes = sorted(self._plugin.homes.get_homes(player).keys())
        if not homes:
            msg.send_error(player, "home.none")
            return True

        # ปิดฟอร์ม -> ต้องพิมพ์ชื่อเอง
        if not forms_enabled(self._plugin):
            msg.send(player, "home.list", homes=", ".join(homes))
            return True

        entries = [
            (name, None, lambda p, n=name: self._confirm_delete(p, n))
            for name in homes
        ]
        open_menu(self._plugin, player, msg.tr("home.delete-form-title"),
                  msg.tr("home.delete-form-content"), entries)
        return True

    # ---------- /homes ----------

    def homes(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        msg = self._plugin.messages

        homes = self._plugin.homes.get_homes(player)
        if not homes:
            msg.send_error(player, "home.none")
            return True
        # แสดงชื่อ + มิติ ไว้ดูเฉย ๆ
        parts = []
        for name in sorted(homes.keys()):
            dim = homes[name].get("dimension", "?")
            parts.append(f"{name} §7({dim})§r")
        msg.send(player, "home.list", homes=", ".join(parts))
        msg.send(player, "home.limit-info",
                 count=len(homes), max=self._plugin.homes.max_homes(player))
        return True
