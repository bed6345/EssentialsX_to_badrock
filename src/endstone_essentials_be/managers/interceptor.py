# ============================================================
# interceptor.py - ระบบดักคำสั่ง vanilla ผ่าน PlayerCommandEvent
#
# ห้าม override คำสั่ง vanilla โดยตรง (ทำไม่ได้บน BDS) จึงใช้วิธีดัก event
# เวอร์ชันนี้ใช้แค่: ดัก /tp ของ vanilla เพื่อบันทึกจุด /back ก่อนวาร์ป
# (ไม่ cancel คำสั่ง แค่แอบเก็บตำแหน่ง) เปิด/ปิดใน config:
#   interceptors.vanilla-tp-back
# ============================================================

from __future__ import annotations

from typing import Callable

from endstone.event import PlayerCommandEvent


class CommandInterceptor:
    """ทะเบียนตัวดักคำสั่ง: จับคู่ชื่อคำสั่งแรก -> เรียก handler"""

    def __init__(self, plugin) -> None:
        self._plugin = plugin
        # {ชื่อคำสั่ง (ตัวเล็ก): handler(event)}
        self._handlers: dict[str, Callable[[PlayerCommandEvent], None]] = {}
        self._setup_defaults()

    def _setup_defaults(self) -> None:
        """ลงทะเบียนตัวดักตามค่า config"""
        cfg = self._plugin.settings.get("interceptors", {}) or {}
        if bool(cfg.get("vanilla-tp-back", True)):
            self.register(["tp", "teleport"], self._record_back_on_tp)

    def register(self, commands: list[str],
                 handler: Callable[[PlayerCommandEvent], None]) -> None:
        for cmd in commands:
            self._handlers[cmd.lower()] = handler

    def handle(self, event: PlayerCommandEvent) -> None:
        """เรียกจาก PlayerCommandEvent ใน plugin หลัก"""
        try:
            command_line = event.command.strip()
            if command_line.startswith("/"):
                command_line = command_line[1:]
            if not command_line:
                return
            name = command_line.split()[0].lower()
            handler = self._handlers.get(name)
            if handler is not None:
                handler(event)
        except Exception as exc:
            self._plugin.logger.error(f"ตัวดักคำสั่งทำงานผิดพลาด: {exc}")

    # ---------- ตัวดักที่มากับปลั๊กอิน ----------

    def _record_back_on_tp(self, event: PlayerCommandEvent) -> None:
        """ผู้เล่นใช้ /tp ของ vanilla -> เก็บจุดปัจจุบันไว้ให้ /back ก่อน
        (ไม่ cancel ปล่อยให้เกมวาร์ปตามปกติ)"""
        self._plugin.teleport.record_back(event.player)
