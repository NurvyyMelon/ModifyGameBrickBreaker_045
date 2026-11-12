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

# ---------------------------------------------------------------- Suara (sintesis)
RATE = 22050
SND = {}
MUSIC_CH = None
music_on = True
SOUND_OK = False


def synth(f0, f1, dur, vol=0.3, wave="square", vib=0.0):
    n = int(RATE * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / n
        if wave == "meow":
            f = 520 + 380 * math.sin(math.pi * t) - 120 * t
        else:
            f = f0 + (f1 - f0) * t
        if vib:
            f *= 1 + vib * math.sin(i / RATE * 6.2832 * 7)
        phase += f / RATE
        ph = phase % 1.0
        if wave == "square":
            v = 1.0 if ph < 0.5 else -1.0
        elif wave == "sine":
            v = math.sin(6.2832 * ph)
        elif wave == "tri":
            v = 4 * abs(ph - 0.5) - 1
        elif wave == "noise":
            v = random.uniform(-1, 1)
        elif wave == "meow":
            v = (math.sin(6.2832 * ph) + 0.5 * math.sin(12.5664 * ph)
                 + 0.25 * math.sin(18.85 * ph)) / 1.75
        else:
            v = 0
        env = math.sin(math.pi * t) ** 0.6 if wave == "meow" else (1 - t) ** 1.4
        env *= min(1.0, i / 80)
        out.append(int(v * env * vol * 32767))
    return out


def seq(notes, wave="square", vol=0.25):
    out = []
    for f, d in notes:
        out += synth(f, f, d, vol, wave) if f else [0] * int(RATE * d)
    return out


def to_sound(samples):
    return pygame.mixer.Sound(buffer=array("h", samples).tobytes())


def init_sound():
    global MUSIC_CH
    try:
        pygame.mixer.init(RATE, -16, 1, 512)
    except Exception:
        return False
    try:
        SND["launch"] = to_sound(synth(300, 700, 0.12, 0.25, "square"))
        SND["paddle"] = to_sound(synth(330, 260, 0.08, 0.3, "tri"))
        SND["wall"] = to_sound(synth(200, 160, 0.05, 0.2, "tri"))
        SND["tough"] = to_sound(synth(220, 150, 0.09, 0.3, "square"))
        SND["break1"] = to_sound(synth(700, 1100, 0.10, 0.25, "square"))
        SND["break2"] = to_sound(synth(800, 1250, 0.10, 0.25, "square"))
        SND["meow"] = to_sound(synth(0, 0, 0.45, 0.35, "meow", vib=0.03))
        SND["fish"] = to_sound(seq([(660, 0.06), (880, 0.06), (1100, 0.10)], "square", 0.22))
        SND["lose"] = to_sound(seq([(440, 0.12), (370, 0.12), (294, 0.12), (220, 0.25)], "tri", 0.35))
        SND["over"] = to_sound(seq([(392, 0.2), (330, 0.2), (262, 0.2), (196, 0.5)], "tri", 0.4))
        SND["level"] = to_sound(seq([(523, 0.08), (659, 0.08), (784, 0.08), (1047, 0.2)], "square", 0.22))
        SND["select"] = to_sound(synth(880, 1100, 0.05, 0.2, "square"))
        SND["skill"] = to_sound(seq([(392, 0.05), (523, 0.05), (659, 0.05), (784, 0.05), (1047, 0.14)], "square", 0.25))
        SND["shoot"] = to_sound(synth(1300, 300, 0.14, 0.22, "square"))
        SND["bosshit"] = to_sound(synth(180, 90, 0.12, 0.35, "square"))
        SND["boom"] = to_sound([int(a * 0.5 + b * 0.6) for a, b in zip(
            synth(0, 0, 0.4, 0.4, "noise"), synth(160, 40, 0.4, 0.5, "sine"))])
        SND["boss"] = to_sound(seq([(196, 0.15), (147, 0.15), (110, 0.35)], "tri", 0.4))
        SND["ready"] = to_sound(seq([(988, 0.05), (1319, 0.09)], "square", 0.18))
        SND["warn"] = to_sound(seq([(1000, 0.05), (0, 0.04), (1000, 0.05)], "square", 0.2))
        SND["dive"] = to_sound(synth(900, 150, 0.25, 0.3, "square"))
        SND["upgrade"] = to_sound(seq([(523, 0.07), (659, 0.07), (784, 0.07), (1047, 0.07), (1319, 0.07), (1568, 0.2)], "square", 0.22))
        # gacha
        SND["gacha_tick"] = to_sound(synth(500, 800, 0.04, 0.18, "square"))
        SND["gacha_dup"] = to_sound(seq([(440, 0.06), (330, 0.1)], "tri", 0.3))
        SND["gacha_rare"] = to_sound(seq([(523, 0.07), (659, 0.07), (784, 0.07), (1047, 0.07),
                                          (1319, 0.07), (1568, 0.22)], "square", 0.24))
        SND["gacha_op"] = to_sound(seq([(523, 0.07), (659, 0.07), (784, 0.07), (1047, 0.07),
                                        (784, 0.07), (1047, 0.07), (1319, 0.07), (1568, 0.07),
                                        (2093, 0.35)], "square", 0.24))
        SND["coin"] = to_sound(seq([(988, 0.05), (1319, 0.12)], "square", 0.2))
        melody = [(523, .16), (659, .16), (784, .16), (659, .16),
                  (587, .16), (698, .16), (880, .16), (698, .16),
                  (523, .16), (659, .16), (784, .16), (1047, .16),
                  (988, .16), (784, .16), (659, .16), (0, .16)]
        bass = [(131, .32), (165, .32), (147, .32), (175, .32),
                (131, .32), (165, .32), (196, .32), (131, .32)]
        m = seq(melody, "square", 0.07)
        b = seq(bass, "tri", 0.18)
        n = min(len(m), len(b))
        SND["music"] = to_sound([max(-32767, min(32767, m[i] + b[i])) for i in range(n)])
        MUSIC_CH = pygame.mixer.Channel(0)
        return True
    except Exception:
        return False


def sfx(name):
    if SOUND_OK and name in SND:
        SND[name].play()


def music_update(play, paused=False):
    if not SOUND_OK or MUSIC_CH is None:
        return
    if play and music_on:
        if not MUSIC_CH.get_busy():
            MUSIC_CH.play(SND["music"], loops=-1)
        if paused:
            MUSIC_CH.pause()
        else:
            MUSIC_CH.unpause()
    else:
        MUSIC_CH.stop()


# ---------------------------------------------------------------- Sprite kecil
def mini_cat(surf, x, y, pal):
    """Ikon kepala kucing 7x6 (untuk nyawa)."""
    pygame.draw.rect(surf, pal["body"], (x, y + 2, 7, 4))
    for ex in (x, x + 6):
        surf.set_at((ex, y), pal["ear"])
        surf.set_at((ex, y + 1), pal["ear"])
    surf.set_at((x + 2, y + 3), pal["eye"])
    surf.set_at((x + 4, y + 3), pal["eye"])
    surf.set_at((x + 3, y + 4), PINK)


def draw_fish(surf, x, y, color=FISH_C):
    pygame.draw.ellipse(surf, color, (x, y, 6, 5))
    pygame.draw.polygon(surf, color, [(x + 5, y + 2), (x + 8, y), (x + 8, y + 4)])
    surf.set_at((x + 1, y + 1), DARK)


def draw_coin(surf, x, y):
    pygame.draw.circle(surf, (214, 150, 30), (x, y), 3)
    pygame.draw.circle(surf, YELLOW, (x, y), 2)
    surf.set_at((x - 1, y - 1), WHITE)


def draw_star(surf, cx, cy, r, col):
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    pygame.draw.polygon(surf, col, pts)


def draw_capsule(surf, cx, cy, rad, col):
    """Kapsul gacha berkuping kucing."""
    pygame.draw.polygon(surf, col, [(cx - rad + 1, cy - rad // 2), (cx - rad + 1, cy - rad - 3),
                                    (cx - rad // 3, cy - rad + 1)])
    pygame.draw.polygon(surf, col, [(cx + rad - 2, cy - rad // 2), (cx + rad - 2, cy - rad - 3),
                                    (cx + rad // 3, cy - rad + 1)])
    pygame.draw.circle(surf, WHITE, (cx, cy), rad)
    pygame.draw.circle(surf, col, (cx, cy), rad, 0, True, True, False, False)
    pygame.draw.line(surf, DARK, (cx - rad, cy), (cx + rad - 1, cy))
    pygame.draw.circle(surf, DARK, (cx, cy), rad, 1)
    pygame.draw.circle(surf, WHITE, (cx, cy), max(2, rad // 4))
    pygame.draw.circle(surf, DARK, (cx, cy), max(2, rad // 4), 1)
    surf.set_at((cx - rad // 2, cy - rad // 2), WHITE)
    surf.set_at((cx - rad // 2 + 1, cy - rad // 2), WHITE)


def draw_icon(surf, kind, cx, cy):
    if kind == 0:      # melebar
        pygame.draw.line(surf, YELLOW, (cx - 6, cy), (cx + 6, cy))
        pygame.draw.polygon(surf, YELLOW, [(cx - 8, cy), (cx - 5, cy - 3), (cx - 5, cy + 3)])
        pygame.draw.polygon(surf, YELLOW, [(cx + 8, cy), (cx + 5, cy - 3), (cx + 5, cy + 3)])
    elif kind == 1:    # jam
        pygame.draw.circle(surf, FISH_C, (cx, cy), 6, 1)
        pygame.draw.line(surf, FISH_C, (cx, cy), (cx, cy - 4))
        pygame.draw.line(surf, FISH_C, (cx, cy), (cx + 3, cy))
    elif kind == 2:    # api
        pygame.draw.polygon(surf, (255, 100, 40), [(cx, cy - 7), (cx + 5, cy + 1), (cx + 3, cy + 6),
                                                   (cx - 3, cy + 6), (cx - 5, cy + 1)])
        pygame.draw.polygon(surf, YELLOW, [(cx, cy - 2), (cx + 2, cy + 2), (cx, cy + 5), (cx - 2, cy + 2)])
    elif kind == 4:    # bola kembar
        for dx, dy in ((-4, 3), (4, 3), (0, -4)):
            pygame.draw.circle(surf, YARN, (cx + dx, cy + dy), 3)
            surf.set_at((cx + dx - 1, cy + dy - 1), WHITE)
    elif kind == 5:    # hati
        pygame.draw.circle(surf, PINK, (cx - 3, cy - 2), 3)
        pygame.draw.circle(surf, PINK, (cx + 3, cy - 2), 3)
        pygame.draw.polygon(surf, PINK, [(cx - 6, cy - 1), (cx + 6, cy - 1), (cx, cy + 6)])
    elif kind == 6:    # ledakan
        pts = []
        for k in range(10):
            a = k * math.pi / 5
            r = 7 if k % 2 == 0 else 3
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        pygame.draw.polygon(surf, (255, 160, 60), pts)
        pygame.draw.circle(surf, YELLOW, (cx, cy), 2)
    elif kind == 7:    # ikan
        draw_fish(surf, cx - 4, cy - 2, YELLOW)
    elif kind == 8:    # bintang dewa
        draw_star(surf, cx, cy, 8, YELLOW)
        pygame.draw.circle(surf, WHITE, (cx, cy), 2)
    else:              # tembak
        for dx in (-4, 0, 4):
            pygame.draw.line(surf, PINK, (cx + dx, cy + 5), (cx + dx, cy - 1))
            pygame.draw.polygon(surf, WHITE, [(cx + dx - 1, cy - 1), (cx + dx + 1, cy - 1), (cx + dx, cy - 4)])


def draw_upg_icon(surf, key, cx, cy):
    if key == "speed":
        for i, ln in enumerate((8, 5, 7)):
            pygame.draw.line(surf, WHITE, (cx - 8, cy - 4 + i * 4), (cx - 8 + ln, cy - 4 + i * 4))
        pygame.draw.polygon(surf, YELLOW, [(cx + 8, cy), (cx + 1, cy - 5), (cx + 1, cy + 5)])
    elif key == "width":
        draw_icon(surf, 0, cx, cy)
    elif key == "cd":
        draw_icon(surf, 1, cx, cy)
    elif key == "life":
        draw_icon(surf, 5, cx, cy)
    elif key == "power":
        draw_icon(surf, 6, cx, cy)
    elif key == "magnet":
        pygame.draw.rect(surf, (230, 60, 80), (cx - 6, cy - 6, 4, 9))
        pygame.draw.rect(surf, (230, 60, 80), (cx + 2, cy - 6, 4, 9))
        pygame.draw.rect(surf, (170, 170, 190), (cx - 6, cy + 3, 12, 3))
        pygame.draw.rect(surf, WHITE, (cx - 6, cy - 6, 4, 2))
        pygame.draw.rect(surf, WHITE, (cx + 2, cy - 6, 4, 2))
    elif key == "poison":
        pygame.draw.circle(surf, (120, 230, 100), (cx, cy + 2), 5)
        pygame.draw.polygon(surf, (120, 230, 100), [(cx - 4, cy + 1), (cx + 4, cy + 1), (cx, cy - 7)])
        surf.set_at((cx - 2, cy + 1), WHITE)


# ---------------------------------------------------------------- Paddle (kucing)
class Paddle:
    def __init__(self, pal):
        self.pal = pal
        self.w, self.h = 30, 9
        self.x = LW / 2 - self.w / 2
        self.y = LH - 17
        self.speed = 3.4
        self.base_w = 30
        self.tier = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), self.y, self.w, self.h)

    @property
    def cx(self):
        return self.x + self.w / 2

    def move(self, direction):
        self.x += direction * self.speed
        self.clamp()

    def set_center(self, cx):
        self.x = cx - self.w / 2
        self.clamp()

    def set_width(self, w):
        cx = self.cx
        self.w = int(w)
        self.set_center(cx)

    def clamp(self):
        self.x = max(0, min(LW - self.w, self.x))

    def draw(self, surf, t, glow=False):
        p = self.pal
        x, y, w = int(self.x), self.y, self.w
        cx = x + w // 2
        if glow:
            pygame.draw.rect(surf, shade(p["body"], -40), (x - 1, y + 2, w + 2, 8), 1, border_radius=3)
        if p.get("halo"):    # aura kucing OP
            col = (255, 214, 90) if (t // 8) % 2 else (255, 240, 170)
            pygame.draw.rect(surf, shade(col, -70), (x - 2, y - 1, w + 4, 12), 1, border_radius=4)
        if p.get("wings"):
            fl = int(math.sin(t * 0.2) * 2)
            wc = (255, 255, 242)
            pygame.draw.polygon(surf, wc, [(cx - 8, y + 5), (cx - 15, y - 2 + fl), (cx - 13, y + 2),
                                           (cx - 16, y + 3 + fl), (cx - 9, y + 8)])
            pygame.draw.polygon(surf, wc, [(cx + 7, y + 5), (cx + 14, y - 2 + fl), (cx + 12, y + 2),
                                           (cx + 15, y + 3 + fl), (cx + 8, y + 8)])
        wag = int(math.sin(t * 0.15) * 3)
        pygame.draw.line(surf, p["tail"], (x + w - 3, y + 6), (x + w + 2, y + 1 + wag), 2)
        pygame.draw.rect(surf, p["body"], (x + 1, y + 4, w - 2, 5), border_radius=2)
        pygame.draw.rect(surf, p["dark"], (x + 1, y + 8, w - 2, 1))
        pygame.draw.rect(surf, p["body"], (cx - 7, y + 1, 14, 8), border_radius=2)
        pygame.draw.polygon(surf, p["ear"], [(cx - 7, y + 3), (cx - 7, y - 2), (cx - 3, y + 1)])
        pygame.draw.polygon(surf, p["ear"], [(cx + 6, y + 3), (cx + 6, y - 2), (cx + 2, y + 1)])
        surf.set_at((cx - 6, y), PINK)
        surf.set_at((cx + 5, y), PINK)
        if p["stripes"]:
            for dx in (-2, 0, 2):
                pygame.draw.line(surf, p["dark"], (cx + dx, y + 1), (cx + dx, y + 2))
        if p["mask"]:
            pygame.draw.rect(surf, p["dark"], (cx - 3, y + 5, 6, 4), border_radius=1)
        if (t // 6) % 40 == 0:   # berkedip
            pygame.draw.line(surf, p["dark"], (cx - 4, y + 5), (cx - 2, y + 5))
            pygame.draw.line(surf, p["dark"], (cx + 2, y + 5), (cx + 4, y + 5))
        else:
            pygame.draw.rect(surf, p["eye"], (cx - 4, y + 4, 2, 2))
            pygame.draw.rect(surf, p["eye"], (cx + 2, y + 4, 2, 2))
            surf.set_at((cx - 3, y + 5), DARK)
            surf.set_at((cx + 3, y + 5), DARK)
            surf.set_at((cx - 4, y + 4), WHITE)
            surf.set_at((cx + 2, y + 4), WHITE)
        surf.set_at((cx - 1, y + 6), PINK)
        surf.set_at((cx, y + 6), PINK)
        if not p["mask"]:
            surf.set_at((cx - 1, y + 7), DARK)
            surf.set_at((cx, y + 7), DARK)
        pygame.draw.line(surf, p["whisk"], (cx - 9, y + 6), (cx - 6, y + 6))
        pygame.draw.line(surf, p["whisk"], (cx + 6, y + 6), (cx + 9, y + 6))
        pygame.draw.rect(surf, p["paws"], (x + 4, y + 8, 4, 1))
        pygame.draw.rect(surf, p["paws"], (x + w - 8, y + 8, 4, 1))
        if p.get("halo"):
            pygame.draw.ellipse(surf, YELLOW, (cx - 6, y - 8, 12, 4), 1)
        # kosmetik upgrade
        tr = self.tier
        if tr >= 1:      # kalung & lonceng
            pygame.draw.rect(surf, (230, 60, 80), (cx - 5, y + 8, 10, 1))
            surf.set_at((cx, y + 9), YELLOW)
        if tr >= 3:      # syal merah di badan
            pygame.draw.rect(surf, (230, 60, 80), (x + 3, y + 5, 5, 1))
            pygame.draw.rect(surf, (230, 60, 80), (x + w - 8, y + 5, 5, 1))
        if tr >= 5 and not p.get("halo"):      # mahkota emas
            pygame.draw.polygon(surf, YELLOW, [(cx - 4, y - 1), (cx - 4, y - 4), (cx - 2, y - 2), (cx, y - 5),
                                               (cx + 2, y - 2), (cx + 4, y - 4), (cx + 4, y - 1)])
            surf.set_at((cx, y - 4), (255, 80, 100))
        if tr >= 7 or p.get("halo"):      # kilau
            for k in range(3):
                sx = x + (t * 2 + k * (w // 3)) % w
                sy = y - 3 + int(math.sin(t * 0.2 + k * 2) * 3)
                surf.set_at((sx, sy), WHITE)


# ---------------------------------------------------------------- Brick
class Brick:
    W, H = 14, 6

    def __init__(self, x, y, kind, color):
        self.rect = pygame.Rect(x, y, self.W, self.H)
        self.kind = kind          # 'n' biasa, 't' kucing (2 hit), 'f' ikan
        self.color = color
        self.hp = 2 if kind == "t" else 1

    def hit(self):
        self.hp -= 1
        return self.hp <= 0

    def draw(self, surf):
        r = self.rect
        base = (170, 170, 190) if self.kind == "t" else self.color
        if self.kind == "t" and self.hp == 1:
            base = (130, 130, 150)
        pygame.draw.rect(surf, shade(base, -70), r, border_radius=1)           # bingkai gelap
        pygame.draw.rect(surf, base, (r.x + 1, r.y + 1, r.w - 2, r.h - 2))
        pygame.draw.line(surf, shade(base, 60), (r.x + 1, r.y + 1), (r.right - 3, r.y + 1))
        pygame.draw.line(surf, shade(base, 25), (r.x + 1, r.y + 2), (r.x + 1, r.bottom - 3))
        pygame.draw.line(surf, shade(base, -45), (r.x + 1, r.bottom - 2), (r.right - 2, r.bottom - 2))
        surf.set_at((r.x + 2, r.y + 1), WHITE)       # kilau
        surf.set_at((r.x + 3, r.y + 1), shade(WHITE, -30))
        if self.kind == "t":
            for ex in (r.left + 1, r.right - 3):
                surf.set_at((ex, r.top - 1), base)
                surf.set_at((ex + 1, r.top - 1), base)
            surf.set_at((r.left + 4, r.top + 2), DARK)
            surf.set_at((r.right - 5, r.top + 2), DARK)
            surf.set_at((r.centerx - 1, r.top + 3), PINK)
            if self.hp == 1:
                pygame.draw.line(surf, DARK, (r.left + 6, r.top), (r.left + 8, r.bottom - 1))
        elif self.kind == "f":
            draw_fish(surf, r.left + 3, r.top, WHITE)


# ---------------------------------------------------------------- Ball (bola benang)
class Ball:
    R = 2

    def __init__(self):
        self.x = self.y = 0.0
        self.vx = self.vy = 0.0
        self.stuck = True
        self.pierce = False
        self.trail = []

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.R), int(self.y - self.R), self.R * 2, self.R * 2)

    def draw(self, surf):
        base = (255, 150, 40) if self.pierce else YARN
        for i, (tx, ty) in enumerate(self.trail):
            surf.set_at((int(tx), int(ty)), shade(base, -150 + i * 15))
        pygame.draw.circle(surf, shade(base, -110), (int(self.x), int(self.y)), self.R + 2, 1)
        pygame.draw.circle(surf, base, (int(self.x), int(self.y)), self.R + 1)
        surf.set_at((int(self.x) - 1, int(self.y) - 1), WHITE if not self.pierce else YELLOW)
        surf.set_at((int(self.x) + 1, int(self.y)), shade(base, -70))


# ---------------------------------------------------------------- Boss
class Boss:
    W, H = 40, 18
    NAMES = ["RAJA TIKUS", "ANJING GALAK", "ELANG PERKASA", "GURITA RAKSASA"]
    BASE_SPEED = [0.35, 0.50, 0.45, 0.30]

    def __init__(self, level):
        self.tier = level // 3
        self.kind = (self.tier - 1) % 4
        self.maxhp = 12 + 6 * self.tier
        self.hp = self.maxhp
        self.x = LW / 2 - self.W / 2
        self.y = 34.0
        self.base_y = 34.0
        self.dir = 1
        self.speed = min(self.BASE_SPEED[self.kind] + 0.05 * self.tier, 0.9)
        self.inv = 0
        self.cd = 90
        # khusus Elang
        self.state = "patrol"
        self.timer = 150
        self.target = LW / 2
        self.tx = LW / 2
        self.hit_flag = False

    @property
    def name(self):
        return self.NAMES[self.kind]

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    def draw(self, surf, t):
        flash = self.inv > 0 and (t // 2) % 2 == 0
        (draw_tikus, draw_anjing, draw_elang, draw_gurita)[self.kind](surf, self, t, flash)


def draw_tikus(surf, bs, t, flash):
    x, y, W, H = int(bs.x), int(bs.y), bs.W, bs.H
    cx = x + W // 2
    body = (255, 255, 255) if flash else (150, 150, 172)
    ear = (255, 255, 255) if flash else (135, 135, 158)
    for ex in (x + 4, x + W - 5):
        pygame.draw.circle(surf, ear, (ex, y + 1), 6)
        pygame.draw.circle(surf, PINK, (ex, y + 1), 3)
    pygame.draw.rect(surf, body, (x, y, W, H), border_radius=4)
    pygame.draw.rect(surf, shade(body, -50), (x, y + H - 2, W, 2), border_radius=1)
    pygame.draw.polygon(surf, YELLOW, [(cx - 8, y), (cx - 8, y - 7), (cx - 4, y - 3), (cx, y - 8),
                                       (cx + 4, y - 3), (cx + 8, y - 7), (cx + 8, y)])
    surf.set_at((cx, y - 6), (255, 80, 100))
    for ex in (x + 9, x + W - 14):
        pygame.draw.rect(surf, (230, 40, 60), (ex, y + 5, 5, 4))
        surf.set_at((ex + 1, y + 6), WHITE)
    pygame.draw.line(surf, DARK, (x + 8, y + 3), (x + 15, y + 5))
    pygame.draw.line(surf, DARK, (x + W - 9, y + 3), (x + W - 16, y + 5))
    pygame.draw.rect(surf, PINK, (cx - 2, y + 10, 4, 3))
    pygame.draw.rect(surf, WHITE, (cx - 3, y + 14, 2, 3))
    pygame.draw.rect(surf, WHITE, (cx + 1, y + 14, 2, 3))
    for dy in (-1, 2):
        pygame.draw.line(surf, WHITE, (x + 7, y + 11), (x - 3, y + 11 + dy))
        pygame.draw.line(surf, WHITE, (x + W - 8, y + 11), (x + W + 2, y + 11 + dy))


def draw_anjing(surf, bs, t, flash):
    x, y, W, H = int(bs.x), int(bs.y), bs.W, bs.H
    cx = x + W // 2
    body = (255, 255, 255) if flash else (178, 132, 88)
    ear = (255, 255, 255) if flash else (105, 66, 38)
    pygame.draw.rect(surf, ear, (x - 4, y + 1, 8, 13), border_radius=3)
    pygame.draw.rect(surf, ear, (x + W - 4, y + 1, 8, 13), border_radius=3)
    pygame.draw.rect(surf, body, (x, y, W, H), border_radius=5)
    pygame.draw.rect(surf, (235, 205, 165) if not flash else WHITE, (cx - 9, y + 8, 18, 10), border_radius=3)
    pygame.draw.rect(surf, DARK, (cx - 3, y + 8, 6, 3), border_radius=1)
    pygame.draw.line(surf, DARK, (cx, y + 11), (cx, y + 13))
    pygame.draw.rect(surf, WHITE, (cx - 6, y + 14, 2, 3))
    pygame.draw.rect(surf, WHITE, (cx + 4, y + 14, 2, 3))
    for ex in (x + 7, x + W - 13):
        pygame.draw.rect(surf, WHITE, (ex, y + 4, 6, 4))
        pygame.draw.rect(surf, DARK, (ex + (3 if ex < cx else 1), y + 5, 2, 3))
    pygame.draw.line(surf, DARK, (x + 6, y + 2), (x + 14, y + 5))
    pygame.draw.line(surf, DARK, (x + W - 7, y + 2), (x + W - 15, y + 5))
    pygame.draw.rect(surf, (220, 50, 70), (x + 4, y + H - 1, W - 8, 2))
    for sx in range(x + 6, x + W - 6, 6):
        surf.set_at((sx, y + H + 1), YELLOW)


def draw_elang(surf, bs, t, flash):
    x, y, W, H = int(bs.x), int(bs.y), bs.W, bs.H
    cx = x + W // 2
    wing = (255, 255, 255) if flash else (96, 66, 42)
    body = (255, 255, 255) if flash else (130, 92, 60)
    head = (255, 255, 255) if flash else (242, 238, 230)
    fl = int(math.sin(t * (0.5 if bs.state == "dive" else 0.2)) * 3)
    pygame.draw.polygon(surf, wing, [(x + 4, y + 5), (x - 10, y - 5 + fl), (x - 5, y + 12), (x + 4, y + 14)])
    pygame.draw.polygon(surf, wing, [(x + W - 4, y + 5), (x + W + 10, y - 5 + fl), (x + W + 5, y + 12), (x + W - 4, y + 14)])
    pygame.draw.rect(surf, body, (x + 4, y + 2, W - 8, H - 2), border_radius=5)
    pygame.draw.rect(surf, head, (x + 10, y, W - 20, 10), border_radius=4)
    pygame.draw.polygon(surf, YELLOW, [(cx - 3, y + 7), (cx + 3, y + 7), (cx, y + 14)])
    for ex in (cx - 9, cx + 5):
        pygame.draw.rect(surf, YELLOW, (ex, y + 3, 4, 3))
        surf.set_at((ex + 1, y + 4), DARK)
    pygame.draw.line(surf, DARK, (cx - 10, y + 2), (cx - 4, y + 4))
    pygame.draw.line(surf, DARK, (cx + 9, y + 2), (cx + 3, y + 4))
    for tx in (x + 12, x + W - 14):
        pygame.draw.line(surf, YELLOW, (tx, y + H), (tx, y + H + 2))
    if bs.state == "warn":
        tx = int(bs.target)
        for yy in range(y + H + 4, LH - 8, 5):
            surf.set_at((tx, yy), (255, 90, 110))
        if (t // 4) % 2:
            pygame.draw.rect(surf, (255, 60, 80), (cx - 1, y - 14, 3, 7))
            pygame.draw.rect(surf, (255, 60, 80), (cx - 1, y - 5, 3, 3))


def draw_gurita(surf, bs, t, flash):
    x, y, W, H = int(bs.x), int(bs.y), bs.W, bs.H
    cx = x + W // 2
    body = (255, 255, 255) if flash else (172, 88, 204)
    dark = (255, 255, 255) if flash else (130, 60, 165)
    for i in range(5):
        tx = x + 4 + i * 7
        th = 6 + int(math.sin(t * 0.15 + i) * 2)
        pygame.draw.rect(surf, dark, (tx, y + H - 4, 4, th), border_radius=1)
    pygame.draw.ellipse(surf, body, (x, y - 5, W, H + 4))
    for sx, sy in ((x + 8, y - 1), (x + W - 10, y), (cx, y - 3)):
        surf.set_at((sx, sy), shade(body, 40))
    for ex in (x + 12, x + W - 12):
        pygame.draw.circle(surf, WHITE, (ex, y + 6), 4)
        pygame.draw.circle(surf, DARK, (ex + (1 if ex < cx else -1), y + 7), 2)
    pygame.draw.line(surf, DARK, (x + 7, y + 1), (x + 15, y + 4))
    pygame.draw.line(surf, DARK, (x + W - 8, y + 1), (x + W - 16, y + 4))
    pygame.draw.rect(surf, DARK, (cx - 3, y + 12, 6, 2), border_radius=1)


def draw_cheese(surf, x, y):
    pygame.draw.polygon(surf, YELLOW, [(x, y + 4), (x + 6, y + 4), (x + 6, y + 1), (x, y)])
    surf.set_at((x + 2, y + 2), (210, 160, 40))
    surf.set_at((x + 4, y + 3), (210, 160, 40))


def draw_proj(surf, x, y, kind):
    if kind == "cheese":
        draw_cheese(surf, x, y)
    elif kind == "bone":
        pygame.draw.rect(surf, WHITE, (x + 1, y + 1, 4, 2))
        pygame.draw.rect(surf, WHITE, (x, y, 2, 4))
        pygame.draw.rect(surf, WHITE, (x + 4, y, 2, 4))
    else:  # ink
        pygame.draw.circle(surf, (120, 50, 160), (x + 3, y + 2), 3)
        surf.set_at((x + 2, y + 1), (225, 175, 255))


HIT_MSG = {"cheese": "AUW! KENA KEJU", "bone": "AUW! KENA TULANG",
           "ink": "AUW! KENA TINTA", "dive": "AUW! KENA CAKAR"}

# ---------------------------------------------------------------- Upgrade kucing
UPGRADES = {
    "speed": dict(title=["GESIT"], desc=["Kucing lari", "lebih cepat 20%"]),
    "width": dict(title=["BADAN", "PANJANG"], desc=["Badan kucing", "lebih lebar +4"]),
    "cd": dict(title=["COOLDOWN", "CEPAT"], desc=["Skill siap 15%", "lebih cepat"]),
    "life": dict(title=["HATI", "CADANGAN"], desc=["+1 nyawa", "(penuh: +100", "skor)"]),
    "power": dict(title=["SKILL", "PERKASA"], desc=["Skill makin", "kuat dan lama"]),
    "magnet": dict(title=["MAGNET", "IKAN"], desc=["Ikan tertarik", "ke arah kucing"]),
    "poison": dict(title=["CAKAR", "RACUN"], desc=["Bola kena boss", "+1 damage"]),
}
UPG_MAX = 3
UPG_CW, UPG_CH, UPG_Y = 60, 82, 32


def upg_rect(i, n):
    total = n * UPG_CW + (n - 1) * 4
    return pygame.Rect((LW - total) // 2 + i * (UPG_CW + 4), UPG_Y, UPG_CW, UPG_CH)


# ---------------------------------------------------------------- Layout menu
CARD_COLS, CARD_W, CARD_H, CARD_X0, CARD_Y0, CARD_GX, CARD_GY = 5, 36, 38, 6, 19, 38, 41
GBTN = [pygame.Rect(10, 108, 56, 24), pygame.Rect(72, 108, 56, 24), pygame.Rect(134, 108, 56, 24)]
PAUSE_ITEMS = 3


def card_rect(i):
    return pygame.Rect(CARD_X0 + (i % CARD_COLS) * CARD_GX, CARD_Y0 + (i // CARD_COLS) * CARD_GY,
                       CARD_W, CARD_H)


def pmenu_rect(i):
    return pygame.Rect(54, 60 + i * 16, 92, 13)


# ---------------------------------------------------------------- Game
class Game:
    def __init__(self):
        self.state = "title"       # title | select | gacha | play | pause | upgrade | over
        self.hi = SAVE["hi"]
        self.t = 0
        self.char = SAVE["char"]
        self.sel = self.char
        self.stars = [(random.randrange(LW), random.randrange(LH), random.choice((0, 0, 1, 2)))
                      for _ in range(46)]
        self.shake = 0
        self.fade = FADE_T
        self.msg = ""
        self.msg_t = 0
        self.pmenu = 0
        # gacha
        self.gstate = "idle"       # idle | open | reveal
        self.gtimer = 0
        self.gsel = 0
        self.gres = []
        self.gidx = 0
        self.gbest = "C"
        self.gmsg = ""
        self.gmsg_t = 0
        self.reset()

    @property
    def cat(self):
        return CATS[self.char]

    @property
    def op(self):
        return bool(self.cat.get("op"))

    @property
    def max_lives(self):
        return 5 + (2 if self.op else 0)

    @property
    def shield_on(self):
        return self.skill_active > 0 and (self.char == 5 or self.op)

    def set_state(self, s, fade=True):
        self.state = s
        if fade:
            self.fade = FADE_T

    def reset(self):
        self.score = 0
        self.lives = 3 + (2 if self.op else 0)
        self.level = 1
        self.paddle = Paddle(self.cat["pal"])
        self.particles = []
        self.fishes = []
        self.floaters = []
        self.shots = []
        self.rings = []
        self.projs = []
        self.skill_cd = 0
        self.skill_active = 0
        self.skill_cd_max = 1
        self.skill_dur_max = 1
        self.up = {k: 0 for k in UPGRADES}
        self.cat_level = 1
        self.upgrade_delay = 0
        self.upg_choices = []
        self.upg_sel = 0
        self.run_coins = 0
        self.over_bonus = 0
        self.refresh_stats()
        self.build_level()

    def refresh_stats(self):
        p = self.paddle
        spd = 3.4 * (1 + 0.2 * self.up["speed"])
        p.speed = spd * (1.2 if self.op else 1.0)
        p.base_w = 30 + 4 * self.up["width"] + (10 if self.op else 0)
        mult = 1.0
        if self.skill_active > 0:
            if self.char == 0:
                mult = 2.0
            elif self.op:
                mult = 1.5
        p.set_width(p.base_w * mult)
        p.tier = self.cat_level - 1

    def gain_coins(self, n):
        SAVE["coins"] += n
        self.run_coins += n

    def build_level(self):
        self.bricks = []
        self.balls = [Ball()]
        self.shots.clear()
        self.projs.clear()
        self.boss = Boss(self.level) if self.level % 3 == 0 else None
        if self.boss:
            rows, top = 3, 58
            sfx("boss")
        else:
            rows, top = min(5 + self.level // 2, 7), 25
        cols = 12
        gap = 2
        total_w = cols * Brick.W + (cols - 1) * gap
        ox = (LW - total_w) // 2
        for r in range(rows):
            for c in range(cols):
                if self.level > 1 and (r + c) % (6 - min(self.level, 4)) == 0 and random.random() < 0.5:
                    continue
                roll = random.random()
                kind = "t" if roll < 0.15 else ("f" if roll < 0.23 else "n")
                self.bricks.append(Brick(ox + c * (Brick.W + gap), top + r * (Brick.H + gap),
                                         kind, ROW_COLORS[(r + (3 if self.boss else 0)) % len(ROW_COLORS)]))
        self.speed = min(1.9 + 0.15 * (self.level - 1), 3.2)

    def burst(self, x, y, color, n=8):
        for _ in range(n):
            a = random.random() * math.tau
            s = random.uniform(0.3, 1.4)
            self.particles.append([x, y, math.cos(a) * s, math.sin(a) * s - 0.3,
                                   random.randint(15, 30), color])

    def floater(self, s, x, y, color=WHITE):
        self.floaters.append([s, x, y, 50, color])

    # --- nyawa
    def lose_life(self, reset_ball):
        self.lives -= 1
        self.shake = 10
        p = self.paddle
        self.burst(p.cx, p.y, YARN, 12)
        if self.lives <= 0:
            self.hi = max(self.hi, self.score)
            SAVE["hi"] = self.hi
            self.over_bonus = self.score // 40
            self.gain_coins(self.over_bonus)
            save_game()
            self.set_state("over", fade=False)
            music_update(False)
            sfx("over")
            return
        sfx("lose")
        if reset_ball:
            self.balls = [Ball()]

    # --- pause
    def pause(self):
        if self.state != "play":
            return
        self.pmenu = 0
        self.set_state("pause", fade=False)
        music_update(True, True)
        sfx("select")

    def resume(self):
        if self.state != "pause":
            return
        self.set_state("play", fade=False)
        music_update(True, False)
        sfx("select")

    def go_menu(self):
        self.hi = max(self.hi, self.score)
        SAVE["hi"] = self.hi
        save_game()
        music_update(False)
        self.set_state("select")
        self.sel = self.char

    def pmenu_do(self, i):
        global music_on
        if i == 0:
            self.resume()
        elif i == 1:
            music_on = not music_on
            music_update(True, True)
            sfx("select")
        else:
            self.go_menu()

    # --- skill
    def use_skill(self):
        if self.state != "play" or self.skill_cd > 0:
            return
        c = self.cat
        p = self.paddle
        src = self.balls[0]
        if c.get("needs_ball") and src.stuck:
            self.floater("LUNCURKAN BOLA DULU!", -1, p.y - 22, PINK)
            return
        pw = self.up["power"]
        self.skill_cd_max = max(120, int(c["cd"] * (1 - 0.15 * self.up["cd"])))
        self.skill_cd = self.skill_cd_max
        if c["dur"] > 0:
            self.skill_dur_max = int(c["dur"] * (1 + 0.25 * pw))
            self.skill_active = self.skill_dur_max
        else:
            self.skill_active = 0
        sfx("skill")
        self.floater(c["skill"].upper() + "!", -1, p.y - 24, YELLOW)
        self.burst(p.cx, p.y, YELLOW, 14)
        if self.char == 0:
            self.refresh_stats()
        elif self.char == 3:
            sfx("shoot")
            n = 3 + 2 * pw
            for i in range(n):
                self.shots.append([p.cx + (i - (n - 1) / 2) * 8, float(p.y)])
        elif self.char == 4:
            for k in range(2 + pw):
                if len(self.balls) >= 8:
                    break
                nb = Ball()
                nb.stuck = False
                ang = math.atan2(src.vy, src.vx) + 0.45 * (k // 2 + 1) * (1 if k % 2 == 0 else -1)
                sp = math.hypot(src.vx, src.vy)
                nb.vx, nb.vy = math.cos(ang) * sp, math.sin(ang) * sp
                nb.x, nb.y = src.x, src.y
                self.balls.append(nb)
        elif self.char == 6:
            self.explode(src.x, src.y, 28 + 6 * pw, 3 + pw)
        elif self.char == 7:
            for _ in range(6 + 2 * pw):
                self.fishes.append([random.uniform(8, LW - 16), -random.uniform(0, 45), "rain"])
        elif self.op:        # Murka Dewa
            self.refresh_stats()
            sfx("shoot")
            self.shake = 8
            self.rings.append([p.cx, p.y, 4.0, 16])
            for i in range(7):
                self.shots.append([p.cx + (i - 3) * 7, float(p.y)])

    def explode(self, x, y, radius, boss_dmg):
        sfx("boom")
        self.shake = 6
        self.rings.append([x, y, 4.0, 14])
        for br in self.bricks[:]:
            if math.hypot(br.rect.centerx - x, br.rect.centery - y) <= radius:
                br.hp = 1
                self.hit_brick(br)
        if self.boss and math.hypot(self.boss.rect.centerx - x, self.boss.rect.centery - y) <= radius + 14:
            self.boss_hit(boss_dmg)
        self.burst(x, y, (255, 160, 60), 20)

    def update_skill(self):
        if self.skill_active > 0:
            self.skill_active -= 1
            if self.op and self.skill_active % 14 == 0 and self.skill_active > 0:
                p = self.paddle
                for dx in (-8, 8):
                    self.shots.append([p.cx + dx, float(p.y)])
            if self.skill_active == 0 and (self.char == 0 or self.op):
                self.refresh_stats()
        if self.skill_cd > 0:
            self.skill_cd -= 1
            if self.skill_cd == 0:
                sfx("ready")
        pierce = self.skill_active > 0 and (self.char == 2 or self.op)
        for b in self.balls:
            b.pierce = pierce

        for s in self.shots[:]:
            s[1] -= 4
            hit = None
            for br in self.bricks:
                if br.rect.collidepoint(int(s[0]), int(s[1])):
                    hit = br
                    break
            if hit:
                self.shots.remove(s)
                if self.op:
                    hit.hp = 1
                self.hit_brick(hit)
            elif self.boss and self.boss.rect.collidepoint(int(s[0]), int(s[1])):
                self.shots.remove(s)
                self.boss_hit(2 if self.op else 1)
            elif s[1] < 0:
                self.shots.remove(s)

    # --- upgrade
    def open_upgrade(self):
        pool = [k for k in UPGRADES if k == "life" or self.up[k] < UPG_MAX]
        self.upg_choices = random.sample(pool, min(3, len(pool)))
        self.upg_sel = 0
        self.set_state("upgrade")
        sfx("upgrade")

    def apply_upgrade(self, i):
        if not (0 <= i < len(self.upg_choices)):
            return
        key = self.upg_choices[i]
        if key == "life":
            if self.lives < self.max_lives:
                self.lives += 1
            else:
                self.score += 100
        else:
            self.up[key] += 1
        self.cat_level += 1
        self.refresh_stats()
        self.set_state("play")
        sfx("meow")
        self.floater("KUCING LV %d!" % self.cat_level, -1, self.paddle.y - 24, YELLOW)
        self.burst(self.paddle.cx, self.paddle.y, YELLOW, 24)

    # --- gacha
    def open_gacha(self):
        self.set_state("gacha")
        self.gstate = "idle"
        self.gsel = 0
        self.gmsg_t = 0
        self.particles.clear()
        music_update(False)
        sfx("select")

    def start_pull(self, n):
        cost = GACHA_COST1 if n == 1 else GACHA_COST10
        if SAVE["coins"] < cost:
            self.gmsg = "KOIN KURANG! Main dulu ya"
            self.gmsg_t = 100
            sfx("lose")
            return
        SAVE["coins"] -= cost
        SAVE["pulls"] += n
        res = []
        for i in range(n):
            min_r = "R" if (n == 10 and i == 9 and all(x["r"] == "C" for x in res)) else None
            r = roll_rarity(min_r)
            pool = [k for k, c in enumerate(CATS) if c["rarity"] == r]
            idx = random.choice(pool)
            new = idx not in SAVE["owned"]
            refund = 0
            if new:
                SAVE["owned"] = sorted(SAVE["owned"] + [idx])
            else:
                refund = RARITY[r]["refund"]
                SAVE["coins"] += refund
            res.append(dict(idx=idx, r=r, new=new, refund=refund))
        save_game()
        order = "CREO"
        self.gres = res
        self.gidx = 0
        self.gbest = max((x["r"] for x in res), key=order.index)
        self.gstate = "open"
        self.gtimer = 80
        sfx("gacha_tick")

    def reveal_start(self):
        self.gstate = "reveal"
        self.gtimer = 0
        r = self.gres[self.gidx]["r"]
        col = RARITY[r]["col"]
        self.burst(100, 52, col, 18 if r in ("C", "R") else 36)
        self.burst(100, 52, WHITE, 8)
        sfx({"C": "gacha_dup", "R": "level", "E": "gacha_rare", "O": "gacha_op"}[r])
        if r == "O":
            self.shake = 16
        if r in ("E", "O"):
            sfx("meow")

    def action_gacha(self):
        if self.gstate == "idle":
            if self.gsel == 0:
                self.start_pull(1)
            elif self.gsel == 1:
                self.start_pull(10)
            else:
                self.set_state("select")
                self.sel = GACHA_SLOT
        elif self.gstate == "open":
            self.gtimer = 0
        else:
            self.gidx += 1
            if self.gidx >= len(self.gres):
                self.gstate = "idle"
                sfx("select")
            else:
                self.reveal_start()

    def gbtn_at(self, pos):
        px, py = pos[0] / SCALE, pos[1] / SCALE
        for i, r in enumerate(GBTN):
            if r.collidepoint(px, py):
                return i
        return None

    # --- input
    def launch(self):
        b = self.balls[0]
        if b.stuck:
            b.stuck = False
            vx = random.uniform(-0.6, 0.6) * self.speed
            b.vx = vx
            b.vy = -math.sqrt(self.speed ** 2 - vx ** 2)
            sfx("launch")

    def card_at(self, pos):
        px, py = pos[0] / SCALE, pos[1] / SCALE
        for i in range(N_SLOTS):
            if card_rect(i).collidepoint(px, py):
                return i
        return None

    def upg_at(self, pos):
        px, py = pos[0] / SCALE, pos[1] / SCALE
        n = len(self.upg_choices)
        for i in range(n):
            if upg_rect(i, n).collidepoint(px, py):
                return i
        return None

    def pmenu_at(self, pos):
        px, py = pos[0] / SCALE, pos[1] / SCALE
        for i in range(PAUSE_ITEMS):
            if pmenu_rect(i).collidepoint(px, py):
                return i
        return None

    def on_escape(self):
        st = self.state
        if st == "title":
            save_game()
            return False
        if st == "play":
            self.pause()
        elif st == "pause":
            self.resume()
        elif st == "select":
            self.set_state("title")
        elif st == "gacha":
            if self.gstate == "idle":
                self.set_state("select")
                self.sel = GACHA_SLOT
            else:
                self.gstate = "idle"
        elif st == "over":
            self.set_state("title")
        return True

    def handle_event(self, e):
        global music_on, crt_on
        if e.type == pygame.QUIT:
            save_game()
            return False
        if FOCUS_LOST is not None and e.type == FOCUS_LOST and self.state == "play":
            self.pause()
        if e.type == pygame.KEYDOWN:
            k = e.key
            if k == pygame.K_ESCAPE:
                return self.on_escape()
            if k == pygame.K_p:
                if self.state == "play":
                    self.pause()
                elif self.state == "pause":
                    self.resume()
            elif k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.action()
            elif k in (pygame.K_e, pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.use_skill()
            if k == pygame.K_m:
                music_on = not music_on
                music_update(self.state in ("play", "upgrade", "pause"), self.state == "pause")
            if k == pygame.K_v:
                crt_on = not crt_on
            if k == pygame.K_g and self.state in ("title", "select", "over"):
                self.open_gacha()
            left = k in (pygame.K_LEFT, pygame.K_a)
            right = k in (pygame.K_RIGHT, pygame.K_d)
            up = k in (pygame.K_UP, pygame.K_w)
            down = k in (pygame.K_DOWN, pygame.K_s)
            if self.state == "select":
                if left:
                    self.sel = (self.sel - 1) % N_SLOTS
                    sfx("select")
                if right:
                    self.sel = (self.sel + 1) % N_SLOTS
                    sfx("select")
                if up or down:
                    self.sel = (self.sel + CARD_COLS) % N_SLOTS
                    sfx("select")
            elif self.state == "pause":
                if up:
                    self.pmenu = (self.pmenu - 1) % PAUSE_ITEMS
                    sfx("select")
                if down:
                    self.pmenu = (self.pmenu + 1) % PAUSE_ITEMS
                    sfx("select")
            elif self.state == "gacha" and self.gstate == "idle":
                if left:
                    self.gsel = (self.gsel - 1) % 3
                    sfx("select")
                if right:
                    self.gsel = (self.gsel + 1) % 3
                    sfx("select")
                if k == pygame.K_1:
                    self.start_pull(1)
                if k == pygame.K_2:
                    self.start_pull(10)
            elif self.state == "upgrade":
                n = len(self.upg_choices)
                if left:
                    self.upg_sel = (self.upg_sel - 1) % n
                    sfx("select")
                if right:
                    self.upg_sel = (self.upg_sel + 1) % n
                    sfx("select")
                for j, kc in enumerate((pygame.K_1, pygame.K_2, pygame.K_3)):
                    if k == kc:
                        self.apply_upgrade(j)
            elif self.state == "over":
                if k == pygame.K_c:
                    self.set_state("select")
                    self.sel = self.char
                    sfx("select")
        if e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 1:
                if self.state == "select":
                    i = self.card_at(e.pos)
                    if i is not None:
                        self.sel = i
                        self.action()
                elif self.state == "upgrade":
                    i = self.upg_at(e.pos)
                    if i is not None:
                        self.apply_upgrade(i)
                elif self.state == "pause":
                    i = self.pmenu_at(e.pos)
                    if i is not None:
                        self.pmenu_do(i)
                elif self.state == "gacha":
                    if self.gstate == "idle":
                        i = self.gbtn_at(e.pos)
                        if i is not None:
                            self.gsel = i
                            self.action_gacha()
                    else:
                        self.action_gacha()
                else:
                    self.action()
            elif e.button == 3:
                self.use_skill()
        if e.type == pygame.MOUSEMOTION:
            if self.state == "play":
                self.paddle.set_center(e.pos[0] / SCALE)
            elif self.state == "select":
                i = self.card_at(e.pos)
                if i is not None and i != self.sel:
                    self.sel = i
                    sfx("select")
            elif self.state == "upgrade":
                i = self.upg_at(e.pos)
                if i is not None and i != self.upg_sel:
                    self.upg_sel = i
                    sfx("select")
            elif self.state == "pause":
                i = self.pmenu_at(e.pos)
                if i is not None and i != self.pmenu:
                    self.pmenu = i
                    sfx("select")
            elif self.state == "gacha" and self.gstate == "idle":
                i = self.gbtn_at(e.pos)
                if i is not None and i != self.gsel:
                    self.gsel = i
                    sfx("select")
        return True

    def action(self):
        if self.state == "title":
            self.set_state("select")
            self.sel = self.char
            sfx("select")
        elif self.state == "select":
            if self.sel == GACHA_SLOT:
                self.open_gacha()
            elif self.sel in SAVE["owned"]:
                self.char = self.sel
                SAVE["char"] = self.char
                self.reset()
                self.set_state("play")
                sfx("meow")
                music_update(True)
            else:
                self.msg = "TERKUNCI! Buka lewat GACHA"
                self.msg_t = 100
                sfx("lose")
        elif self.state == "play":
            self.launch()
        elif self.state == "pause":
            self.pmenu_do(self.pmenu)
        elif self.state == "upgrade":
            self.apply_upgrade(self.upg_sel)
        elif self.state == "gacha":
            self.action_gacha()
        elif self.state == "over":
            self.reset()
            self.set_state("play")
            music_update(True)

    # --- update
    def update_fx(self):
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.05
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]
        for f in self.floaters:
            f[2] -= 0.3
            f[3] -= 1
        self.floaters = [f for f in self.floaters if f[3] > 0]
        for r in self.rings:
            r[2] += 2.0
            r[3] -= 1
        self.rings = [r for r in self.rings if r[3] > 0]

    def update_gacha(self):
        self.update_fx()
        if self.gmsg_t > 0:
            self.gmsg_t -= 1
        if self.gstate == "open":
            self.gtimer -= 1
            if self.gtimer > 0 and self.gtimer % 10 == 0:
                sfx("gacha_tick")
            if self.t % 2 == 0:
                a = random.random() * math.tau
                self.particles.append([100 + math.cos(a) * 20, 58 + math.sin(a) * 20,
                                       -math.cos(a) * 0.5, -math.sin(a) * 0.5, 14,
                                       RARITY[self.gbest]["col"]])
            if self.gtimer <= 0:
                self.reveal_start()
        elif self.gstate == "reveal":
            self.gtimer += 1
            r = self.gres[self.gidx]["r"]
            if r in ("E", "O") and self.t % 3 == 0:
                self.burst(100 + random.randint(-30, 30), 52 + random.randint(-14, 14),
                           RARITY[r]["col"], 2)

    def update(self):
        self.t += 1
        if self.shake > 0:
            self.shake -= 1
        if self.fade > 0:
            self.fade -= 1
        if self.msg_t > 0:
            self.msg_t -= 1
        if self.state == "gacha":
            self.update_gacha()
            return
        if self.state != "play":
            return

        keys = pygame.key.get_pressed()
        d = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        if d:
            self.paddle.move(d)

        self.update_skill()
        self.update_balls()
        if self.state != "play":
            return
        self.update_fishes()
        self.update_boss()
        if self.state != "play":
            return

        self.update_fx()

        if self.upgrade_delay > 0:
            self.upgrade_delay -= 1
            if self.upgrade_delay == 0:
                self.open_upgrade()
                return

        if not self.bricks and not self.boss and self.upgrade_delay == 0:
            self.level += 1
            sfx("level")
            self.gain_coins(10)
            self.fishes.clear()
            self.build_level()
            if self.boss:
                self.floater("BOSS: %s!" % self.boss.name, -1, LH // 2 - 6, (255, 110, 130))
            else:
                self.floater("LEVEL %d" % self.level, -1, LH // 2 - 6, YELLOW)

    def update_balls(self):
        b0 = self.balls[0]
        p = self.paddle
        if b0.stuck:
            b0.x = p.cx
            b0.y = p.y - b0.R - 2
            b0.trail.clear()
            return
        if self.char == 1 and self.skill_active > 0:
            m = 0.5
        elif self.op and self.skill_active > 0:
            m = 0.8
        else:
            m = 1.0
        for b in self.balls[:]:
            if self.step_ball(b, m):
                self.balls.remove(b)
        if not self.balls:
            self.lose_life(True)

    def step_ball(self, b, m):
        p = self.paddle
        dx, dy = b.vx * m, b.vy * m
        b.trail.append((b.x, b.y))
        b.trail = b.trail[-8:]

        b.x += dx
        if b.x - b.R < 0:
            b.x = b.R
            b.vx = abs(b.vx)
            sfx("wall")
        elif b.x + b.R > LW:
            b.x = LW - b.R
            b.vx = -abs(b.vx)
            sfx("wall")
        self.ball_vs_bricks(b, "x", dx)

        b.y += dy
        if b.y - b.R < 0:
            b.y = b.R
            b.vy = abs(b.vy)
            sfx("wall")
        self.ball_vs_bricks(b, "y", dy)

        if b.vy > 0 and p.rect.colliderect(b.rect):
            off = (b.x - p.cx) / (p.w / 2)
            off = max(-1, min(1, off))
            ang = off * math.radians(65)
            b.vx = self.speed * math.sin(ang)
            b.vy = -self.speed * math.cos(ang)
            b.y = p.y - b.R - 1
            sfx("paddle")

        if self.shield_on and b.vy > 0 and b.y + b.R >= LH - 3:
            b.vy = -abs(b.vy)
            b.y = LH - 3 - b.R
            sfx("paddle")

        return b.y - b.R > LH

    def ball_vs_bricks(self, b, axis, step):
        dmg = 1 + self.up["poison"] + (1 if self.op else 0)
        if b.pierce:
            for br in self.bricks[:]:
                if br.rect.colliderect(b.rect):
                    br.hp = 1
                    self.hit_brick(br)
            if self.boss and self.boss.rect.colliderect(b.rect):
                self.boss_hit(dmg)
            return
        for br in self.bricks:
            if br.rect.colliderect(b.rect):
                self.bounce(b, axis, step)
                self.hit_brick(br)
                return
        if self.boss and self.boss.rect.colliderect(b.rect):
            self.bounce(b, axis, step)
            self.boss_hit(dmg)

    @staticmethod
    def bounce(b, axis, step):
        if axis == "x":
            b.x -= step
            b.vx = -b.vx
        else:
            b.y -= step
            b.vy = -b.vy

    def hit_brick(self, br):
        if br not in self.bricks:
            return
        if br.hit():
            self.bricks.remove(br)
            self.score += 10 if br.kind == "t" else 5
            self.burst(br.rect.centerx, br.rect.centery,
                       br.color if br.kind != "t" else (170, 170, 190))
            sfx(random.choice(["break1", "break2"]))
            if br.kind == "f":
                self.fishes.append([br.rect.left + 3.0, float(br.rect.top), "life"])
        else:
            self.burst(br.rect.centerx, br.rect.centery, WHITE, 3)
            self.score += 1
            sfx("tough")

    # --- boss
    def boss_hit(self, dmg):
        bs = self.boss
        if not bs or bs.inv > 0:
            return
        bs.hp -= dmg
        bs.inv = 8
        self.score += 2
        sfx("bosshit")
        self.burst(bs.rect.centerx, bs.rect.centery, (255, 120, 120), 6)
        if bs.hp <= 0:
            self.kill_boss()

    def kill_boss(self):
        bs = self.boss
        bonus = 150 + 50 * bs.tier
        self.score += bonus
        coins = 40 + 10 * bs.tier
        self.gain_coins(coins)
        cx, cy = bs.rect.center
        for col in ((255, 120, 120), YELLOW, WHITE, (150, 150, 172)):
            self.burst(cx, cy, col, 14)
        self.rings.append([cx, cy, 4.0, 18])
        self.shake = 16
        sfx("boom")
        self.floater("BOSS KALAH!  +%d" % bonus, -1, 70, YELLOW)
        self.floater("+%d KOIN" % coins, -1, 82, YELLOW)
        for dx in (-22, 0, 22):
            self.fishes.append([cx + dx - 4.0, float(cy), "life"])
        self.boss = None
        self.projs.clear()
        self.upgrade_delay = 70

    def update_boss(self):
        bs = self.boss
        if not bs:
            return
        pr = self.paddle.rect
        if bs.inv > 0:
            bs.inv -= 1
        if bs.kind == 2:
            self.update_elang(bs, pr)
            if self.state != "play":
                return
        else:
            self.boss_patrol(bs)
            bs.cd -= 1
            if bs.cd <= 0:
                self.boss_attack(bs, pr)
        for c in self.projs[:]:
            c[0] += c[2]
            c[1] += c[3]
            if pygame.Rect(int(c[0]), int(c[1]), 6, 5).colliderect(pr):
                self.projs.remove(c)
                self.floater(HIT_MSG[c[4]], -1, pr.top - 14, (255, 110, 130))
                self.lose_life(False)
                if self.state != "play":
                    return
            elif c[1] > LH or c[0] < -8 or c[0] > LW + 8:
                self.projs.remove(c)

    @staticmethod
    def boss_patrol(bs):
        bs.x += bs.dir * bs.speed
        if bs.x <= 4:
            bs.dir = 1
        elif bs.x + bs.W >= LW - 4:
            bs.dir = -1

    def boss_attack(self, bs, pr):
        r = bs.rect
        cx, by = r.centerx, r.bottom
        half = bs.hp < bs.maxhp / 2
        tier = bs.tier
        if bs.kind == 0:       # Tikus: jatuhkan keju
            vy = 1.0 + 0.05 * tier
            self.projs.append([cx + random.randint(-8, 8) - 3.0, float(by), 0.0, vy, "cheese"])
            if half:
                self.projs.append([cx + random.choice([-16, 16]) - 3.0, float(by), 0.0, vy, "cheese"])
            bs.cd = max(45, random.randint(70, 110) - tier * 5)
        elif bs.kind == 1:     # Anjing: tembak tulang menyebar
            n = 5 if half else 3
            for i in range(n):
                self.projs.append([cx - 3.0, float(by), (i - (n - 1) / 2) * 0.5, 1.1, "bone"])
            sfx("wall")
            bs.cd = max(60, random.randint(95, 135) - tier * 5)
        else:                  # Gurita: tinta mengincar kucing
            base = math.atan2(pr.centery - by, pr.centerx - cx)
            sp = 1.3 + 0.05 * tier
            for off in ((-0.3, 0, 0.3) if half else (0,)):
                a = base + off
                self.projs.append([cx - 3.0, float(by), math.cos(a) * sp, math.sin(a) * sp, "ink"])
            sfx("wall")
            bs.cd = max(45, random.randint(75, 115) - tier * 5)

    def update_elang(self, bs, pr):
        if bs.state == "patrol":
            self.boss_patrol(bs)
            bs.timer -= 1
            if bs.timer <= 0:
                bs.state, bs.timer = "warn", 45
                sfx("warn")
        elif bs.state == "warn":
            bs.target = pr.centerx
            bs.timer -= 1
            if bs.timer <= 0:
                bs.state = "dive"
                bs.hit_flag = False
                bs.tx = bs.target - bs.W / 2
                sfx("dive")
        elif bs.state == "dive":
            bs.x += max(-2.2, min(2.2, bs.tx - bs.x))
            bs.y += 3.2
            if not bs.hit_flag and bs.rect.colliderect(pr):
                bs.hit_flag = True
                self.floater(HIT_MSG["dive"], -1, pr.top - 14, (255, 110, 130))
                self.lose_life(False)
                if self.state != "play":
                    return
            if bs.y >= 128:
                bs.y = 128.0
                bs.state = "rise"
        elif bs.state == "rise":
            bs.y -= 1.8
            if bs.y <= bs.base_y:
                bs.y = bs.base_y
                bs.state = "patrol"
                bs.timer = max(70, random.randint(120, 190) - bs.tier * 8)
        bs.x = max(4, min(LW - bs.W - 4, bs.x))

    def update_fishes(self):
        pr = self.paddle.rect
        mg = self.up["magnet"] + (1 if self.op else 0)
        for f in self.fishes[:]:
            f[1] += 0.7
            if mg and f[1] > 20:
                f[0] += max(-0.6 * mg, min(0.6 * mg, (pr.centerx - 4 - f[0]) * 0.05))
            fr = pygame.Rect(int(f[0]), int(f[1]), 8, 5)
            if fr.colliderect(pr):
                self.fishes.remove(f)
                sfx("fish")
                if f[2] == "rain":
                    self.score += 25
                    self.gain_coins(1)
                    self.burst(fr.centerx, fr.centery, YELLOW, 4)
                    continue
                sfx("meow")
                self.gain_coins(2)
                if self.lives < self.max_lives:
                    self.lives += 1
                    self.floater("MEOW! +1 NYAWA", -1, pr.top - 14, FISH_C)
                else:
                    self.score += 50
                    self.floater("MEOW! +50", -1, pr.top - 14, FISH_C)

    # --- gambar
    def theme(self):
        if self.state in ("title", "select", "upgrade"):
            return 0
        if self.state == "gacha":
            return 1
        if self.boss:
            return 2
        return (0, 1, 3)[(self.level - 1) % 3]

    def draw_bg(self):
        c = canvas
        c.blit(get_bg(self.theme()), (0, 0))
        cols = ((90, 80, 130), (135, 125, 185), (215, 205, 250))
        for sx, sy, ly in self.stars:
            y = int(sy + self.t * (0.05, 0.12, 0.22)[ly]) % LH
            if ly == 0 or int(self.t / 20 + sx) % 3:
                c.set_at((sx, y), cols[ly])
                if ly == 2 and int(self.t / 15 + sx) % 4 == 0:
                    c.set_at((sx + 1, y), cols[1])
                    c.set_at((sx - 1, y), cols[1])
                    c.set_at((sx, y + 1), cols[1])
                    c.set_at((sx, y - 1), cols[1])
        ph = self.t % 420          # bintang jatuh
        if ph < 24:
            rnd = random.Random(self.t // 420)
            x0, y0 = rnd.randint(70, 190), rnd.randint(4, 40)
            for k in range(7):
                px = x0 - (ph - k) * 4
                py = y0 + (ph - k) * 2
                c.set_at((px, py), shade(WHITE, -k * 28))

    def draw_fx(self):
        c = canvas
        for p in self.particles:
            if p[4] > 18:
                pygame.draw.rect(c, p[5], (int(p[0]), int(p[1]), 2, 2))
            else:
                c.set_at((int(p[0]), int(p[1])), p[5])
        for r in self.rings:
            pygame.draw.circle(c, YELLOW if r[3] % 2 else (255, 160, 60), (int(r[0]), int(r[1])), int(r[2]), 1)

    def draw(self):
        self.draw_bg()
        st = self.state
        if st == "title":
            self.draw_title()
        elif st == "select":
            self.draw_select()
        elif st == "gacha":
            self.draw_gacha()
        elif st == "upgrade":
            self.draw_upgrade()
        else:
            self.draw_world()

    def draw_world(self):
        c = canvas
        for br in self.bricks:
            br.draw(c)
        if self.boss:
            self.boss.draw(c, self.t)
        for f in self.fishes:
            draw_fish(c, int(f[0]), int(f[1]), YELLOW)
        for px, py, _, _, kind in self.projs:
            draw_proj(c, int(px), int(py), kind)
        scol = YELLOW if self.op else WHITE
        for sx, sy in self.shots:
            pygame.draw.line(c, scol, (int(sx), int(sy)), (int(sx), int(sy) + 3))
            c.set_at((int(sx), int(sy)), PINK if not self.op else WHITE)
        self.draw_fx()
        for b in self.balls:
            b.draw(c)
        if self.shield_on and (self.skill_active > 90 or (self.t // 6) % 2):
            pygame.draw.rect(c, (255, 120, 170) if self.char == 5 else (255, 215, 90), (0, LH - 3, LW, 2))
            for hx in range(6, LW, 24):
                c.set_at((hx, LH - 4), PINK)
                c.set_at((hx + 2, LH - 4), PINK)
        glow = self.skill_active > 0 and (self.char == 0 or self.op)
        self.paddle.draw(c, self.t, glow)

        if self.char == 1 and self.skill_active > 0:
            tint = pygame.Surface((LW, LH), pygame.SRCALPHA)
            tint.fill((90, 140, 255, 28))
            c.blit(tint, (0, 0))
        if self.op and self.skill_active > 0:
            tint = pygame.Surface((LW, LH), pygame.SRCALPHA)
            tint.fill((255, 215, 90, 16 + (self.t // 4) % 2 * 6))
            c.blit(tint, (0, 0))

        for s, x, y, life, col in self.floaters:
            txt(s, "s", col, cx=LW // 2 if x < 0 else None, x=int(x), y=int(y))

        # HUD
        c.blit(HUD_BAR, (0, 0))
        pygame.draw.line(c, (70, 56, 120), (0, 11), (LW, 11))
        txt("SKOR %d" % self.score, "s", WHITE, x=3, y=3)
        txt("LV %d" % self.level, "s", YELLOW, cx=LW // 2, y=3)
        for i in range(self.lives):
            mini_cat(c, LW - 9 - i * 9, 3, self.cat["pal"])
        self.draw_skill_hud()
        txt("KUCING LV %d" % self.cat_level, "xs", (150, 140, 190), x=3, y=153)
        draw_coin(c, 150, 156)
        txt("%d" % SAVE["coins"], "xs", YELLOW, x=155, y=153)
        if self.boss:
            bs = self.boss
            txt(bs.name, "xs", (255, 150, 160), cx=150, y=12)
            pygame.draw.rect(c, (50, 20, 40), (108, 19, 84, 4))
            pygame.draw.rect(c, (230, 50, 80), (108, 19, int(84 * max(0, bs.hp) / bs.maxhp), 4))
            pygame.draw.rect(c, WHITE, (107, 18, 86, 6), 1)

        if self.state == "play" and self.balls[0].stuck and (self.t // 30) % 2:
            txt("SPASI / KLIK untuk meluncur", "s", WHITE, cx=LW // 2, y=LH // 2 + 22)
            txt("P = jeda", "xs", GRAY, cx=LW // 2, y=LH // 2 + 32)

        if self.state == "pause":
            self.draw_pause()
        elif self.state == "over":
            ov = pygame.Surface((LW, LH), pygame.SRCALPHA)
            ov.fill((10, 5, 20, 200))
            c.blit(ov, (0, 0))
            txt("GAME OVER", "b", (255, 110, 130), cx=LW // 2, y=20, wave=5)
            panel(c, (36, 50, 128, 50))
            txt("Skor  %d" % self.score, "m", WHITE, cx=LW // 2, y=52)
            txt("Terbaik  %d" % self.hi, "xs", YELLOW, cx=LW // 2, y=72)
            draw_coin(c, 48, 87)
            txt("Koin didapat  +%d   (total %d)" % (self.run_coins, SAVE["coins"]), "xs", YELLOW,
                x=54, y=84)
            txt("%s kecewa... :(" % self.cat["name"].capitalize(), "s", PINK, cx=LW // 2, y=104)
            if (self.t // 30) % 2:
                txt("SPASI = main lagi", "s", YELLOW, cx=LW // 2, y=118)
            txt("C = ganti kucing    G = gacha", "xs", GRAY, cx=LW // 2, y=134)

    def draw_pause(self):
        c = canvas
        ov = pygame.Surface((LW, LH), pygame.SRCALPHA)
        ov.fill((8, 4, 20, 175))
        c.blit(ov, (0, 0))
        panel(c, (44, 36, 112, 90), fill=(22, 14, 46, 240))
        txt("JEDA", "m", None, cx=LW // 2, y=40, rainbow=True, wave=2)
        labels = ["LANJUT", "MUSIK: %s" % ("ON" if music_on else "OFF"), "MENU UTAMA"]
        for i, lab in enumerate(labels):
            r = pmenu_rect(i)
            sel = i == self.pmenu
            if sel:
                pygame.draw.rect(c, (60, 44, 110), r, border_radius=2)
                pygame.draw.rect(c, YELLOW, r, 1, border_radius=2)
                pygame.draw.polygon(c, YELLOW, [(r.x + 4, r.y + 3), (r.x + 4, r.y + 9), (r.x + 8, r.y + 6)])
            txt(lab, "s", YELLOW if sel else GRAY, cx=r.centerx + 3, y=r.y + 2)
        txt("P / ESC = lanjut", "xs", GRAY, cx=LW // 2, y=112)

    def draw_skill_hud(self):
        c = canvas
        cat = self.cat
        if self.skill_active > 0:
            label, col = "%s AKTIF!" % cat["skill"].upper(), GREEN
            frac = self.skill_active / max(1, self.skill_dur_max)
            bar_col = col
        elif self.skill_cd > 0:
            label, col = "%s  %ds" % (cat["skill"], self.skill_cd // 60 + 1), GRAY
            frac = 1 - self.skill_cd / max(1, self.skill_cd_max)
            bar_col = (110, 100, 160)
        else:
            blink = (self.t // 15) % 2
            label, col = "[E] %s SIAP!" % cat["skill"].upper(), (YELLOW if blink else WHITE)
            frac = 1
            bar_col = YELLOW
        txt(label, "xs", col, x=3, y=12)
        pygame.draw.rect(c, (30, 22, 56), (3, 21, 52, 4))
        pygame.draw.rect(c, bar_col, (4, 22, int(50 * frac), 2))
        pygame.draw.rect(c, (110, 100, 160), (3, 21, 52, 4), 1)
        if frac >= 1 and self.skill_active == 0:
            sx = 4 + (self.t * 2) % 50
            c.set_at((sx, 22), WHITE)

    def draw_title(self):
        c = canvas
        txt("NEKO", "b", ORANGE, cx=LW // 2, y=6, wave=5)
        txt("BLOCK BREAKER", "b", None, cx=LW // 2, y=27, wave=4, rainbow=True)
        # deretan brick dekorasi bergelombang
        for i in range(12):
            yy = 62 + int(math.sin(self.t * 0.06 + i * 0.5) * 3)
            b = Brick(8 + i * 16, yy, "n", ROW_COLORS[i % len(ROW_COLORS)])
            b.draw(c)
        k = (self.t // 90) % N_CATS
        demo = Paddle(CATS[k]["pal"])
        demo.x = LW / 2 - demo.w / 2
        demo.y = 98
        demo.tier = min(7, k)
        demo.draw(c, self.t)
        bx = LW / 2 + math.sin(self.t * 0.05) * 40
        by = 84 - abs(math.sin(self.t * 0.12)) * 12
        pygame.draw.circle(c, YARN, (int(bx), int(by)), 3)
        c.set_at((int(bx) - 1, int(by) - 1), WHITE)
        draw_fish(c, 40, 102 + int(math.sin(self.t * 0.1) * 2), FISH_C)
        draw_fish(c, 152, 102 + int(math.cos(self.t * 0.1) * 2), YELLOW)
        if (self.t // 30) % 2:
            txt("SPASI / KLIK untuk mulai", "s", YELLOW, cx=LW // 2, y=116)
        txt("9 kucing - 4 boss - GACHA - kucing OP!", "xs", (200, 190, 230), cx=LW // 2, y=131)
        txt("G = gacha     M = musik     V = CRT", "xs", GRAY, cx=LW // 2, y=142)
        draw_coin(c, 8, 154)
        txt("%d" % SAVE["coins"], "xs", YELLOW, x=13, y=151)
        txt("Terbaik %d" % self.hi, "xs", GRAY, x=150, y=151)

    def draw_select(self):
        c = canvas
        txt("PILIH KUCINGMU", "m", None, cx=LW // 2, y=3, rainbow=True, wave=3)
        draw_coin(c, 166, 6)
        txt("%d" % SAVE["coins"], "xs", YELLOW, x=171, y=2)
        for i in range(N_SLOTS):
            r = card_rect(i)
            sel = i == self.sel
            if sel:
                r = r.move(0, -1)
            if i == GACHA_SLOT:
                panel(c, r, fill=(52, 34, 70, 235) if sel else (30, 20, 52, 225),
                      border=YELLOW if sel else (210, 150, 70))
                draw_capsule(c, r.centerx, r.y + 18, 8, rainbow_color(self.t // 6))
                txt("GACHA", "s", YELLOW if sel else GRAY, cx=r.centerx, y=r.y + 26)
                continue
            cat = CATS[i]
            owned = i in SAVE["owned"]
            rar = RARITY[cat["rarity"]]
            border = YELLOW if sel else (shade(rar["col"], -70) if owned else (60, 50, 90))
            panel(c, r, fill=(40, 28, 78, 235) if sel else (24, 16, 48, 225), border=border)
            pd = Paddle(cat["pal"] if owned else SIL_PAL)
            pd.x = r.x + (CARD_W - pd.w) / 2 - 1
            pd.y = r.y + 14
            pd.draw(c, self.t if sel else 1)
            for k in range(rar["stars"]):
                c.set_at((r.x + 3 + k * 2, r.y + 3), rar["col"])
                c.set_at((r.x + 3 + k * 2, r.y + 4), shade(rar["col"], -60))
            if owned and i == self.char:
                pygame.draw.rect(c, GREEN, (r.right - 6, r.y + 3, 3, 3))
            if not sel:
                dim = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
                dim.fill((15, 10, 30, 55))
                c.blit(dim, r.topleft)
            if owned:
                txt(cat["name"], "s", YELLOW if sel else GRAY, cx=r.centerx, y=r.y + 26)
            else:
                txt("???", "s", (110, 100, 150), cx=r.centerx, y=r.y + 26)

        panel(c, (6, 101, 188, 47), border=(160, 130, 255))
        if self.sel == GACHA_SLOT:
            draw_capsule(c, 17, 126, 8, rainbow_color(self.t // 6))
            txt("GACHA KUCING", "s", YELLOW, cx=LW // 2 + 6, y=103)
            txt("Putar koin jadi kucing baru, ada yang OP!", "xs", WHITE, cx=LW // 2 + 6, y=114)
            txt("1x = %d koin    10x = %d koin" % (GACHA_COST1, GACHA_COST10), "xs",
                (200, 190, 230), cx=LW // 2 + 6, y=123)
            txt("Kamu punya %d koin  -  %d/%d kucing" % (SAVE["coins"], len(SAVE["owned"]), N_CATS),
                "xs", GRAY, cx=LW // 2 + 6, y=132)
        else:
            cat = CATS[self.sel]
            rar = RARITY[cat["rarity"]]
            owned = self.sel in SAVE["owned"]
            if owned:
                draw_icon(c, cat["icon"], 17, 124)
                txt("SKILL: " + cat["skill"].upper(), "s", YELLOW, cx=LW // 2 + 2, y=103)
                txt(cat["d1"], "xs", WHITE, cx=LW // 2 + 6, y=114)
                txt(cat["d2"], "xs", (200, 190, 230), cx=LW // 2 + 6, y=123)
                txt("Cooldown %d detik  -  tombol E / SHIFT / klik kanan" % (cat["cd"] // 60),
                    "xs", GRAY, cx=LW // 2 + 6, y=132)
            else:
                txt("?", "m", (110, 100, 150), cx=17, y=114)
                txt("KUCING TERKUNCI", "s", (150, 140, 190), cx=LW // 2 + 2, y=103)
                txt("Dapatkan lewat GACHA kucing (tekan G)", "xs", WHITE, cx=LW // 2 + 6, y=114)
                txt("Peluang %d%% per tarikan  -  %s" % (rar["w"], rar["name"]), "xs",
                    rar["col"], cx=LW // 2 + 6, y=123)
                txt("Duplikat otomatis jadi koin", "xs", GRAY, cx=LW // 2 + 6, y=132)
            txt(rar["name"], "xs", rar["col"], cx=176, y=103)
        if self.msg_t > 0 and (self.t // 6) % 2:
            txt(self.msg, "s", RED, cx=LW // 2, y=149)
        elif (self.t // 30) % 2:
            txt("panah/mouse pilih    SPASI mulai    G gacha", "xs", WHITE, cx=LW // 2, y=150)

    def draw_gacha(self):
        c = canvas
        txt("GACHA KUCING", "m", None, cx=LW // 2, y=3, rainbow=True, wave=3)
        panel(c, (64, 19, 72, 11))
        draw_coin(c, 72, 24)
        txt("KOIN  %d" % SAVE["coins"], "xs", YELLOW, x=78, y=20)

        if self.gstate == "reveal":
            self.draw_reveal()
            self.draw_fx()
            return

        # kapsul
        bx, by = 100, 58
        if self.gstate == "open":
            amp = 1 + (80 - self.gtimer) / 14
            bx += int(math.sin(self.t * 1.7) * amp)
            by += int(math.cos(self.t * 2.3) * amp * 0.5)
            col = RARITY[self.gbest]["col"]
            gl = 20 + int(math.sin(self.t * 0.4) * 3)
            pygame.draw.circle(c, shade(col, -140), (bx, by), gl, 1)
            pygame.draw.circle(c, shade(col, -90), (bx, by), gl - 4, 1)
            if self.gtimer < 10:
                pygame.draw.circle(c, WHITE, (bx, by), 12 + (10 - self.gtimer) * 4)
        else:
            by += int(math.sin(self.t * 0.08) * 2)
            col = rainbow_color(self.t // 5)
        draw_capsule(c, bx, by, 14, col)
        self.draw_fx()

        txt("Epik pasti dalam %d tarikan" % (PITY_EPIC - SAVE["pity_epic"]), "xs",
            RARITY["E"]["col"], cx=LW // 2, y=76)
        txt("OP pasti dalam %d tarikan" % (PITY_OP - SAVE["pity_op"]), "xs",
            RARITY["O"]["col"], cx=LW // 2, y=85)
        for k, cx in (("C", 28), ("R", 76), ("E", 124), ("O", 170)):
            txt("%s %d%%" % (RARITY[k]["name"], RARITY[k]["w"]), "xs", RARITY[k]["col"], cx=cx, y=96)

        idle = self.gstate == "idle"
        costs = (GACHA_COST1, GACHA_COST10, 0)
        labels = ("PUTAR x1", "PUTAR x10", "KEMBALI")
        for i, r in enumerate(GBTN):
            sel = idle and i == self.gsel
            can = i == 2 or SAVE["coins"] >= costs[i]
            panel(c, r, fill=(52, 38, 94, 240) if sel else (24, 16, 48, 230),
                  border=YELLOW if sel else (100, 85, 150))
            if sel:
                pygame.draw.rect(c, YELLOW, r.inflate(2, 2), 1)
            txt(labels[i], "s", (YELLOW if sel else WHITE) if can else (130, 120, 160),
                cx=r.centerx, y=r.y + 3)
            if i < 2:
                draw_coin(c, r.centerx - 9, r.y + 18)
                txt("%d" % costs[i], "xs", YELLOW if can else (130, 120, 160), x=r.centerx - 4, y=r.y + 14)
            else:
                txt("ESC", "xs", GRAY, cx=r.centerx, y=r.y + 14)
        if self.gmsg_t > 0 and (self.t // 6) % 2:
            txt(self.gmsg, "s", RED, cx=LW // 2, y=137)
        elif idle and (self.t // 30) % 2:
            txt("panah/mouse pilih    SPASI/klik    1 = x1   2 = x10", "xs", WHITE, cx=LW // 2, y=148)
        elif self.gstate == "open" and (self.t // 15) % 2:
            txt("SPASI = lewati", "xs", GRAY, cx=LW // 2, y=148)

    def draw_reveal(self):
        c = canvas
        res = self.gres[self.gidx]
        cat = CATS[res["idx"]]
        rar = RARITY[res["r"]]
        col = rar["col"]
        gt = self.gtimer
        cx, cy = 100, 52
        # sinar berputar
        rays = pygame.Surface((LW, LH), pygame.SRCALPHA)
        n = 16 if res["r"] in ("C", "R") else 24
        for k in range(n):
            a = k * math.tau / n + self.t * (0.012 if res["r"] != "O" else 0.03)
            pts = [(cx, cy), (cx + math.cos(a) * 130, cy + math.sin(a) * 130),
                   (cx + math.cos(a + 0.1) * 130, cy + math.sin(a + 0.1) * 130)]
            pygame.draw.polygon(rays, (col[0], col[1], col[2], 48), pts)
        c.blit(rays, (0, 0))
        pygame.draw.circle(c, shade(col, -150), (cx, cy), 34, 1)
        pygame.draw.circle(c, shade(col, -110), (cx, cy), 28, 1)
        # sprite kucing 2x
        sc = min(1.0, gt / 10)
        if sc > 0.15:
            tmp = pygame.Surface((50, 20), pygame.SRCALPHA)
            pd = Paddle(cat["pal"])
            pd.x, pd.y, pd.tier = 10, 8, 4 if res["r"] != "O" else 7
            pd.draw(tmp, self.t)
            big = pygame.transform.scale(tmp, (int(100 * sc), int(40 * sc)))
            c.blit(big, (cx - big.get_width() // 2, cy - big.get_height() // 2))
        # bintang rarity
        ns = rar["stars"]
        for k in range(ns):
            draw_star(c, cx + int((k - (ns - 1) / 2) * 11), 76, 4, col)
        if res["r"] == "O":
            txt(cat["name"] + " NEKO", "m", None, cx=LW // 2, y=82, rainbow=True, wave=3)
        else:
            txt(cat["name"], "m", col, cx=LW // 2, y=82, wave=2 if res["r"] == "E" else 0)
        txt(rar["name"], "xs", col, cx=LW // 2, y=97)
        if res["new"]:
            txt("BARU!", "s", GREEN if (self.t // 5) % 2 else WHITE, cx=LW // 2, y=105)
        else:
            txt("DUPLIKAT  +%d KOIN" % res["refund"], "s", GRAY, cx=LW // 2, y=105)
        panel(c, (14, 117, 172, 26), border=shade(col, -40))
        txt("SKILL: " + cat["skill"].upper(), "xs", YELLOW, cx=LW // 2, y=119)
        txt(cat["d1"], "xs", WHITE, cx=LW // 2, y=127)
        txt(cat["d2"], "xs", (200, 190, 230), cx=LW // 2, y=135)
        more = len(self.gres) > 1
        if (self.t // 30) % 2:
            tail = "(%d/%d)" % (self.gidx + 1, len(self.gres)) if more else ""
            txt("SPASI = lanjut  %s" % tail, "xs", WHITE, cx=LW // 2, y=148)
        if gt < 8:      # kilatan putih
            fl = pygame.Surface((LW, LH), pygame.SRCALPHA)
            fl.fill((255, 255, 255, int(255 * (1 - gt / 8))))
            c.blit(fl, (0, 0))

    def draw_upgrade(self):
        c = canvas
        txt("KUCING NAIK LEVEL!", "m", None, cx=LW // 2, y=3, rainbow=True, wave=3)
        txt("Boss kalah! Pilih 1 upgrade", "xs", (200, 190, 230), cx=LW // 2, y=20)
        n = len(self.upg_choices)
        for i, key in enumerate(self.upg_choices):
            u = UPGRADES[key]
            r = upg_rect(i, n)
            sel = i == self.upg_sel
            if sel:
                r = r.move(0, -2)
            panel(c, r, fill=(44, 30, 84, 240) if sel else (24, 16, 48, 230),
                  border=YELLOW if sel else (100, 85, 150))
            draw_upg_icon(c, key, r.centerx, r.y + 12)
            ty = r.y + 22
            for ln in u["title"]:
                txt(ln, "xs", YELLOW if sel else (225, 215, 150), cx=r.centerx, y=ty)
                ty += 7
            ty += 2
            if key == "life":
                txt("+1", "xs", GREEN, cx=r.centerx, y=ty)
            else:
                lv = self.up[key]
                txt("Lv %d > %d" % (lv, lv + 1), "xs", GREEN, cx=r.centerx, y=ty)
            ty += 9
            for ln in u["desc"]:
                txt(ln, "xs", WHITE if sel else GRAY, cx=r.centerx, y=ty)
                ty += 7
            txt(str(i + 1), "xs", (150, 140, 190), x=r.x + 3, y=r.y + 2)
        txt("1 / 2 / 3  atau  panah + ENTER  atau  klik", "xs", WHITE, cx=LW // 2, y=119)
        pv = Paddle(self.cat["pal"])
        pv.x = LW / 2 - pv.w / 2
        pv.y = 136
        pv.tier = self.cat_level  # pratinjau: tampilan setelah naik level
        pv.draw(c, self.t)
        txt("%s  LV %d  >  LV %d" % (self.cat["name"], self.cat_level, self.cat_level + 1),
            "xs", YELLOW, cx=LW // 2, y=150)

    def render(self):
        global TICK
        TICK = self.t
        self.draw()
        scaled = pygame.transform.scale(canvas, (WIDTH, HEIGHT))
        screen.fill((0, 0, 0))
        ox = oy = 0
        if self.shake:
            ox = random.randint(-self.shake, self.shake) * 2
            oy = random.randint(-self.shake, self.shake) * 2
        screen.blit(scaled, (ox, oy))
        if crt_on:
            screen.blit(OVERLAY, (0, 0))
        flush_text(ox, oy)
        if self.fade > 0:
            FADE.set_alpha(int(255 * self.fade / FADE_T))
            screen.blit(FADE, (0, 0))
        pygame.display.flip()


def main():
    global SOUND_OK
    load_save()
    SOUND_OK = init_sound()
    game = Game()
    running = True
    while running:
        for e in pygame.event.get():
            if not game.handle_event(e):
                running = False
        game.update()
        game.render()
        clock.tick(FPS)
    save_game()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()