# ============================================================
# warp.py (commands) - /warp /setwarp /delwarp /spawn /setspawn
#
# /warp ไม่ใส่ชื่อ: เปิดฟอร์มแสดงเฉพาะ warp ที่ผู้เล่นมีสิทธิ์ใช้
# ============================================================

from __future__ import annotations

from endstone import Player
from endstone.command import CommandSender

from endstone_essentials_be.utils.forms import forms_enabled, open_menu


class WarpCommands:
    def __init__(self, plugin) -> None:
        self._plugin = plugin

    def register(self) -> dict:
        return {
            "warp": self.warp,
            "setwarp": self.setwarp,
            "delwarp": self.delwarp,
            "spawn": self.spawn,
            "setspawn": self.setspawn,
        }

    def _as_player(self, sender: CommandSender):
        if isinstance(sender, Player):
            return sender
        self._plugin.messages.send_error(sender, "general.player-only")
        return None

    # ---------- /warp ----------

    def _teleport_warp(self, player: Player, name: str) -> None:
        """วาร์ปไป warp ตามชื่อ (ใช้ทั้งจากคำสั่งและปุ่มฟอร์ม)"""
        msg = self._plugin.messages
        name = name.lower()
        loc = self._plugin.warps.get_warp(name)
        if loc is None:
            msg.send_error(player, "warp.not-found", warp=name)
            return
        if not self._plugin.warps.can_use(player, name):
            msg.send_error(player, "warp.no-permission", warp=name)
            return
        self._plugin.teleport.request_teleport(
            player, loc, "warp.teleported", {"warp": name})

    def warp(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        msg = self._plugin.messages

        # /warp <ชื่อ> - วาร์ปตรง
        if args:
            self._teleport_warp(player, args[0])
            return True

        usable = self._plugin.warps.usable_names(player)
        if not usable:
            msg.send_error(player, "warp.none")
            return True

        if not forms_enabled(self._plugin):
            msg.send(player, "warp.list", warps=", ".join(usable))
            return True

        entries = [
            (name, None, lambda p, n=name: self._teleport_warp(p, n))
            for name in usable
        ]
        open_menu(self._plugin, player, msg.tr("warp.form-title"),
                  msg.tr("warp.form-content"), entries)
        return True

    # ---------- /setwarp /delwarp (แอดมิน) ----------

    def setwarp(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        if not args:
            return False  # ให้เซิร์ฟเวอร์แสดงวิธีใช้
        name = args[0].lower()
        self._plugin.warps.set_warp(name, player.location)
        self._plugin.messages.send(player, "warp.set", warp=name)
        return True

    def delwarp(self, sender: CommandSender, args: list[str]) -> bool:
        if not args:
            return False
        name = args[0].lower()
        msg = self._plugin.messages
        if self._plugin.warps.del_warp(name):
            msg.send(sender, "warp.deleted", warp=name)
        else:
            msg.send_error(sender, "warp.not-found", warp=name)
        return True

    # ---------- /spawn /setspawn ----------

    def spawn(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        msg = self._plugin.messages
        loc = self._plugin.warps.get_spawn()
        if loc is None:
            msg.send_error(player, "spawn.not-set")
            return True
        self._plugin.teleport.request_teleport(player, loc, "spawn.teleported", {})
        return True

    def setspawn(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        self._plugin.warps.set_spawn(player.location)
        self._plugin.messages.send(player, "spawn.set")
        return True
