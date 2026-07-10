# EssentialsBE

ปลั๊กอิน **Endstone** (Python) สำหรับ Minecraft Bedrock Dedicated Server
เลียนแบบฟีเจอร์หลักของ EssentialsX ฝั่ง Java: Home / Warp / Spawn / TPA / Kit / Back / RTP
พร้อม **Form UI** (ActionForm / MessageForm) รองรับ 2 ภาษา (ไทย/อังกฤษ)

- ต้องการ Endstone **0.11.x** ขึ้นไป
- ข้อมูลผู้เล่นเก็บเป็น JSON ต่อคน เขียนไฟล์แบบ atomic กันไฟล์พัง
- ทุกการวาร์ป (รวมถึงจากปุ่มในฟอร์ม) ผ่าน warmup/cooldown เดียวกันทั้งหมด

## วิธีติดตั้ง

### แบบที่ 1: ติดตั้งจากซอร์ส (แนะนำตอนพัฒนา)

```bash
# ในโฟลเดอร์โปรเจกต์นี้
pip install .
# แล้วรีสตาร์ตเซิร์ฟเวอร์ Endstone
```

### แบบที่ 2: สร้างไฟล์ .whl แล้ววางในโฟลเดอร์ plugins

```bash
pip install build
python -m build --wheel
# ได้ไฟล์ dist/endstone_essentials_be-1.0.0-py3-none-any.whl
# นำไปวางในโฟลเดอร์ plugins/ ของเซิร์ฟเวอร์ แล้วรีสตาร์ต
```

เปิดเซิร์ฟเวอร์ครั้งแรก ปลั๊กอินจะสร้างไฟล์ตั้งค่าทั้งหมดที่
`plugins/essentials_be/` ให้อัตโนมัติ

## โครงสร้างไฟล์ในโฟลเดอร์ข้อมูล (`plugins/essentials_be/`)

```
plugins/essentials_be/
├── config.yml          # ตั้งค่าหลัก (ภาษา, ฟอร์ม, warmup/cooldown, rtp ฯลฯ)
├── kits.yml            # นิยาม kit ทั้งหมด (มีตัวอย่าง starter, daily)
├── warps.json          # จุด warp (สร้างเมื่อใช้ /setwarp)
├── spawn.json          # จุด spawn (สร้างเมื่อใช้ /setspawn)
├── messages/
│   ├── th.yml          # ข้อความภาษาไทย (ค่าเริ่มต้น)
│   └── en.yml          # ข้อความภาษาอังกฤษ
└── userdata/
    └── <xuid>.json     # ข้อมูลต่อคน: homes, จุด /back, cooldown kit, tptoggle
```

## ค่าตั้งใน config.yml

| คีย์ | ค่าเริ่มต้น | ความหมาย |
|---|---|---|
| `language` | `th` | ภาษาข้อความ (`th` / `en`) |
| `use-forms` | `true` | เปิด/ปิดระบบ Form UI ทั้งหมด (ปิดแล้ว fallback เป็นข้อความ) |
| `default-homes` | `3` | จำนวน home ต่อคน ถ้าไม่มี permission `.multiple.<n>` |
| `per-warp-permission` | `false` | ต้องมี `essentials.warps.<ชื่อ>` ถึงจะใช้ warp นั้นได้ |
| `tpa-request-form` | `true` | เด้ง MessageForm ถามผู้รับเมื่อมีคำขอ tpa |
| `tpa-expire-seconds` | `60` | อายุคำขอ tpa ก่อนหมดเวลาอัตโนมัติ |
| `teleport-warmup` | `3` | วินาทีที่ต้องยืนนิ่งก่อนวาร์ป (ขยับ/โดนตี = ยกเลิก) |
| `teleport-cooldown` | `3` | วินาทีกันสแปมวาร์ป |
| `rtp.min-radius` / `rtp.max-radius` | `100` / `1000` | รัศมีสุ่มวาร์ปรอบจุด center |
| `rtp.center-x` / `rtp.center-z` | `0` / `0` | จุดศูนย์กลางการสุ่ม |
| `rtp.cooldown` | `60` | cooldown ของ /rtp ต่อคน (วินาที) |
| `rtp.max-attempts` | `15` | จำนวนครั้งที่ลองหาจุดปลอดภัย |
| `interceptors.vanilla-tp-back` | `true` | ดัก `/tp` ของ vanilla เพื่อบันทึกจุด /back |
| `autosave-minutes` | `5` | ความถี่บันทึก userdata อัตโนมัติ |

## ตารางคำสั่ง + Permission ทั้งหมด

ทุกคำสั่งมี alias สำรองขึ้นต้นด้วย `e` (เช่น `/ehome`) เผื่อชื่อชนกับปลั๊กอินอื่น
ค่าเริ่มต้น: **✅ = ผู้เล่นทุกคนใช้ได้**, **OP = เฉพาะ OP**

| คำสั่ง | ความสามารถ | Permission | ค่าเริ่มต้น |
|---|---|---|---|
| `/home [ชื่อ]` | วาร์ปไป home (ไม่ใส่ชื่อ = เมนู, มีอันเดียว = วาร์ปเลย) | `essentials.home` | ✅ |
| `/sethome [ชื่อ]` | ตั้ง home (ค่าเริ่มต้นชื่อ `home`) | `essentials.sethome` | ✅ |
| `/delhome [ชื่อ]` | ลบ home (ไม่ใส่ชื่อ = เมนู + ยืนยันก่อนลบ) | `essentials.delhome` | ✅ |
| `/homes` | ดูรายชื่อ home ทั้งหมดเป็นข้อความ | `essentials.homes` | ✅ |
| — | โควตา home เพิ่ม เช่น `.multiple.5` = 5 อัน | `essentials.sethome.multiple.<n>` | ❌ (ให้ผ่านปลั๊กอิน permission) |
| `/warp [ชื่อ]` | วาร์ปไป warp (ไม่ใส่ชื่อ = เมนูเฉพาะที่มีสิทธิ์) | `essentials.warp` | ✅ |
| — | สิทธิ์ราย warp (เมื่อเปิด `per-warp-permission`) | `essentials.warps.<ชื่อ>` | OP |
| `/setwarp <ชื่อ>` | สร้าง/ย้ายจุด warp | `essentials.setwarp` | OP |
| `/delwarp <ชื่อ>` | ลบจุด warp | `essentials.delwarp` | OP |
| `/spawn` | วาร์ปไปจุด spawn ของเซิร์ฟเวอร์ | `essentials.spawn` | ✅ |
| `/setspawn` | ตั้งจุด spawn ของเซิร์ฟเวอร์ | `essentials.setspawn` | OP |
| `/tpa [ผู้เล่น]` | ขอวาร์ปไปหา (ไม่ใส่ชื่อ = เมนูผู้เล่นออนไลน์) | `essentials.tpa` | ✅ |
| `/tpahere [ผู้เล่น]` | ขอให้อีกฝ่ายวาร์ปมาหา | `essentials.tpahere` | ✅ |
| `/tpaccept [ผู้เล่น]` | ยอมรับคำขอ (หลายคำขอ = เมนูเลือก) | `essentials.tpaccept` | ✅ |
| `/tpdeny [ผู้เล่น]` | ปฏิเสธคำขอ | `essentials.tpdeny` | ✅ |
| `/tpacancel` | ยกเลิกคำขอที่ส่งไป | `essentials.tpacancel` | ✅ |
| `/tptoggle` | เปิด/ปิดการรับคำขอ (บันทึกถาวร) | `essentials.tptoggle` | ✅ |
| `/back` | กลับจุดก่อนวาร์ป/จุดตายล่าสุด | `essentials.back` | ✅ |
| — | บันทึกจุดตายให้ /back | `essentials.back.ondeath` | ✅ |
| `/rtp` | สุ่มวาร์ปหาจุดปลอดภัย (มี cooldown ต่อคน) | `essentials.rtp` | ✅ |
| `/tppos <x> <y> <z>` | วาร์ปไปพิกัด | `essentials.tppos` | OP |
| `/top` | ขึ้นบล็อกบนสุด ณ จุดปัจจุบัน | `essentials.top` | ✅ |
| `/tps` (หรือ `/ping`) | ดู TPS / MSPT ของเซิร์ฟเวอร์ และ ping ของคุณ | `essentials.tps` | ✅ |
| `/kit [ชื่อ]` | รับ kit (ไม่ใส่ชื่อ = เมนูพร้อมสถานะ cooldown) | `essentials.kit` | ✅ |
| — | สิทธิ์ราย kit (เมื่อ kit ตั้ง `public: false`) | `essentials.kits.<ชื่อ>` | OP |
| — | ข้าม warmup/cooldown การวาร์ปทั้งหมด | `essentials.teleport.timer.bypass` | OP |

## การเพิ่ม Kit ใหม่

แก้ `plugins/essentials_be/kits.yml`:

```yaml
kits:
  pvp:
    cooldown: 3600        # วินาที (-1 = รับได้ครั้งเดียวตลอดกาล)
    public: false         # ต้องมี essentials.kits.pvp (OP ผ่านเสมอ)
    auto-equip: true      # สวมเกราะให้อัตโนมัติถ้าช่องว่าง
    items:
      - item: minecraft:diamond_sword
        amount: 1
        name: "§bดาบ PVP"
        lore:
          - "§7ของรางวัลสายบู๊"
        enchantments:
          sharpness: 3
      - item: minecraft:golden_apple
        amount: 8
```

แล้วรีสตาร์ตเซิร์ฟเวอร์ (หรือ `/reload`) — ถ้าช่องเก็บของผู้เล่นเต็ม
ของที่เหลือจะถูกดรอปลงพื้นพร้อมข้อความแจ้งเตือน

## หมายเหตุด้านเทคนิค

- **คำสั่ง vanilla**: ปลั๊กอินไม่ override คำสั่ง vanilla (`/tp`, `/give`,
  `/gamemode` ฯลฯ ใช้ของเกมตามปกติ) มีเพียงระบบ interceptor ที่ดัก
  `PlayerCommandEvent` ของ `/tp` เพื่อบันทึกจุด `/back` เท่านั้น
  (ปิดได้ใน config)
- **Warmup/Cooldown**: ใช้ scheduler ของ Endstone ทั้งหมด ไม่มีการบล็อกเธรดหลัก
- **ข้ามมิติ**: home/warp/spawn/back เก็บมิติ (Overworld/Nether/TheEnd)
  และวาร์ปข้ามมิติได้ถูกต้อง
- **ฟอร์ม**: ผู้เล่นปิดฟอร์มโดยไม่เลือก = ไม่เกิดอะไรและไม่มี error
  ส่วนคำขอ tpa ที่ปิดฟอร์มทิ้งจะยังค้างอยู่จนหมดเวลา และใช้
  `/tpaccept`, `/tpdeny` พิมพ์เองได้เสมอ

## โครงสร้างซอร์สโค้ด

```
src/endstone_essentials_be/
├── plugin.py            # คลาสหลัก: ประกาศ commands/permissions, event, autosave
├── commands/            # ตัวจัดการคำสั่งแยกหมวด (home, warp, tpa, kit, misc)
├── managers/            # ตรรกะแต่ละระบบ (playerdata, teleport, home, warp,
│                        #   tpa, kit, interceptor)
├── utils/               # ตัวช่วยกลาง (storage, messages, forms)
├── config.yml           # ไฟล์ตั้งค่าเริ่มต้น (ถูกคัดลอกไป data folder)
├── kits.yml
└── messages/th.yml, en.yml
```
