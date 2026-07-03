# ============================================================
# tpa.py (commands) - /tpa /tpahere /tpaccept /tpdeny /tpacancel /tptoggle
#
# /tpa และ /tpahere ไม่ใส่ชื่อ: ฟอร์มเลือกผู้เล่นออนไลน์
# (ไม่แสดงตัวเองและคนที่ปิด tptoggle)
# /tpaccept ไม่ใส่ชื่อ + มีหลายคำขอ: ฟอร์มเลือกว่ารับของใคร
# ============================================================

from __future__ import annotations

from endstone import Player
from endstone.command import CommandSender

from endstone_essentials_be.managers.tpa import TYPE_TPA, TYPE_TPAHERE
from endstone_essentials_be.utils.forms import forms_enabled, open_menu


class TpaCommands:
    def __init__(self, plugin) -> None:
        self._plugin = plugin

    def register(self) -> dict:
        return {
            "tpa": lambda s, a: self._send(s, a, TYPE_TPA),
            "tpahere": lambda s, a: self._send(s, a, TYPE_TPAHERE),
            "tpaccept": self.tpaccept,
            "tpdeny": self.tpdeny,
            "tpacancel": self.tpacancel,
            "tptoggle": self.tptoggle,
        }

    def _as_player(self, sender: CommandSender):
        if isinstance(sender, Player):
            return sender
        self._plugin.messages.send_error(sender, "general.player-only")
        return None

    # ---------- /tpa /tpahere ----------

    def _candidates(self, player: Player) -> list[Player]:
        """ผู้เล่นที่ส่งคำขอหาได้: ออนไลน์ ไม่ใช่ตัวเอง และเปิดรับ tpa"""
        result = []
        for other in self._plugin.server.online_players:
            if other.xuid == player.xuid:
                continue
            if not self._plugin.playerdata.get(other).get("tptoggle", True):
                continue
            result.append(other)
        return result

    def _send(self, sender: CommandSender, args: list[str], kind: str) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        msg = self._plugin.messages

        # /tpa <ผู้เล่น> - ส่งคำขอตรง
        if args:
            target = self._plugin.server.get_player(args[0])
            if target is None:
                msg.send_error(player, "general.player-not-found", player=args[0])
                return True
            self._plugin.tpa.send_request(player, target, kind)
            return True

        candidates = self._candidates(player)
        if not candidates:
            msg.send_error(player, "tpa.no-players")
            return True

        # ปิดฟอร์ม -> ต้องพิมพ์ชื่อเอง
        if not forms_enabled(self._plugin):
            msg.send(player, "tpa.online-list",
                     players=", ".join(p.name for p in candidates))
            return True

        title_key = "tpa.form-title" if kind == TYPE_TPA else "tpahere.form-title"
        entries = [
            (other.name, None,
             lambda p, name=other.name: self._send_to_name(p, name, kind))
            for other in candidates
        ]
        open_menu(self._plugin, player, msg.tr(title_key),
                  msg.tr("tpa.form-content"), entries)
        return True

    def _send_to_name(self, player: Player, name: str, kind: str) -> None:
        """callback จากปุ่มฟอร์ม - เป้าหมายอาจออกจากเกมไปแล้วระหว่างเปิดฟอร์ม"""
        target = self._plugin.server.get_player(name)
        if target is None:
            self._plugin.messages.send_error(player, "general.player-not-found",
                                             player=name)
            return
        self._plugin.tpa.send_request(player, target, kind)

    # ---------- /tpaccept /tpdeny ----------

    def tpaccept(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        msg = self._plugin.messages

        requests = self._plugin.tpa.requests_for(player)
        if not requests:
            msg.send_error(player, "tpa.no-requests")
            return True

        # ระบุชื่อ หรือมีคำขอเดียว -> จัดการเลย
        if args:
            if self._plugin.tpa.accept(player, sender_name=args[0]) is None:
                msg.send_error(player, "tpa.no-request-from", player=args[0])
            return True
        if len(requests) == 1:
            self._plugin.tpa.accept(player)
            return True

        # หลายคำขอ + เปิดฟอร์ม -> ให้เลือกว่ารับของใคร
        if forms_enabled(self._plugin):
            entries = [
                (req.sender_name, None,
                 lambda p, x=req.sender_xuid:
                     self._plugin.tpa.accept(p, sender_xuid=x))
                for req in requests
            ]
            open_menu(self._plugin, player, msg.tr("tpa.accept-form-title"),
                      msg.tr("tpa.accept-form-content"), entries)
        else:
            msg.send(player, "tpa.pending-list",
                     players=", ".join(r.sender_name for r in requests))
        return True

    def tpdeny(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        msg = self._plugin.messages

        requests = self._plugin.tpa.requests_for(player)
        if not requests:
            msg.send_error(player, "tpa.no-requests")
            return True

        if args:
            if self._plugin.tpa.deny(player, sender_name=args[0]) is None:
                msg.send_error(player, "tpa.no-request-from", player=args[0])
            return True
        if len(requests) == 1:
            self._plugin.tpa.deny(player)
            return True

        # หลายคำขอ - ปฏิเสธทั้งหมดทีเดียว (พิมพ์ชื่อได้ถ้าอยากเลือก)
        for req in list(requests):
            self._plugin.tpa.deny(player, sender_xuid=req.sender_xuid)
        return True

    # ---------- /tpacancel /tptoggle ----------

    def tpacancel(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        if not self._plugin.tpa.cancel(player):
            self._plugin.messages.send_error(player, "tpa.no-outgoing")
        return True

    def tptoggle(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        data = self._plugin.playerdata.get(player)
        new_state = not data.get("tptoggle", True)
        data["tptoggle"] = new_state  # บันทึกลง userdata คงอยู่หลังรีสตาร์ต
        self._plugin.playerdata.mark_dirty(player.xuid)
        key = "tpa.toggle-on" if new_state else "tpa.toggle-off"
        self._plugin.messages.send(player, key)
        return True
