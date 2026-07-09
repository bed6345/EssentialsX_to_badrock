# ============================================================
# misc.py (commands) - /back /rtp /tppos /top /tps
#
# /back: กลับจุดก่อนวาร์ป/จุดตายล่าสุด
# /rtp:  สุ่มวาร์ปหาจุดปลอดภัย (ไม่ลงลาวา/น้ำ/ช่องว่าง) + cooldown ต่อคน
# /tppos: วาร์ปไปพิกัด (แอดมิน)
# /top:  ขึ้นบล็อกบนสุด ณ จุดปัจจุบัน
# /tps:  ดู TPS / MSPT ของเซิร์ฟเวอร์ และ ping ของผู้ใช้คำสั่ง
# ============================================================

from __future__ import annotations

import math
import random
import time

from endstone import Player
from endstone.command import CommandSender
from endstone.level import Location

from endstone_essentials_be.utils.storage import dict_to_location

# บล็อกที่ห้ามยืน (จุดลงของ rtp/top ต้องไม่ใช่พวกนี้)
_UNSAFE_BLOCKS = {
    "minecraft:water", "minecraft:flowing_water",
    "minecraft:lava", "minecraft:flowing_lava",
    "minecraft:cactus", "minecraft:magma_block", "minecraft:fire",
    "minecraft:soul_fire", "minecraft:sweet_berry_bush", "minecraft:powder_snow",
}


class MiscCommands:
    def __init__(self, plugin) -> None:
        self._plugin = plugin

    def register(self) -> dict:
        return {
            "back": self.back,
            "rtp": self.rtp,
            "tppos": self.tppos,
            "top": self.top,
            "tps": self.tps,
        }

    def _as_player(self, sender: CommandSender):
        if isinstance(sender, Player):
            return sender
        self._plugin.messages.send_error(sender, "general.player-only")
        return None

    # ---------- /back ----------

    def back(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        msg = self._plugin.messages

        data = self._plugin.playerdata.get(player)
        back = data.get("back")
        loc = dict_to_location(self._plugin.server, back) if back else None
        if loc is None:
            msg.send_error(player, "back.none")
            return True
        # record_back=True ทำให้ /back สลับไป-กลับสองจุดได้เหมือน EssentialsX
        self._plugin.teleport.request_teleport(player, loc, "back.teleported", {})
        return True

    # ---------- /rtp ----------

    def rtp(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        msg = self._plugin.messages
        cfg = self._plugin.settings.get("rtp", {}) or {}

        # cooldown ต่อคน (เก็บใน userdata)
        data = self._plugin.playerdata.get(player)
        cooldown = int(cfg.get("cooldown", 60))
        if not player.has_permission("essentials.teleport.timer.bypass"):
            remaining = int(data.get("rtp_last", 0)) + cooldown - int(time.time())
            if remaining > 0:
                msg.send_error(player, "rtp.cooldown",
                               time=msg.format_duration(remaining))
                return True

        loc = self._find_safe_spot(player, cfg)
        if loc is None:
            msg.send_error(player, "rtp.fail")
            return True

        data["rtp_last"] = int(time.time())
        self._plugin.playerdata.mark_dirty(player.xuid)
        self._plugin.teleport.request_teleport(
            player, loc, "rtp.teleported",
            {"x": int(loc.x), "y": int(loc.y), "z": int(loc.z)})
        return True

    def _find_safe_spot(self, player: Player, cfg: dict):
        """สุ่มหาจุดปลอดภัยในรัศมี min/max รอบจุด center ใน config
        เช็ค: บล็อกที่ยืนไม่ใช่ของอันตราย และไม่ใช่การตกลงช่องว่าง"""
        dimension = player.dimension
        min_r = int(cfg.get("min-radius", 100))
        max_r = int(cfg.get("max-radius", 1000))
        center_x = int(cfg.get("center-x", 0))
        center_z = int(cfg.get("center-z", 0))
        attempts = int(cfg.get("max-attempts", 15))

        for _ in range(max(1, attempts)):
            # สุ่มมุม + ระยะ ให้กระจายเป็นวงแหวนรอบจุด center
            distance = random.uniform(min_r, max_r)
            angle = random.uniform(0, 2 * math.pi)
            x = int(center_x + distance * math.cos(angle))
            z = int(center_z + distance * math.sin(angle))
            try:
                y = dimension.get_highest_block_y_at(x, z)
                if y <= -64 or y >= 320:  # chunk ยังไม่โหลด/ค่าประหลาด
                    continue
                block = dimension.get_block_at(x, y, z)
                if block.type in _UNSAFE_BLOCKS or block.type == "minecraft:air":
                    continue
                return Location(dimension, x + 0.5, float(y + 1), z + 0.5)
            except Exception:
                # chunk ไม่โหลด/อ่านบล็อกไม่ได้ - ลองจุดใหม่
                continue
        return None

    # ---------- /tppos (แอดมิน) ----------

    def tppos(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        if len(args) < 3:
            return False  # แสดงวิธีใช้
        msg = self._plugin.messages
        try:
            x, y, z = float(args[0]), float(args[1]), float(args[2])
        except ValueError:
            msg.send_error(player, "tppos.invalid")
            return True
        dest = Location(player.dimension, x, y, z,
                        player.location.pitch, player.location.yaw)
        self._plugin.teleport.request_teleport(
            player, dest, "tppos.teleported",
            {"x": int(x), "y": int(y), "z": int(z)})
        return True

    # ---------- /top ----------

    def top(self, sender: CommandSender, args: list[str]) -> bool:
        player = self._as_player(sender)
        if player is None:
            return True
        msg = self._plugin.messages
        loc = player.location
        try:
            y = player.dimension.get_highest_block_y_at(loc.block_x, loc.block_z)
        except Exception as exc:
            self._plugin.logger.error(f"/top หาบล็อกบนสุดไม่สำเร็จ: {exc}")
            msg.send_error(player, "teleport.failed")
            return True
        dest = Location(player.dimension, loc.block_x + 0.5, float(y + 1),
                        loc.block_z + 0.5, loc.pitch, loc.yaw)
        self._plugin.teleport.request_teleport(player, dest, "top.teleported", {})
        return True

    # ---------- /tps ----------

    def tps(self, sender: CommandSender, args: list[str]) -> bool:
        """แสดง TPS/MSPT ของเซิร์ฟเวอร์ (คอนโซลใช้ได้)
        ถ้าผู้ใช้เป็นผู้เล่นจะแสดง ping ของตัวเองด้วย"""
        msg = self._plugin.messages
        server = self._plugin.server

        msg.send(sender, "tps.header")
        msg.send(sender, "tps.tps",
                 current=self._format_tps(float(server.current_tps)),
                 average=self._format_tps(float(server.average_tps)))
        msg.send(sender, "tps.mspt", mspt=f"{float(server.average_mspt):.1f}")

        if isinstance(sender, Player):
            msg.send(sender, "tps.ping",
                     ping=self._format_ping(self._ping_ms(sender)))
        return True

    @staticmethod
    def _format_tps(tps: float) -> str:
        """ใส่สีตามสุขภาพเซิร์ฟเวอร์: เขียว >= 18, เหลือง >= 15, แดงต่ำกว่านั้น
        (เพดานแสดงผลที่ 20.0 เหมือน EssentialsX)"""
        color = "§a" if tps >= 18 else ("§e" if tps >= 15 else "§c")
        return f"{color}{min(tps, 20.0):.1f}"

    @staticmethod
    def _format_ping(ms: int) -> str:
        """ใส่สีตามความหน่วง: เขียว < 100ms, เหลือง < 200ms, แดงมากกว่านั้น"""
        color = "§a" if ms < 100 else ("§e" if ms < 200 else "§c")
        return f"{color}{ms} ms"

    @staticmethod
    def _ping_ms(player: Player) -> int:
        # Endstone คืน ping เป็น datetime.timedelta (เผื่อบางเวอร์ชันคืนตัวเลขตรง ๆ)
        ping = player.ping
        total_seconds = getattr(ping, "total_seconds", None)
        if callable(total_seconds):
            return int(total_seconds() * 1000)
        return int(ping)
