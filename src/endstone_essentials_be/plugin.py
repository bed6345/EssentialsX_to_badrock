# ============================================================
# plugin.py - คลาสหลักของ EssentialsBE
#
# หน้าที่:
#   - ประกาศคำสั่ง + permission ทั้งหมด (class attributes ตามสเปก Endstone)
#   - โหลด config.yml / kits.yml / messages/*.yml (คัดลอกไฟล์เริ่มต้นให้ก่อน)
#   - สร้าง managers และผูก event ทั้งหมด
#   - dispatch คำสั่งไปยัง handler ของแต่ละหมวด
#   - autosave userdata ทุก 5 นาที
#
# หมายเหตุเรื่องชื่อคำสั่ง: ทุกคำสั่งตั้งชื่อไม่ชนกับ vanilla อยู่แล้ว
# และมี alias สำรองขึ้นต้นด้วย "e" (เช่น /ehome) เผื่อชนกับปลั๊กอินอื่น
# ============================================================
# ห้ามใส่ `from __future__ import annotations` ในไฟล์นี้:
# มันทำให้ annotation ของ event handler กลายเป็น string
# แล้ว Endstone จับคู่ event ไม่ได้ (invalid event handler signature)

import os

from endstone import ColorFormat, Player
from endstone.command import Command, CommandSender
from endstone.event import (
    ActorDamageEvent,
    PlayerCommandEvent,
    PlayerDeathEvent,
    PlayerJoinEvent,
    PlayerMoveEvent,
    PlayerQuitEvent,
    event_handler,
)
from endstone.plugin import Plugin

from endstone_essentials_be.commands.home import HomeCommands
from endstone_essentials_be.commands.kit import KitCommands
from endstone_essentials_be.commands.misc import MiscCommands
from endstone_essentials_be.commands.tpa import TpaCommands
from endstone_essentials_be.commands.warp import WarpCommands
from endstone_essentials_be.managers.home import HomeManager
from endstone_essentials_be.managers.interceptor import CommandInterceptor
from endstone_essentials_be.managers.kit import KitManager
from endstone_essentials_be.managers.playerdata import PlayerDataManager
from endstone_essentials_be.managers.teleport import TeleportManager
from endstone_essentials_be.managers.tpa import TpaManager
from endstone_essentials_be.managers.warp import WarpManager
from endstone_essentials_be.utils.messages import Messages
from endstone_essentials_be.utils.storage import load_yaml


class EssentialsBE(Plugin):
    # ต้องตรงกับเวอร์ชัน API ของเซิร์ฟเวอร์ Endstone
    api_version = "0.11"

    # ---------- ประกาศคำสั่งทั้งหมด ----------
    commands = {
        # --- Home ---
        "home": {
            "description": "วาร์ปไป home ของคุณ (ไม่ใส่ชื่อ = เปิดเมนู)",
            "usages": ["/home [home: string]"],
            "aliases": ["ehome"],
            "permissions": ["essentials.home"],
        },
        "sethome": {
            "description": "ตั้ง home ที่ตำแหน่งปัจจุบัน",
            "usages": ["/sethome [name: string]"],
            "aliases": ["esethome"],
            "permissions": ["essentials.sethome"],
        },
        "delhome": {
            "description": "ลบ home (ไม่ใส่ชื่อ = เปิดเมนูเลือก)",
            "usages": ["/delhome [home: string]"],
            "aliases": ["edelhome"],
            "permissions": ["essentials.delhome"],
        },
        "homes": {
            "description": "ดูรายชื่อ home ทั้งหมดของคุณ",
            "usages": ["/homes"],
            "aliases": ["ehomes"],
            "permissions": ["essentials.homes"],
        },
        # --- Warp / Spawn ---
        "warp": {
            "description": "วาร์ปไปจุด warp (ไม่ใส่ชื่อ = เปิดเมนู)",
            "usages": ["/warp [warp: string]"],
            "aliases": ["ewarp"],
            "permissions": ["essentials.warp"],
        },
        "setwarp": {
            "description": "สร้าง/ย้ายจุด warp (แอดมิน)",
            "usages": ["/setwarp <name: string>"],
            "aliases": ["esetwarp"],
            "permissions": ["essentials.setwarp"],
        },
        "delwarp": {
            "description": "ลบจุด warp (แอดมิน)",
            "usages": ["/delwarp <name: string>"],
            "aliases": ["edelwarp"],
            "permissions": ["essentials.delwarp"],
        },
        "spawn": {
            "description": "วาร์ปไปจุด spawn ของเซิร์ฟเวอร์",
            "usages": ["/spawn"],
            "aliases": ["espawn"],
            "permissions": ["essentials.spawn"],
        },
        "setspawn": {
            "description": "ตั้งจุด spawn ของเซิร์ฟเวอร์ (แอดมิน)",
            "usages": ["/setspawn"],
            "aliases": ["esetspawn"],
            "permissions": ["essentials.setspawn"],
        },
        # --- TPA ---
        "tpa": {
            "description": "ขอวาร์ปไปหาผู้เล่นอื่น (ไม่ใส่ชื่อ = เปิดเมนู)",
            "usages": ["/tpa [player: string]"],
            "aliases": ["etpa"],
            "permissions": ["essentials.tpa"],
        },
        "tpahere": {
            "description": "ขอให้ผู้เล่นอื่นวาร์ปมาหาคุณ (ไม่ใส่ชื่อ = เปิดเมนู)",
            "usages": ["/tpahere [player: string]"],
            "aliases": ["etpahere"],
            "permissions": ["essentials.tpahere"],
        },
        "tpaccept": {
            "description": "ยอมรับคำขอวาร์ป",
            "usages": ["/tpaccept [player: string]"],
            "aliases": ["etpaccept"],
            "permissions": ["essentials.tpaccept"],
        },
        "tpdeny": {
            "description": "ปฏิเสธคำขอวาร์ป",
            "usages": ["/tpdeny [player: string]"],
            "aliases": ["etpdeny"],
            "permissions": ["essentials.tpdeny"],
        },
        "tpacancel": {
            "description": "ยกเลิกคำขอวาร์ปที่คุณส่งไป",
            "usages": ["/tpacancel"],
            "aliases": ["etpacancel"],
            "permissions": ["essentials.tpacancel"],
        },
        "tptoggle": {
            "description": "เปิด/ปิดการรับคำขอวาร์ป",
            "usages": ["/tptoggle"],
            "aliases": ["etptoggle"],
            "permissions": ["essentials.tptoggle"],
        },
        # --- อื่น ๆ ---
        "back": {
            "description": "กลับไปจุดก่อนวาร์ป/จุดตายล่าสุด",
            "usages": ["/back"],
            "aliases": ["eback"],
            "permissions": ["essentials.back"],
        },
        "rtp": {
            "description": "สุ่มวาร์ปไปจุดปลอดภัย",
            "usages": ["/rtp"],
            "aliases": ["ertp"],
            "permissions": ["essentials.rtp"],
        },
        "tppos": {
            "description": "วาร์ปไปพิกัดที่กำหนด (แอดมิน)",
            "usages": ["/tppos <x: float> <y: float> <z: float>"],
            "aliases": ["etppos"],
            "permissions": ["essentials.tppos"],
        },
        "top": {
            "description": "วาร์ปขึ้นบล็อกบนสุด ณ จุดปัจจุบัน",
            "usages": ["/top"],
            "aliases": ["etop"],
            "permissions": ["essentials.top"],
        },
        "tps": {
            "description": "ดู TPS ของเซิร์ฟเวอร์ และ ping ของคุณ",
            "usages": ["/tps"],
            "aliases": ["etps", "ping"],
            "permissions": ["essentials.tps"],
        },
        # --- Kit ---
        "kit": {
            "description": "รับชุดไอเทม (ไม่ใส่ชื่อ = เปิดเมนู)",
            "usages": ["/kit [kit: string]"],
            "aliases": ["ekit", "kits"],
            "permissions": ["essentials.kit"],
        },
    }

    # ---------- ประกาศ permission ----------
    # รูปแบบ essentials.<command> - OP ได้ทุกสิทธิ์ / ผู้เล่นทั่วไปได้ชุดพื้นฐาน
    permissions = {
        # คำสั่งพื้นฐานของผู้เล่นทั่วไป
        "essentials.home": {"description": "ใช้ /home", "default": True},
        "essentials.sethome": {"description": "ใช้ /sethome", "default": True},
        "essentials.delhome": {"description": "ใช้ /delhome", "default": True},
        "essentials.homes": {"description": "ใช้ /homes", "default": True},
        "essentials.warp": {"description": "ใช้ /warp", "default": True},
        "essentials.spawn": {"description": "ใช้ /spawn", "default": True},
        "essentials.tpa": {"description": "ใช้ /tpa", "default": True},
        "essentials.tpahere": {"description": "ใช้ /tpahere", "default": True},
        "essentials.tpaccept": {"description": "ใช้ /tpaccept", "default": True},
        "essentials.tpdeny": {"description": "ใช้ /tpdeny", "default": True},
        "essentials.tpacancel": {"description": "ใช้ /tpacancel", "default": True},
        "essentials.tptoggle": {"description": "ใช้ /tptoggle", "default": True},
        "essentials.back": {"description": "ใช้ /back", "default": True},
        "essentials.back.ondeath": {
            "description": "บันทึกจุดตายให้ /back", "default": True},
        "essentials.rtp": {"description": "ใช้ /rtp", "default": True},
        "essentials.top": {"description": "ใช้ /top", "default": True},
        "essentials.tps": {"description": "ใช้ /tps", "default": True},
        "essentials.kit": {"description": "ใช้ /kit", "default": True},
        # คำสั่งแอดมิน
        "essentials.setwarp": {"description": "ใช้ /setwarp", "default": "op"},
        "essentials.delwarp": {"description": "ใช้ /delwarp", "default": "op"},
        "essentials.setspawn": {"description": "ใช้ /setspawn", "default": "op"},
        "essentials.tppos": {"description": "ใช้ /tppos", "default": "op"},
        "essentials.teleport.timer.bypass": {
            "description": "ข้าม warmup/cooldown การวาร์ป", "default": "op"},
        # โควตา home (ตัวอย่างระดับที่ประกาศไว้ - ปลั๊กอิน permission กำหนดเพิ่มได้)
        "essentials.sethome.multiple.2": {
            "description": "มี home ได้ 2 อัน", "default": False},
        "essentials.sethome.multiple.3": {
            "description": "มี home ได้ 3 อัน", "default": False},
        "essentials.sethome.multiple.5": {
            "description": "มี home ได้ 5 อัน", "default": False},
        "essentials.sethome.multiple.10": {
            "description": "มี home ได้ 10 อัน", "default": False},
    }

    # ---------- วงจรชีวิต ----------

    def on_load(self) -> None:
        self.logger.info("กำลังโหลด EssentialsBE...")

    def on_enable(self) -> None:
        try:
            # คัดลอกไฟล์ตั้งค่าเริ่มต้นไปยัง plugins/essentials_be/ (ถ้ายังไม่มี)
            for resource in ("config.yml", "kits.yml",
                             "messages/th.yml", "messages/en.yml"):
                try:
                    self.save_resources(resource, replace=False)
                except Exception as exc:
                    self.logger.error(f"คัดลอกไฟล์ {resource} ไม่สำเร็จ: {exc}")

            # โหลด config.yml (เก็บใน self.settings - ไม่ใช้ self.config
            # เพราะของ Endstone ผูกกับ config.toml)
            self.settings: dict = load_yaml(
                os.path.join(self.data_folder, "config.yml"), {}) or {}

            # สร้างระบบทั้งหมด (ลำดับสำคัญ: messages/playerdata ก่อนตัวอื่น)
            self.messages = Messages(self)
            self.playerdata = PlayerDataManager(self)
            self.teleport = TeleportManager(self)
            self.homes = HomeManager(self)
            self.warps = WarpManager(self)
            self.tpa = TpaManager(self)
            self.kits = KitManager(self)
            self.interceptor = CommandInterceptor(self)

            # รวม handler ของทุกหมวดคำสั่งเข้าตารางเดียว
            self._handlers: dict = {}
            for group in (HomeCommands(self), WarpCommands(self),
                          TpaCommands(self), KitCommands(self),
                          MiscCommands(self)):
                self._handlers.update(group.register())

            # ผูก event ทั้งหมด (handler อยู่ในคลาสนี้)
            self.register_events(self)

            # autosave userdata (ค่าเริ่มต้นทุก 5 นาที)
            minutes = max(1, int(self.settings.get("autosave-minutes", 5)))
            ticks = minutes * 60 * 20
            self.server.scheduler.run_task(
                self, self._autosave, delay=ticks, period=ticks)

            # รองรับ /reload ขณะมีผู้เล่นออนไลน์: โหลดข้อมูลให้ทันที
            for player in self.server.online_players:
                self.playerdata.load(player)

            self.logger.info(
                f"{ColorFormat.GREEN}เปิดใช้งาน EssentialsBE แล้ว "
                f"(คำสั่ง {len(self.commands)} | ภาษา: "
                f"{self.settings.get('language', 'th')})")
        except Exception as exc:
            self.logger.error(f"เปิดใช้งาน EssentialsBE ไม่สำเร็จ: {exc}")
            raise

    def on_disable(self) -> None:
        # ยกเลิกงานตั้งเวลาทั้งหมด แล้วเซฟข้อมูลทุกคนก่อนปิด
        try:
            self.server.scheduler.cancel_tasks(self)
        except Exception:
            pass
        try:
            saved = self.playerdata.save_all(only_dirty=False)
            self.logger.info(f"ปิด EssentialsBE แล้ว (บันทึก userdata {saved} คน)")
        except Exception as exc:
            self.logger.error(f"บันทึกข้อมูลตอนปิดปลั๊กอินไม่สำเร็จ: {exc}")

    # ---------- งานตั้งเวลา ----------

    def _autosave(self) -> None:
        """บันทึก userdata ที่มีการแก้ไขลงดิสก์"""
        try:
            saved = self.playerdata.save_all(only_dirty=True)
            if saved > 0:
                self.logger.debug(f"Autosave: บันทึก userdata {saved} คน")
        except Exception as exc:
            self.logger.error(f"Autosave ล้มเหลว: {exc}")

    # ---------- dispatch คำสั่ง ----------

    def on_command(self, sender: CommandSender, command: Command,
                   args: list[str]) -> bool:
        handler = self._handlers.get(command.name)
        if handler is None:
            return False
        try:
            return bool(handler(sender, args))
        except Exception as exc:
            # กันคำสั่งพังแล้วลาม: log ไว้แล้วแจ้งผู้ใช้สั้น ๆ
            self.logger.error(f"คำสั่ง /{command.name} ผิดพลาด: {exc}")
            self.messages.send_error(sender, "general.command-error")
            return True

    # ---------- Event ----------

    @event_handler
    def on_player_join(self, event: PlayerJoinEvent) -> None:
        # โหลด userdata เข้าแคชทันทีที่เข้าเซิร์ฟเวอร์
        try:
            self.playerdata.load(event.player)
        except Exception as exc:
            self.logger.error(f"โหลด userdata ของ {event.player.name} ไม่สำเร็จ: {exc}")

    @event_handler
    def on_player_quit(self, event: PlayerQuitEvent) -> None:
        # เก็บกวาดคำขอ tpa/warmup ที่ค้าง แล้วเซฟ+ปลดข้อมูลออกจากแคช
        try:
            self.tpa.on_quit(event.player)
            self.teleport.on_quit(event.player)
            self.playerdata.unload(event.player)
        except Exception as exc:
            self.logger.error(f"จัดการตอน {event.player.name} ออกไม่สำเร็จ: {exc}")

    @event_handler
    def on_player_death(self, event: PlayerDeathEvent) -> None:
        # บันทึกจุดตายให้ /back (ต้องมี essentials.back.ondeath)
        try:
            player = event.player
            if player.has_permission("essentials.back.ondeath"):
                self.teleport.record_back(player)
        except Exception as exc:
            self.logger.error(f"บันทึกจุดตายไม่สำเร็จ: {exc}")

    @event_handler
    def on_player_move(self, event: PlayerMoveEvent) -> None:
        # ขยับระหว่างรอ warmup = ยกเลิกการวาร์ป (เช็คเร็ว ๆ ก่อน กัน event ถี่)
        if not self.teleport.has_pending(event.player.xuid):
            return
        try:
            self.teleport.check_movement(event.player, event.to_location)
        except Exception as exc:
            self.logger.error(f"ตรวจการขยับระหว่าง warmup ผิดพลาด: {exc}")

    @event_handler
    def on_actor_damage(self, event: ActorDamageEvent) -> None:
        # โดนตีระหว่างรอ warmup = ยกเลิกการวาร์ป
        try:
            actor = event.actor
            if isinstance(actor, Player):
                self.teleport.on_damaged(actor)
        except Exception as exc:
            self.logger.error(f"ตรวจดาเมจระหว่าง warmup ผิดพลาด: {exc}")

    @event_handler
    def on_player_command(self, event: PlayerCommandEvent) -> None:
        # ระบบ interceptor: ดัก /tp ของ vanilla เพื่อบันทึกจุด /back
        self.interceptor.handle(event)
