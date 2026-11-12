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
