"""
NEKO BLOCK BREAKER v2  -  Brick Breaker versi pixel + kucing (Pygame)

Yang baru di versi ini:
- Desain dipoles: latar gradasi 4 tema + kota malam + bintang parallax + bintang jatuh,
  brick glossy, HUD berpanel, efek CRT (scanline + vignette), transisi fade.
- PAUSE  (P / ESC)  + menu jeda (lanjut, musik, menu utama). Otomatis pause saat jendela
  kehilangan fokus.
- Kucing OP: DEWA NEKO (rarity OP!) - bersayap & berhalo, nyawa awal 5, badan lebih
  lebar, damage boss +1, skill "Murka Dewa" (tembus + laser otomatis + perisai + lambat).
- GACHA KUCING: kumpulkan KOIN dari bermain, putar gacha (x1 / x10), ada rarity
  BIASA / LANGKA / EPIK / OP, sistem pity, duplikat jadi koin. Progres tersimpan otomatis.

Kontrol:
  Panah kiri/kanan atau A/D  : gerakkan kucing / pilih menu
  Mouse                      : gerakkan kucing, klik tombol/kartu
  SPASI / ENTER / klik kiri  : konfirmasi & luncurkan bola benang
  E / SHIFT / klik kanan     : pakai SKILL
  P / ESC                    : pause (saat main)
  G                          : buka gacha (title / pilih kucing / game over)
  C                          : ganti kucing (saat game over)
  M                          : musik on/off
  V                          : efek CRT on/off
  ESC                        : kembali / keluar
"""
import colorsys
import json
import math
import os
import random
import sys
from array import array
from functools import lru_cache

import pygame

pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()

# ---------------------------------------------------------------- Layar
LW, LH = 200, 160            # ukuran "layar pixel"
SCALE = 4                    # perbesaran
WIDTH, HEIGHT = LW * SCALE, LH * SCALE
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Neko Block Breaker")
canvas = pygame.Surface((LW, LH))
clock = pygame.time.Clock()
TICK = 0
crt_on = True
FOCUS_LOST = getattr(pygame, "WINDOWFOCUSLOST", None)


# ---------------------------------------------------------------- Font
def load_font(size):
    """Cari font bulat & tebal yang ada di komputer; kalau tidak ada pakai bawaan."""
    path = pygame.font.match_font(
        ["comicsansms", "trebuchetms", "verdana", "arialrounded", "arial"], bold=True)
    return pygame.font.Font(path, size) if path else pygame.font.Font(None, size + 6)


FONTS = {"xs": load_font(24), "s": load_font(32), "m": load_font(46), "b": load_font(74)}
OUTLINE = {"xs": 2, "s": 2, "m": 3, "b": 4}
TEXTQ = []   # antrean teks yang digambar setelah canvas di-zoom

# ---------------------------------------------------------------- Warna
BG = (28, 20, 48)
WHITE = (255, 255, 255)
ORANGE = (255, 163, 71)
ORANGE_D = (214, 110, 40)
PINK = (255, 140, 170)
DARK = (35, 25, 45)
YELLOW = (255, 225, 110)
FISH_C = (130, 210, 255)
YARN = (255, 105, 150)
GRAY = (170, 165, 200)
GREEN = (130, 255, 160)
RED = (255, 110, 130)
ROW_COLORS = [(255, 107, 129), (255, 168, 76), (255, 224, 102),
              (120, 220, 140), (110, 190, 255), (190, 150, 255),
              (255, 150, 220)]


def shade(c, d):
    return tuple(max(0, min(255, v + d)) for v in c)


# ---------------------------------------------------------------- Rarity gacha
RARITY = {
    "C": dict(name="BIASA", col=(190, 190, 215), w=55, refund=25, stars=1),
    "R": dict(name="LANGKA", col=(110, 190, 255), w=28, refund=50, stars=2),
    "E": dict(name="EPIK", col=(205, 130, 255), w=14, refund=100, stars=3),
    "O": dict(name="OP!!", col=(255, 205, 70), w=3, refund=400, stars=5),
}
GACHA_COST1, GACHA_COST10 = 100, 900
PITY_EPIC, PITY_OP = 10, 40

# ---------------------------------------------------------------- Karakter kucing
CATS = [
    dict(name="OYEN", skill="Cakar Super", icon=0, dur=360, cd=900, rarity="C",
         d1="Badan kucing melebar 2x selama 6 detik",
         d2="Cocok buat pemula, jarang meleset!",
         pal=dict(body=ORANGE, dark=ORANGE_D, eye=DARK, paws=WHITE, ear=ORANGE,
                  tail=ORANGE_D, stripes=True, mask=False, whisk=WHITE)),
    dict(name="MOCHI", skill="Waktu Lambat", icon=1, dur=300, cd=840, rarity="C",
         d1="Bola melambat 50% selama 5 detik",
         d2="Enak buat mengatur arah pantulan",
         pal=dict(body=(245, 245, 250), dark=(190, 190, 215), eye=(70, 100, 220),
                  paws=WHITE, ear=(245, 245, 250), tail=(200, 200, 222),
                  stripes=False, mask=False, whisk=WHITE)),
    dict(name="KURO", skill="Cakar Api", icon=2, dur=240, cd=1080, rarity="R",
         d1="Bola menembus semua brick selama 4 detik",
         d2="Sapu bersih satu baris sekaligus!",
         pal=dict(body=(70, 70, 92), dark=(40, 40, 58), eye=(255, 225, 80),
                  paws=(110, 110, 135), ear=(70, 70, 92), tail=(48, 48, 66),
                  stripes=False, mask=False, whisk=(200, 200, 220))),
    dict(name="ABU", skill="Meong Laser", icon=3, dur=0, cd=600, rarity="C",
         d1="Tembakkan 3 benang ke atas sekaligus",
         d2="Cooldown paling singkat, cuma 10 detik",
         pal=dict(body=(238, 222, 196), dark=(120, 85, 70), eye=(90, 170, 255),
                  paws=(120, 85, 70), ear=(120, 85, 70), tail=(120, 85, 70),
                  stripes=False, mask=True, whisk=WHITE)),
    dict(name="BOBA", skill="Bola Kembar", icon=4, dur=0, cd=960, needs_ball=True, rarity="R",
         d1="Lepaskan 2 bola tambahan sekaligus",
         d2="Satu bola jatuh? Masih ada cadangan!",
         pal=dict(body=(150, 100, 70), dark=(100, 62, 40), eye=(120, 225, 120),
                  paws=(235, 205, 175), ear=(150, 100, 70), tail=(100, 62, 40),
                  stripes=True, mask=False, whisk=WHITE)),
    dict(name="PINKY", skill="Perisai Hati", icon=5, dur=480, cd=1200, rarity="E",
         d1="Perisai di dasar layar, bola memantul 8 detik",
         d2="Aman buat yang sering kebobolan",
         pal=dict(body=(255, 172, 202), dark=(230, 120, 160), eye=(110, 60, 130),
                  paws=WHITE, ear=(255, 172, 202), tail=(230, 120, 160),
                  stripes=False, mask=False, whisk=WHITE)),
    dict(name="LUNA", skill="Ledakan Bulu", icon=6, dur=0, cd=1020, needs_ball=True, rarity="E",
         d1="Ledakan menghancurkan brick di sekitar bola",
         d2="Ampuh buat menyerang boss (3 damage)",
         pal=dict(body=(172, 142, 232), dark=(120, 90, 182), eye=(255, 240, 120),
                  paws=(222, 208, 252), ear=(172, 142, 232), tail=(120, 90, 182),
                  stripes=True, mask=False, whisk=WHITE)),
    dict(name="MOMO", skill="Hujan Ikan", icon=7, dur=0, cd=1500, rarity="E",
         d1="6 ikan jatuh dari langit, tiap ikan +25 skor",
         d2="Cooldown 25 detik, skor melesat!",
         pal=dict(body=(255, 214, 90), dark=(210, 150, 40), eye=(60, 150, 90),
                  paws=WHITE, ear=(255, 214, 90), tail=(210, 150, 40),
                  stripes=True, mask=False, whisk=WHITE)),
    # --- KUCING OP ---
    dict(name="DEWA", skill="Murka Dewa", icon=8, dur=600, cd=1200, rarity="O", op=True,
         d1="10 detik: tembus brick + laser otomatis + perisai",
         d2="Pasif: nyawa 5, badan lebar, boss kena +1",
         pal=dict(body=(255, 238, 160), dark=(214, 168, 60), eye=(150, 70, 220),
                  paws=WHITE, ear=(255, 220, 110), tail=(255, 250, 205),
                  stripes=True, mask=False, whisk=WHITE, halo=True, wings=True)),
]
SIL_PAL = dict(body=(44, 36, 72), dark=(32, 26, 54), eye=(44, 36, 72), paws=(44, 36, 72),
               ear=(44, 36, 72), tail=(36, 30, 60), stripes=False, mask=False,
               whisk=(60, 50, 96))
N_CATS = len(CATS)
GACHA_SLOT = N_CATS            # slot ke-10 di layar pilih kucing = tombol gacha
N_SLOTS = N_CATS + 1

# ---------------------------------------------------------------- Simpanan
SAVE_PATH = os.path.join(os.path.expanduser("~"), ".neko_block_breaker.json")
SAVE = dict(coins=300, owned=[0], hi=0, pity_epic=0, pity_op=0, pulls=0, char=0)


def load_save():
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        for k in SAVE:
            if k in d:
                SAVE[k] = d[k]
    except Exception:
        pass
    try:
        owned = [int(i) for i in SAVE["owned"] if 0 <= int(i) < N_CATS]
    except Exception:
        owned = []
    SAVE["owned"] = sorted(set(owned)) or [0]
    for k in ("coins", "hi", "pity_epic", "pity_op", "pulls", "char"):
        try:
            SAVE[k] = max(0, int(SAVE[k]))
        except Exception:
            SAVE[k] = 0
    if SAVE["char"] not in SAVE["owned"]:
        SAVE["char"] = SAVE["owned"][0]


def save_game():
    try:
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(SAVE, f)
    except Exception:
        pass


def roll_rarity(min_r=None):
    tiers = ["C", "R", "E", "O"]
    ws = [RARITY[k]["w"] for k in tiers]
    if SAVE["pity_op"] >= PITY_OP - 1:
        r = "O"
    else:
        if SAVE["pity_epic"] >= PITY_EPIC - 1:
            ws[0] = ws[1] = 0
        if min_r == "R":
            ws[0] = 0
        r = random.choices(tiers, ws)[0]
    SAVE["pity_op"] = 0 if r == "O" else SAVE["pity_op"] + 1
    SAVE["pity_epic"] = 0 if r in ("E", "O") else SAVE["pity_epic"] + 1
    return r


# ---------------------------------------------------------------- Teks
def txt(s, size, color, cx=None, x=0, y=0, wave=0, rainbow=False):
    """Masukkan teks ke antrean. Koordinat dalam piksel logis (200x160)."""
    TEXTQ.append((s, size, color, cx, x, y, wave, rainbow))


@lru_cache(maxsize=1024)
def render_text(size, s, color):
    f = FONTS[size]
    off = OUTLINE[size]
    img = f.render(s, True, color)
    ol = f.render(s, True, (12, 6, 24))
    w, h = img.get_size()
    surf = pygame.Surface((w + off * 2, h + off * 2), pygame.SRCALPHA)
    for dx in range(-off, off + 1):
        for dy in range(-off, off + 1):
            if (dx or dy) and dx * dx + dy * dy <= off * off + 1:
                surf.blit(ol, (off + dx, off + dy))
    surf.blit(img, (off, off))
    return surf


def rainbow_color(i):
    h = (i * 0.07 + TICK * 0.012) % 1.0
    r, g, b = colorsys.hsv_to_rgb(h, 0.5, 1.0)
    return (int(r * 15) * 17, int(g * 15) * 17, int(b * 15) * 17)


def flush_text(ox, oy):
    for s, size, color, cx, x, y, wave, rainbow in TEXTQ:
        off = OUTLINE[size]
        py = y * SCALE
        if wave or rainbow:
            widths = [FONTS[size].size(ch)[0] for ch in s]
            total = sum(widths)
            px = cx * SCALE - total // 2 if cx is not None else x * SCALE
            for i, ch in enumerate(s):
                if ch != " ":
                    col = rainbow_color(i) if rainbow else color
                    img = render_text(size, ch, col)
                    yo = int(math.sin(TICK * 0.1 + i * 0.6) * wave)
                    screen.blit(img, (px + ox - off, py + oy + yo - off))
                px += widths[i]
        else:
            img = render_text(size, s, color)
            w = img.get_width()
            if w > WIDTH - 12:      # jaga-jaga kalau terlalu lebar
                img = pygame.transform.smoothscale(
                    img, (WIDTH - 12, int(img.get_height() * (WIDTH - 12) / w)))
                w = img.get_width()
            px = cx * SCALE - w // 2 if cx is not None else x * SCALE - off
            screen.blit(img, (px + ox, py + oy - off))
    TEXTQ.clear()


def panel(surf, rect, fill=(18, 12, 36, 215), border=(160, 130, 255)):
    r = pygame.Rect(rect)
    s = pygame.Surface(r.size, pygame.SRCALPHA)
    s.fill(fill)
    surf.blit(s, r.topleft)
    pygame.draw.line(surf, border, (r.x + 1, r.y), (r.right - 2, r.y))
    pygame.draw.line(surf, border, (r.x + 1, r.bottom - 1), (r.right - 2, r.bottom - 1))
    pygame.draw.line(surf, border, (r.x, r.y + 1), (r.x, r.bottom - 2))
    pygame.draw.line(surf, border, (r.right - 1, r.y + 1), (r.right - 1, r.bottom - 2))
    # kilau tipis di sisi atas panel
    hi = shade(border, 40)
    pygame.draw.line(surf, hi, (r.x + 2, r.y + 1), (min(r.x + 8, r.right - 3), r.y + 1))


# ---------------------------------------------------------------- Latar & overlay
THEMES = [((22, 14, 50), (70, 40, 110)),     # malam ungu
          ((26, 16, 66), (176, 80, 112)),    # senja
          ((40, 10, 28), (124, 30, 54)),     # boss merah
          ((10, 26, 58), (34, 112, 130))]    # laut
BG_CACHE = {}


def build_bg(i):
    top, bot = THEMES[i]
    s = pygame.Surface((LW, LH))
    steps = 14
    for y in range(LH):
        k = int(y / LH * steps) / steps
        col = tuple(int(top[j] + (bot[j] - top[j]) * k) for j in range(3))
        pygame.draw.line(s, col, (0, y), (LW, y))
    # bulan
    mx, my = 172, 38
    pygame.draw.circle(s, shade(bot, -20), (mx, my), 11)
    pygame.draw.circle(s, (255, 244, 205), (mx, my), 7)
    for dx, dy in ((-2, -2), (2, 1), (-1, 3)):
        s.set_at((mx + dx, my + dy), (232, 218, 170))
    # kota malam
    rnd = random.Random(i * 7 + 3)
    sky = shade(bot, -62)
    x = 0
    while x < LW:
        w = rnd.randint(8, 16)
        h = rnd.randint(6, 20)
        pygame.draw.rect(s, sky, (x, LH - h, w, h))
        pygame.draw.line(s, shade(sky, 14), (x, LH - h), (x + w - 1, LH - h))
        for wy in range(LH - h + 3, LH - 2, 4):
            for wx in range(x + 2, x + w - 2, 4):
                if rnd.random() < 0.28:
                    s.set_at((wx, wy), (170, 140, 80))
        x += w + rnd.randint(0, 2)
    return s


def get_bg(i):
    if i not in BG_CACHE:
        BG_CACHE[i] = build_bg(i)
    return BG_CACHE[i]


def build_overlay():
    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, SCALE):
        pygame.draw.line(s, (0, 0, 0, 24), (0, y + SCALE - 1), (WIDTH, y + SCALE - 1))
    vig = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i in range(12):
        a = int(75 * (1 - i / 12) ** 2)
        pygame.draw.rect(vig, (0, 0, 0, a), (i * 6, i * 4, WIDTH - i * 12, HEIGHT - i * 8), 6)
    s.blit(vig, (0, 0))
    return s


OVERLAY = build_overlay()
FADE = pygame.Surface((WIDTH, HEIGHT))
FADE.fill((0, 0, 0))
FADE_T = 14
HUD_BAR = pygame.Surface((LW, 12), pygame.SRCALPHA)
HUD_BAR.fill((10, 6, 24, 150))
