# ============================================================
# teleport.py - ศูนย์กลางการวาร์ปทั้งหมดของปลั๊กอิน
#
# ทุกการวาร์ป (home/warp/spawn/tpa/back/rtp/tppos/top และจากปุ่มในฟอร์ม)
# ต้องผ่าน request_teleport() ที่นี่ เพื่อให้ได้พฤติกรรมเดียวกันหมด:
#   - teleport-cooldown: กันสแปมวาร์ป
#   - teleport-warmup: ต้องยืนนิ่ง ถ้าขยับ/โดนตี ยกเลิก
#   - บันทึกจุด /back ก่อนวาร์ปทุกครั้ง
#   - ข้ามได้ด้วย permission essentials.teleport.timer.bypass
# ใช้ scheduler ของ Endstone เท่านั้น (ห้าม time.sleep บล็อกเธรดหลัก)
# ============================================================

from __future__ import annotations

import time
from typing import Callable, Optional

from endstone import Player
from endstone.level import Location

BYPASS_PERM = "essentials.teleport.timer.bypass"


class _Pending:
    """คำขอวาร์ปที่กำลังรอ warmup อยู่"""

    def __init__(self, task, origin: Location, dest: Location,
                 done_key: Optional[str], done_args: dict) -> None:
        self.task = task
        self.origin = origin
        self.dest = dest
        self.done_key = done_key
        self.done_args = done_args


class TeleportManager:
    def __init__(self, plugin) -> None:
        self._plugin = plugin
        self._pending: dict[str, _Pending] = {}  # xuid -> คำขอที่รอ warmup

    # ---------- ค่า config ----------

    @property
    def _warmup(self) -> int:
        return int(self._plugin.settings.get("teleport-warmup", 0))

    @property
    def _cooldown(self) -> int:
        return int(self._plugin.settings.get("teleport-cooldown", 0))

    # ---------- จุด /back ----------

    def record_back(self, player: Player) -> None:
        """บันทึกตำแหน่งปัจจุบันเป็นจุด /back (เรียกก่อนวาร์ป และตอนตาย)"""
        from endstone_essentials_be.utils.storage import location_to_dict

        try:
            data = self._plugin.playerdata.get(player)
            data["back"] = location_to_dict(player.location)
            self._plugin.playerdata.mark_dirty(player.xuid)
        except Exception as exc:
            self._plugin.logger.error(f"บันทึกจุด /back ของ {player.name} ไม่สำเร็จ: {exc}")

    # ---------- การขอวาร์ป ----------

    def request_teleport(
        self,
        player: Player,
        dest: Location,
        done_key: Optional[str] = None,
        done_args: Optional[dict] = None,
        record_back: bool = True,
    ) -> bool:
        """ขอวาร์ปผู้เล่นไปยัง dest ผ่านกติกา warmup/cooldown
        คืน True ถ้าเริ่มกระบวนการได้ (วาร์ปทันทีหรือเข้าคิว warmup)"""
        msg = self._plugin.messages
        data = self._plugin.playerdata.get(player)
        bypass = player.has_permission(BYPASS_PERM)

        # กันกดซ้ำระหว่างรอ warmup อยู่
        if player.xuid in self._pending:
            msg.send_error(player, "teleport.already-pending")
            return False

        # เช็ค cooldown (ยกเว้นคนมีสิทธิ์ bypass)
        if not bypass and self._cooldown > 0:
            remaining = int(data.get("tp_last", 0)) + self._cooldown - int(time.time())
            if remaining > 0:
                msg.send_error(player, "teleport.cooldown",
                               time=msg.format_duration(remaining))
                return False

        done_args = done_args or {}

        # ไม่มี warmup หรือ bypass -> วาร์ปทันที
        if bypass or self._warmup <= 0:
            self._do_teleport(player, dest, done_key, done_args, record_back)
            return True

        # มี warmup -> ตั้งเวลาแล้วรอ ถ้าขยับ/โดนตีจะถูกยกเลิก
        xuid = player.xuid

        def finish() -> None:
            pending = self._pending.pop(xuid, None)
            if pending is None:
                return
            target = self._plugin.server.get_player(player.unique_id)
            if target is None:  # ออกจากเกมไปแล้ว
                return
            self._do_teleport(target, pending.dest, pending.done_key,
                              pending.done_args, record_back)

        task = self._plugin.server.scheduler.run_task(
            self._plugin, finish, delay=self._warmup * 20)
        self._pending[xuid] = _Pending(task, player.location, dest, done_key, done_args)
        msg.send(player, "teleport.warmup", seconds=self._warmup)
        return True

    def _do_teleport(self, player: Player, dest: Location,
                     done_key: Optional[str], done_args: dict,
                     record_back: bool) -> None:
        """วาร์ปจริง: เก็บจุด back -> teleport -> ตั้ง cooldown -> แจ้งผล"""
        msg = self._plugin.messages
        try:
            if record_back:
                self.record_back(player)
            player.teleport(dest)
            data = self._plugin.playerdata.get(player)
            data["tp_last"] = int(time.time())
            self._plugin.playerdata.mark_dirty(player.xuid)
            if done_key:
                msg.send(player, done_key, **done_args)
        except Exception as exc:
            self._plugin.logger.error(f"วาร์ป {player.name} ไม่สำเร็จ: {exc}")
            msg.send_error(player, "teleport.failed")

    # ---------- การยกเลิก warmup ----------

    def has_pending(self, xuid: str) -> bool:
        return xuid in self._pending

    def cancel_pending(self, xuid: str, reason_key: Optional[str] = None) -> None:
        """ยกเลิกคำขอที่รอ warmup อยู่ พร้อมแจ้งเหตุผล (ถ้ามี)"""
        pending = self._pending.pop(xuid, None)
        if pending is None:
            return
        try:
            pending.task.cancel()
        except Exception:
            pass
        if reason_key:
            player = None
            for p in self._plugin.server.online_players:
                if p.xuid == xuid:
                    player = p
                    break
            if player is not None:
                self._plugin.messages.send_error(player, reason_key)

    def check_movement(self, player: Player, to_location: Location) -> None:
        """เรียกจาก PlayerMoveEvent - ขยับเกิน 0.35 บล็อกระหว่าง warmup = ยกเลิก"""
        pending = self._pending.get(player.xuid)
        if pending is None:
            return
        origin = pending.origin
        if (origin.dimension.name != to_location.dimension.name
                or origin.distance_squared(to_location) > 0.35 * 0.35):
            self.cancel_pending(player.xuid, "teleport.warmup-cancelled-move")

    def on_damaged(self, player: Player) -> None:
        """เรียกจาก ActorDamageEvent - โดนตีระหว่าง warmup = ยกเลิก"""
        if player.xuid in self._pending:
            self.cancel_pending(player.xuid, "teleport.warmup-cancelled-damage")

    def on_quit(self, player: Player) -> None:
        """ผู้เล่นออกจากเกมระหว่างรอ warmup - เก็บกวาด task ทิ้ง"""
        self.cancel_pending(player.xuid)
