# ============================================================
# forms.py - ตัวสร้าง Form UI กลาง (ใช้ร่วมกันทุกคำสั่ง)
#
# กติกากลางตามสเปก:
#   1) เปิด/ปิดทั้งระบบด้วย use-forms ใน config (เช็คผ่าน forms_enabled)
#   2) การวาร์ปจากปุ่มในฟอร์มต้องเรียกผ่าน TeleportManager เสมอ
#      (จึงผ่าน warmup/cooldown เหมือนพิมพ์คำสั่ง) - ผู้เรียกเป็นคนส่ง callback
#   3) ผู้เล่นปิดฟอร์มโดยไม่เลือก -> ไม่เกิดอะไรและไม่มี error
#   4) ทุกคำสั่งใช้ helper ที่นี่ ไม่สร้างฟอร์มเองซ้ำ ๆ
# ============================================================

from __future__ import annotations

from typing import Callable, Optional, Sequence, Tuple

from endstone import Player
from endstone.form import ActionForm, MessageForm

# entry ของเมนู: (ข้อความบนปุ่ม, ไอคอน (หรือ None), callback รับ Player)
MenuEntry = Tuple[str, Optional[str], Callable[[Player], None]]


def forms_enabled(plugin) -> bool:
    """เช็คสวิตช์รวม use-forms ใน config.yml"""
    return bool(plugin.settings.get("use-forms", True))


def _safe(plugin, callback: Callable[[Player], None]) -> Callable[[Player], None]:
    """ครอบ callback ของฟอร์มด้วย try/except กัน error หลุดไป client"""

    def wrapper(player: Player) -> None:
        try:
            callback(player)
        except Exception as exc:  # จุดเสี่ยง: callback ฟอร์มถูกเรียกภายหลัง
            plugin.logger.error(f"เกิดข้อผิดพลาดใน callback ของฟอร์ม: {exc}")

    return wrapper


def open_menu(
    plugin,
    player: Player,
    title: str,
    content: str,
    entries: Sequence[MenuEntry],
) -> None:
    """เปิด ActionForm แบบรายการปุ่ม - ปิดฟอร์มเฉย ๆ = ไม่เกิดอะไร"""
    form = ActionForm(title=title, content=content)
    for text, icon, callback in entries:
        form.add_button(text, icon=icon, on_click=_safe(plugin, callback))
    player.send_form(form)


def open_confirm(
    plugin,
    player: Player,
    title: str,
    content: str,
    yes_text: str,
    no_text: str,
    on_yes: Callable[[Player], None],
    on_no: Optional[Callable[[Player], None]] = None,
) -> None:
    """เปิด MessageForm ยืนยัน 2 ปุ่ม (ปุ่มแรก = ยืนยัน)"""

    def submit(p: Player, index: int) -> None:
        try:
            if index == 0:
                on_yes(p)
            elif on_no is not None:
                on_no(p)
        except Exception as exc:
            plugin.logger.error(f"เกิดข้อผิดพลาดใน callback ของฟอร์มยืนยัน: {exc}")

    player.send_form(
        MessageForm(
            title=title,
            content=content,
            button1=yes_text,
            button2=no_text,
            on_submit=submit,
        )
    )
