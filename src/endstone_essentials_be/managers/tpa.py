# ============================================================
# tpa.py - ระบบคำขอวาร์ปหาผู้เล่น (/tpa, /tpahere)
#
# โครงสร้าง: คำขอเก็บตาม "ผู้รับ" -> {xuid ผู้ส่ง: TpaRequest}
# - คำขอหมดอายุอัตโนมัติตาม tpa-expire-seconds (ผ่าน scheduler)
# - ผู้รับได้ MessageForm เด้งทันที (ปิดได้ใน config: tpa-request-form)
#   ปิดฟอร์มโดยไม่กด = คำขอยังค้างอยู่ ใช้ /tpaccept /tpdeny ได้ตามปกติ
# - แจ้งข้อความทั้งสองฝ่ายทุกขั้นตอน
# ============================================================

from __future__ import annotations

from typing import Optional

from endstone import Player

# ประเภทคำขอ: "tpa" = ผู้ส่งวาร์ปไปหาผู้รับ / "tpahere" = ผู้รับวาร์ปมาหาผู้ส่ง
TYPE_TPA = "tpa"
TYPE_TPAHERE = "tpahere"


class TpaRequest:
    def __init__(self, sender: Player, target: Player, kind: str, task) -> None:
        self.sender_xuid = sender.xuid
        self.sender_name = sender.name
        self.target_xuid = target.xuid
        self.target_name = target.name
        self.kind = kind
        self.task = task  # task หมดอายุ (ยกเลิกเมื่อคำขอถูกจัดการแล้ว)


class TpaManager:
    def __init__(self, plugin) -> None:
        self._plugin = plugin
        # คำขอค้าง: {xuid ผู้รับ: {xuid ผู้ส่ง: TpaRequest}}
        self._incoming: dict[str, dict[str, TpaRequest]] = {}

    # ---------- ตัวช่วย ----------

    def _find_player(self, xuid: str) -> Optional[Player]:
        for p in self._plugin.server.online_players:
            if p.xuid == xuid:
                return p
        return None

    def requests_for(self, target: Player) -> list[TpaRequest]:
        """คำขอค้างทั้งหมดที่ส่งมาหาผู้เล่นคนนี้"""
        return list(self._incoming.get(target.xuid, {}).values())

    def outgoing_of(self, sender: Player) -> Optional[TpaRequest]:
        """คำขอที่ผู้เล่นคนนี้ส่งออกไป (คนหนึ่งส่งค้างได้ทีละ 1 คำขอ)"""
        for requests in self._incoming.values():
            req = requests.get(sender.xuid)
            if req is not None:
                return req
        return None

    def _remove(self, req: TpaRequest) -> None:
        """เอาคำขอออกจากระบบ + ยกเลิก task หมดอายุ"""
        requests = self._incoming.get(req.target_xuid)
        if requests is not None:
            requests.pop(req.sender_xuid, None)
            if not requests:
                del self._incoming[req.target_xuid]
        try:
            req.task.cancel()
        except Exception:
            pass

    # ---------- ส่งคำขอ ----------

    def send_request(self, sender: Player, target: Player, kind: str) -> None:
        msg = self._plugin.messages

        if target.xuid == sender.xuid:
            msg.send_error(sender, "tpa.self")
            return

        # ผู้รับปิดรับคำขอ (tptoggle)
        target_data = self._plugin.playerdata.get(target)
        if not target_data.get("tptoggle", True):
            msg.send_error(sender, "tpa.target-toggle-off", player=target.name)
            return

        # ส่งซ้ำหาคนเดิม/คนอื่นระหว่างมีคำขอค้าง -> ยกเลิกอันเก่าก่อนอัตโนมัติ
        old = self.outgoing_of(sender)
        if old is not None:
            self._remove(old)

        expire = int(self._plugin.settings.get("tpa-expire-seconds", 60))
        sender_xuid, target_xuid = sender.xuid, target.xuid

        def on_expire() -> None:
            requests = self._incoming.get(target_xuid, {})
            req = requests.get(sender_xuid)
            if req is None:
                return
            self._remove(req)
            s = self._find_player(sender_xuid)
            t = self._find_player(target_xuid)
            if s is not None:
                msg.send_error(s, "tpa.expired-sender", player=req.target_name)
            if t is not None:
                msg.send_error(t, "tpa.expired-target", player=req.sender_name)

        task = self._plugin.server.scheduler.run_task(
            self._plugin, on_expire, delay=max(1, expire) * 20)
        req = TpaRequest(sender, target, kind, task)
        self._incoming.setdefault(target.xuid, {})[sender.xuid] = req

        msg.send(sender, "tpa.sent", player=target.name)
        received_key = "tpa.received" if kind == TYPE_TPA else "tpahere.received"
        msg.send(target, received_key, player=sender.name)
        msg.send(target, "tpa.howto")

        # เด้งฟอร์มถามผู้รับทันที (ถ้าเปิดใช้ทั้ง use-forms และ tpa-request-form)
        from endstone_essentials_be.utils.forms import forms_enabled, open_confirm

        if forms_enabled(self._plugin) and bool(
                self._plugin.settings.get("tpa-request-form", True)):
            content_key = ("tpa.request-form-content"
                           if kind == TYPE_TPA else "tpahere.request-form-content")
            open_confirm(
                self._plugin,
                target,
                msg.tr("tpa.request-form-title"),
                msg.tr(content_key, player=sender.name),
                msg.tr("tpa.accept-button"),
                msg.tr("tpa.deny-button"),
                on_yes=lambda p, s=sender.xuid: self.accept(p, sender_xuid=s),
                on_no=lambda p, s=sender.xuid: self.deny(p, sender_xuid=s),
            )
            # หมายเหตุ: ปิดฟอร์มเฉย ๆ -> ไม่เรียกอะไร คำขอค้างจนหมดเวลาเอง

    # ---------- ยอมรับ / ปฏิเสธ / ยกเลิก ----------

    def _pick(self, target: Player, sender_name: Optional[str] = None,
              sender_xuid: Optional[str] = None) -> Optional[TpaRequest]:
        """เลือกคำขอของผู้รับ: ตาม xuid > ตามชื่อ > ถ้ามีอันเดียวใช้อันนั้น"""
        requests = self._incoming.get(target.xuid, {})
        if not requests:
            return None
        if sender_xuid is not None:
            return requests.get(sender_xuid)
        if sender_name is not None:
            for req in requests.values():
                if req.sender_name.lower() == sender_name.lower():
                    return req
            return None
        if len(requests) == 1:
            return next(iter(requests.values()))
        return None  # มีหลายคำขอ - ให้ผู้เรียกเปิดฟอร์มเลือกเอง

    def has_multiple(self, target: Player) -> bool:
        return len(self._incoming.get(target.xuid, {})) > 1

    def accept(self, target: Player, sender_name: Optional[str] = None,
               sender_xuid: Optional[str] = None) -> Optional[TpaRequest]:
        """ยอมรับคำขอ -> เริ่มวาร์ป (ผ่าน warmup/cooldown ของ TeleportManager)"""
        msg = self._plugin.messages
        req = self._pick(target, sender_name, sender_xuid)
        if req is None:
            return None
        self._remove(req)

        sender = self._find_player(req.sender_xuid)
        if sender is None:
            msg.send_error(target, "tpa.player-left", player=req.sender_name)
            return req

        msg.send(target, "tpa.accepted-target", player=sender.name)
        msg.send(sender, "tpa.accepted-sender", player=target.name)

        # tpa: ผู้ส่งวาร์ปไปหาผู้รับ / tpahere: ผู้รับวาร์ปมาหาผู้ส่ง
        if req.kind == TYPE_TPA:
            self._plugin.teleport.request_teleport(
                sender, target.location, "tpa.teleported", {"player": target.name})
        else:
            self._plugin.teleport.request_teleport(
                target, sender.location, "tpa.teleported", {"player": sender.name})
        return req

    def deny(self, target: Player, sender_name: Optional[str] = None,
             sender_xuid: Optional[str] = None) -> Optional[TpaRequest]:
        msg = self._plugin.messages
        req = self._pick(target, sender_name, sender_xuid)
        if req is None:
            return None
        self._remove(req)
        msg.send(target, "tpa.denied-target", player=req.sender_name)
        sender = self._find_player(req.sender_xuid)
        if sender is not None:
            msg.send_error(sender, "tpa.denied-sender", player=target.name)
        return req

    def cancel(self, sender: Player) -> bool:
        """ผู้ส่งยกเลิกคำขอของตัวเอง (/tpacancel)"""
        req = self.outgoing_of(sender)
        if req is None:
            return False
        self._remove(req)
        self._plugin.messages.send(sender, "tpa.cancelled", player=req.target_name)
        target = self._find_player(req.target_xuid)
        if target is not None:
            self._plugin.messages.send(target, "tpa.cancelled-target",
                                       player=sender.name)
        return True

    # ---------- เก็บกวาดเมื่อผู้เล่นออกจากเกม ----------

    def on_quit(self, player: Player) -> None:
        msg = self._plugin.messages
        xuid = player.xuid

        # คำขอที่คนอื่นส่งมาหาคนที่ออก -> แจ้งผู้ส่งว่าอีกฝ่ายออกจากเกม
        for req in list(self._incoming.get(xuid, {}).values()):
            self._remove(req)
            sender = self._find_player(req.sender_xuid)
            if sender is not None:
                msg.send_error(sender, "tpa.player-left", player=player.name)

        # คำขอที่คนที่ออกส่งไปหาคนอื่น -> แจ้งผู้รับ
        out = self.outgoing_of(player)
        if out is not None:
            self._remove(out)
            target = self._find_player(out.target_xuid)
            if target is not None:
                msg.send_error(target, "tpa.player-left", player=player.name)
