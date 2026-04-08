"""
DUNGEON OF SHADOWS  —  First-Person Raycaster
32-bit Pixel Art Edition
pip install pygame
"""

import pygame, sys, math, random
pygame.init()

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
SW, SH = screen.get_size()
pygame.display.set_caption("Dungeon FPS — 32-bit Pixel Art")
clock = pygame.time.Clock()

# Quarter-resolution render — each rendered pixel = 4×4 block on screen
RW = SW // 4
RH = SH
HALF_H  = RH // 2
render_surf = pygame.Surface((RW, RH))

FOV      = math.pi / 3
HALF_FOV = FOV / 2
NUM_RAYS = RW
MAX_D    = 14.0
HUD_H    = int(SH * 0.22)
VIEW_H   = SH - HUD_H
HALF_VH  = VIEW_H // 2

SHADE_STEPS = 6

# ── Palette — Gothic Dungeon ──────────────────────────────────────────────────
SKY     = (16,  12,  26)   # deep indigo ceiling
GROUND  = (18,  16,  22)   # dark purple-gray stone floor
WALL_N  = (62,  58,  74)   # north: cool purple-gray stone
WALL_S  = (36,  32,  46)   # south: dark shadowed stone
WALL_E  = (82,  76,  94)   # east:  lighter stone (lit face)
WALL_W  = (48,  44,  58)   # west:  medium stone
MORTAR  = (10,   8,  14)   # dark mortar with purple tint
MOSS_C  = (28,  56,  34)   # dark green moss in crevices
VINE_C  = (22,  48,  28)   # vine green
TORCH_C = (255, 140,  24)  # warm amber torch flame
GOLD    = (220, 180,  40)  # pixel gold
RED_LT  = (200,  36,  36)  # deep red
GREEN   = ( 28, 200,  52)  # vivid green
GREY    = (100, 102, 116)  # cool gray-purple text
WHITE   = (215, 218, 228)  # cool near-white
BLACK   = (  0,   0,   0)
BTN_BG  = ( 14,  12,  20)  # button background — purple tint
BTN_BD  = ( 58,  54,  72)  # button border — stone purple-gray
BTN_HL  = ( 82,  78,  96)  # button highlight

# ── Map ───────────────────────────────────────────────────────────────────────
MAP = [
    "################",
    "#..............#",
    "#.T##..T..##.T.#",
    "#..#........#..#",
    "#..#.######.#..#",
    "#....#....#....#",
    "#.T..#....#..T.#",
    "#....#....#....#",
    "#..#.######.#..#",
    "#..#........#..#",
    "#.T##..T..##.T.#",
    "#..............#",
    "################",
    "################",
]
MAP_W = len(MAP[0])
MAP_H = len(MAP)

TORCHES = [(ci, ri) for ri, row in enumerate(MAP)
           for ci, ch in enumerate(row) if ch == 'T']

def cell(x, y):
    mx, my = int(x), int(y)
    if 0 <= my < MAP_H and 0 <= mx < MAP_W:
        return MAP[my][mx]
    return '#'

def is_wall(x, y):
    return cell(x, y) == '#'

# ── DDA Raycaster — returns (dist, side, hit_frac) ───────────────────────────
def cast_ray(ox, oy, angle):
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    map_x, map_y = int(ox), int(oy)
    if cos_a == 0: cos_a = 1e-10
    if sin_a == 0: sin_a = 1e-10
    delta_x = abs(1 / cos_a)
    delta_y = abs(1 / sin_a)
    step_x = 1 if cos_a > 0 else -1
    step_y = 1 if sin_a > 0 else -1
    side_x = (map_x + (1 if cos_a > 0 else 0) - ox) / cos_a
    side_y = (map_y + (1 if sin_a > 0 else 0) - oy) / sin_a
    side = 0
    for _ in range(int(MAX_D * 2)):
        if side_x < side_y:
            side_x += delta_x
            map_x  += step_x
            side = 0
        else:
            side_y += delta_y
            map_y  += step_y
            side = 1
        if 0 <= map_y < MAP_H and 0 <= map_x < MAP_W and MAP[map_y][map_x] == '#':
            if side == 0:
                dist = (map_x - ox + (0 if step_x > 0 else 1)) / cos_a
                hit_frac = (oy + dist * sin_a) % 1.0
            else:
                dist = (map_y - oy + (0 if step_y > 0 else 1)) / sin_a
                hit_frac = (ox + dist * cos_a) % 1.0
            return max(0.01, dist), side, hit_frac
    return MAX_D, 0, 0.0

# ── Player ────────────────────────────────────────────────────────────────────
class Player:
    MAXHP = 100
    SPD   = 0.04
    ROT   = 0.04
    ATK   = 35
    ATKR  = 2.2

    def __init__(self):
        self.x     = 1.5
        self.y     = 1.5
        self.angle = 0.0
        self.hp    = self.MAXHP
        self.alive = True
        self.flash = 0
        self.acd   = 0
        self.score = 0
        self.bob   = 0.0
        self.move_fwd = False
        self.move_bk  = False
        self.turn_l   = False
        self.turn_r   = False

    def update(self, enemies):
        if not self.alive: return
        moved = False
        if self.turn_l: self.angle -= self.ROT
        if self.turn_r: self.angle += self.ROT
        dx = math.cos(self.angle) * self.SPD
        dy = math.sin(self.angle) * self.SPD
        if self.move_fwd:
            nx, ny = self.x + dx, self.y + dy
            if not is_wall(nx, self.y): self.x = nx
            if not is_wall(self.x, ny): self.y = ny
            moved = True
        if self.move_bk:
            nx, ny = self.x - dx, self.y - dy
            if not is_wall(nx, self.y): self.x = nx
            if not is_wall(self.x, ny): self.y = ny
            moved = True
        if moved: self.bob += 0.25
        if self.flash > 0: self.flash -= 1
        if self.acd   > 0: self.acd   -= 1

    def attack(self, enemies):
        if self.acd > 0 or not self.alive: return False
        self.acd = 25
        hit = False
        for e in enemies:
            if not e.alive: continue
            d = math.hypot(e.x - self.x, e.y - self.y)
            if d < self.ATKR:
                dx, dy = e.x - self.x, e.y - self.y
                ea = math.atan2(dy, dx)
                da = ea - self.angle
                while da >  math.pi: da -= 2*math.pi
                while da < -math.pi: da += 2*math.pi
                if abs(da) < HALF_FOV * 0.9:
                    e.do_hit(self.ATK)
                    hit = True
                    if not e.alive: self.score += 10
        return hit

    def damage(self, dmg):
        self.hp -= dmg
        self.flash = 15
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

# ── Enemy ─────────────────────────────────────────────────────────────────────
class Enemy:
    MAXHP = 50
    SPD   = 0.012
    ATKR  = 0.7
    ATKD  = 6
    ATKCD = 80
    DETR  = 7.0

    def __init__(self, x, y):
        self.x     = x
        self.y     = y
        self.hp    = self.MAXHP
        self.alive = True
        self.acd   = random.randint(0, self.ATKCD)
        self.wt    = 0
        self.wdx   = 0.0
        self.wdy   = 0.0
        self.flash = 0

    def update(self, player):
        if not self.alive: return
        if self.flash > 0: self.flash -= 1
        if self.acd   > 0: self.acd   -= 1
        d = math.hypot(player.x - self.x, player.y - self.y)
        if d < self.ATKR and self.acd == 0 and player.alive:
            player.damage(self.ATKD)
            self.acd = self.ATKCD
            return
        if d < self.DETR and player.alive and d > 0.01:
            ax, ay = (player.x - self.x) / d, (player.y - self.y) / d
        else:
            self.wt -= 1
            if self.wt <= 0:
                ang = random.uniform(0, math.pi * 2)
                self.wdx, self.wdy = math.cos(ang), math.sin(ang)
                self.wt = random.randint(60, 180)
            ax, ay = self.wdx, self.wdy
        nx = self.x + ax * self.SPD
        ny = self.y + ay * self.SPD
        if not is_wall(nx, self.y): self.x = nx
        if not is_wall(self.x, ny): self.y = ny

    def do_hit(self, dmg):
        self.hp -= dmg
        self.flash = 10
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

ENEMY_STARTS = [(3.5,3.5),(12.5,3.5),(3.5,10.5),(12.5,10.5),
                (8.5,6.5),(6.5,7.5),(10.5,7.5)]

# ── Touch Buttons ─────────────────────────────────────────────────────────────
class Button:
    def __init__(self, label, cx, cy, r):
        self.label   = label
        self.cx, self.cy = cx, cy
        self.r       = r
        self.pressed = False

    def hit(self, x, y):
        return abs(x - self.cx) < self.r and abs(y - self.cy) < self.r

    def draw(self, surf, font):
        r   = self.r
        bdr = max(3, r // 7)
        col = BTN_HL if self.pressed else BTN_BG
        rx_, ry_ = self.cx - r, self.cy - r
        rw_, rh_ = r * 2, r * 2
        pygame.draw.rect(surf, (6, 4, 8), (rx_ + 4, ry_ + 4, rw_, rh_))
        pygame.draw.rect(surf, col, (rx_, ry_, rw_, rh_))
        pygame.draw.rect(surf, BTN_BD, (rx_, ry_, rw_, rh_), bdr)
        hl = tuple(min(c + 40, 255) for c in col)
        pygame.draw.line(surf, hl, (rx_+bdr, ry_+bdr), (rx_+rw_-bdr, ry_+bdr), 2)
        pygame.draw.line(surf, hl, (rx_+bdr, ry_+bdr), (rx_+bdr, ry_+rh_-bdr), 2)
        sh = tuple(max(c - 20, 0) for c in BTN_BD)
        pygame.draw.line(surf, sh, (rx_+rw_-bdr, ry_+bdr),     (rx_+rw_-bdr, ry_+rh_-bdr), 2)
        pygame.draw.line(surf, sh, (rx_+bdr,     ry_+rh_-bdr), (rx_+rw_-bdr, ry_+rh_-bdr), 2)
        txt = font.render(self.label, True, WHITE)
        surf.blit(txt, (self.cx - txt.get_width()//2, self.cy - txt.get_height()//2))


def make_buttons():
    r   = int(SH * 0.07)
    by  = SH - HUD_H // 2
    gap = int(SW * 0.14)
    lx  = int(SW * 0.18)
    rx  = int(SW * 0.82)
    return {
        'fwd' : Button("^",   lx,       by - r, r),
        'bk'  : Button("v",   lx,       by + r, r),
        'left': Button("<",   lx - gap, by,     r),
        'right':Button(">",   lx + gap, by,     r),
        'atk' : Button("ATK", rx,       by,     int(r*1.3)),
    }


# ── draw_view ─────────────────────────────────────────────────────────────────
def draw_view(surf, player, enemies, zbuf, t):

    # ── Ceiling — dark indigo stone with beam structure ──
    surf.fill(SKY, (0, 0, RW, HALF_H))
    # Crossbeam lines on ceiling (perspective-corrected)
    beam_col = (24, 18, 36)
    beam_hi  = (30, 24, 44)
    for bd in [0.7, 1.4, 2.4, 3.8, 6.0, 10.0]:
        cy = int(HALF_H - (RH - HALF_H) * 0.40 / (bd * 0.5 + 0.001))
        cy = max(0, min(HALF_H - 1, cy))
        pygame.draw.line(surf, beam_col, (0, cy), (RW, cy), max(1, 3 - int(bd * 0.3)))
        if cy + 1 < HALF_H:
            pygame.draw.line(surf, beam_hi, (0, cy + 1), (RW, cy + 1), 1)
    # Vertical ceiling beams
    for vb in range(0, RW, max(4, RW // 8)):
        pygame.draw.line(surf, beam_col, (vb, 0), (vb, HALF_H // 3), 1)
    # Subtle purple haze near horizon
    pygame.draw.rect(surf, (22, 16, 32), (0, HALF_H - HALF_H//5, RW, HALF_H//5))

    # ── Floor — cobblestone with moss growth ──
    surf.fill(GROUND, (0, HALF_H, RW, RH - HALF_H))
    tile_col  = (GROUND[0]+10, GROUND[1]+9, GROUND[2]+12)
    moss_line = (MOSS_C[0]//2, MOSS_C[1]//2, MOSS_C[2]//2)
    for row_dist in [0.6, 0.9, 1.3, 1.8, 2.5, 3.4, 4.8, 6.8, 10.0, 15.0]:
        proj_y = int(HALF_H + (RH - HALF_H) * 0.45 / (row_dist * 0.5 + 0.001))
        proj_y = min(RH - 1, max(HALF_H + 1, proj_y))
        pygame.draw.line(surf, tile_col, (0, proj_y), (RW, proj_y), 1)
        # Moss between floor tiles
        if proj_y + 1 < RH:
            pygame.draw.line(surf, moss_line, (0, proj_y + 1), (RW, proj_y + 1), 1)

    # Torch flicker
    flicker = 1.0 + math.sin(t * 9.1) * 0.08 + math.sin(t * 17.3) * 0.05

    # Torch glow — player-position-based, warm amber with stronger reach
    raw_glow = 0.0
    for (tc, tr) in TORCHES:
        td = math.hypot(player.x - tc, player.y - tr)
        raw_glow += max(0.0, (1.0 - td / 4.2) * flicker) * 0.5
    raw_glow = min(raw_glow, 0.6)

    # ── Brick constants ──
    BRICK_H  = 0.28   # brick height (slightly shorter, more rows)
    BRICK_W  = 0.45   # brick width
    MORT_AMT = 28     # mortar darkening amount
    MOSS_CHN = 0.35   # chance of moss in mortar

    # ── Raycasting ──
    for col_i in range(NUM_RAYS):
        ray_angle = player.angle - HALF_FOV + (col_i / NUM_RAYS) * FOV
        dist, side, hit_frac = cast_ray(player.x, player.y, ray_angle)
        corr = dist * math.cos(ray_angle - player.angle)
        zbuf[col_i] = corr

        wall_h = min(int(RH / (corr + 0.0001) * 0.8), RH)
        top    = HALF_H - wall_h // 2

        # Side-based colour
        if side == 0:
            base = WALL_E if math.cos(ray_angle) > 0 else WALL_W
        else:
            base = WALL_S if math.sin(ray_angle) > 0 else WALL_N

        # Distance shading
        shade   = max(0.04, 1.0 - corr / MAX_D)
        shade_q = round(shade * SHADE_STEPS) / SHADE_STEPS

        # Torch amber tint — stronger warm glow
        glow_q = round(raw_glow * SHADE_STEPS) / SHADE_STEPS
        r = min(int(base[0] * shade_q + TORCH_C[0] * glow_q * 0.20), 255)
        g = min(int(base[1] * shade_q + TORCH_C[1] * glow_q * 0.08), 255)
        b = min(int(base[2] * shade_q * 1.05), 255)  # slight purple boost

        # Vertical mortar seam from hit_frac — with moss
        seam = hit_frac % BRICK_W
        is_v_seam = seam < 0.035 or seam > (BRICK_W - 0.035)
        if is_v_seam:
            # Determine if this seam has moss based on position
            seam_seed = int(hit_frac * 100 + col_i * 7) % 100
            if seam_seed < MOSS_CHN * 100:
                moss_sh = max(0.15, shade_q * 0.7)
                r = int(MOSS_C[0] * moss_sh)
                g = int(MOSS_C[1] * moss_sh)
                b = int(MOSS_C[2] * moss_sh)
            else:
                r = max(r - MORT_AMT, 0)
                g = max(g - MORT_AMT, 0)
                b = max(b - MORT_AMT, 0)

        wall_col = (r, g, b)
        mort_col = (max(r - MORT_AMT, 0), max(g - MORT_AMT, 0), max(b - MORT_AMT, 0))
        moss_col = (int(MOSS_C[0] * shade_q * 0.6),
                    int(MOSS_C[1] * shade_q * 0.6),
                    int(MOSS_C[2] * shade_q * 0.6))

        # Solid wall strip
        pygame.draw.rect(surf, wall_col, (col_i, top, 1, wall_h))

        # Horizontal mortar lines with moss growth
        if wall_h > 5:
            brick_h_px = max(3, int(wall_h * BRICK_H))
            offset = int(hit_frac * brick_h_px * 1.7) % brick_h_px
            by_m = top + (brick_h_px - offset) % brick_h_px
            row_idx = 0
            while by_m < top + wall_h:
                if 0 <= by_m < RH:
                    # Moss in some horizontal mortar lines
                    m_seed = (int(hit_frac * 50) + row_idx * 13) % 100
                    if m_seed < MOSS_CHN * 100:
                        surf.set_at((col_i, by_m), moss_col)
                        # Moss drip below mortar line
                        if by_m + 1 < min(RH, top + wall_h) and m_seed < 15:
                            surf.set_at((col_i, by_m + 1), moss_col)
                    else:
                        surf.set_at((col_i, by_m), mort_col)
                by_m += brick_h_px
                row_idx += 1

        # Ambient occlusion at wall top/bottom edges — deeper shadows
        if wall_h > 10:
            ao_h = max(1, wall_h // 8)
            ao_c = (max(r-62, 0), max(g-56, 0), max(b-48, 0))
            pygame.draw.rect(surf, ao_c, (col_i, top, 1, ao_h))
            pygame.draw.rect(surf, ao_c, (col_i, top + wall_h - ao_h, 1, ao_h))
            # Vine creep at wall top (some columns)
            vine_seed = (col_i * 31 + int(hit_frac * 200)) % 100
            if vine_seed < 12 and wall_h > 20:
                vine_len = max(1, wall_h // 6)
                vine_c = (int(VINE_C[0] * shade_q),
                          int(VINE_C[1] * shade_q),
                          int(VINE_C[2] * shade_q))
                pygame.draw.rect(surf, vine_c, (col_i, top, 1, vine_len))

    # ── Enemy sprites ──
    living = [(e, math.hypot(e.x-player.x, e.y-player.y)) for e in enemies if e.alive]
    living.sort(key=lambda x: -x[1])

    for e, dist_e in living:
        if dist_e < 0.3: continue
        dx, dy = e.x - player.x, e.y - player.y
        sprite_angle = math.atan2(dy, dx) - player.angle
        while sprite_angle >  math.pi: sprite_angle -= 2*math.pi
        while sprite_angle < -math.pi: sprite_angle += 2*math.pi
        if abs(sprite_angle) > HALF_FOV + 0.15: continue
        corr_d = dist_e * math.cos(sprite_angle)
        if corr_d <= 0: continue

        proj_h = max(2, int(RH / corr_d * 0.75))
        proj_w = max(1, int(proj_h * 0.55))
        sx     = int((0.5 + sprite_angle / FOV) * RW) - proj_w // 2
        sy     = HALF_H - proj_h // 2

        mid_col = sx + proj_w // 2
        if not (0 <= mid_col < RW) or zbuf[mid_col] < corr_d:
            continue

        sshade   = max(0.15, 1.0 - corr_d / MAX_D)
        is_hit   = e.flash % 4 < 2 and e.flash > 0
        skin_raw = (255, 80, 80) if is_hit else (72, 145, 68)
        skin_col = tuple(int(c * sshade) for c in skin_raw)
        robe_col = tuple(int(c * sshade) for c in (38, 52, 34))
        robe_drk = tuple(int(c * sshade) for c in (18, 28, 16))
        eye_col  = (min(int(240*sshade), 255), min(int(200*sshade), 255), min(int(20*sshade), 255))

        bx_ = max(sx, 0)
        by_ = sy + proj_h // 3
        bw_ = min(proj_w, RW - bx_)
        bh_ = proj_h - proj_h // 3
        if bw_ > 0 and bh_ > 0:
            pygame.draw.rect(surf, robe_col, (bx_, by_, bw_, bh_))
            ew_ = max(1, bw_ // 4)
            pygame.draw.rect(surf, robe_drk, (bx_, by_, ew_, bh_))
            if bx_ + bw_ - ew_ < RW:
                pygame.draw.rect(surf, robe_drk, (bx_+bw_-ew_, by_, ew_, bh_))
            s_col = tuple(min(c+18, 255) for c in robe_col)
            stx_  = sx + proj_w//2 - max(1, proj_w//5)
            stw_  = max(1, proj_w // 3)
            if 0 <= stx_ < RW:
                pygame.draw.rect(surf, s_col, (stx_, by_, min(stw_, RW-stx_), bh_//2))

        head_w = max(3, proj_w * 3 // 4)
        head_h = max(2, proj_h // 5)
        hx_    = sx + (proj_w - head_w) // 2
        hy_    = sy + proj_h // 9
        hxc    = max(hx_, 0)
        hwc    = min(head_w, RW - hxc)
        if hwc > 0 and head_h > 0:
            pygame.draw.rect(surf, skin_col, (hxc, hy_, hwc, head_h))
            # Darker scalp / brow ridge
            hood = tuple(max(c-50, 0) for c in skin_col)
            pygame.draw.rect(surf, hood, (hxc, hy_, hwc, max(1, head_h // 3)))
            if head_w > 3 and head_h > 2:
                ew2  = max(1, head_w // 5)
                ehy2 = hy_ + head_h * 2 // 3
                elx  = hx_ + head_w // 4 - ew2 // 2
                erx  = hx_ + head_w * 3 // 4 - ew2 // 2
                if 0 <= elx < RW:
                    pygame.draw.rect(surf, eye_col, (elx, ehy2, ew2, ew2))
                if 0 <= erx < RW:
                    pygame.draw.rect(surf, eye_col, (erx, ehy2, ew2, ew2))

        if proj_w > 4:
            bw_h  = proj_w
            bh_h  = max(2, proj_h // 14)
            bxh   = sx
            bby   = sy - bh_h - 2
            if bxh + bw_h > 0 and bxh < RW:
                segs   = max(1, bw_h // max(2, bw_h // 5))
                segw   = bw_h // segs
                filled = int(segs * e.hp / e.MAXHP)
                for si in range(segs):
                    sxs = bxh + si * segw
                    if sxs < 0 or sxs >= RW: continue
                    sc_ = (60, 180, 60) if si < filled else (14, 28, 14)
                    pygame.draw.rect(surf, sc_, (sxs, bby, max(1, segw-1), bh_h))

    # ── Torch sprites ──
    for tc, tr in TORCHES:
        dx_t   = (tc + 0.5) - player.x
        dy_t   = (tr + 0.5) - player.y
        dist_t = math.hypot(dx_t, dy_t)
        if dist_t < 0.2: continue
        sa_t   = math.atan2(dy_t, dx_t) - player.angle
        while sa_t >  math.pi: sa_t -= 2*math.pi
        while sa_t < -math.pi: sa_t += 2*math.pi
        if abs(sa_t) > HALF_FOV + 0.1: continue
        corr_t = dist_t * math.cos(sa_t)
        if corr_t <= 0.01: continue
        mid_t  = int((0.5 + sa_t / FOV) * RW)
        if not (0 <= mid_t < RW) or zbuf[mid_t] < corr_t: continue

        proj_ht = max(2, int(RH / corr_t * 0.22))
        proj_wt = max(1, proj_ht // 2)
        stx     = mid_t - proj_wt // 2
        sty     = HALF_H - proj_ht // 2
        flick_v = 1.0 + math.sin(t*9.1)*0.18 + math.sin(t*17.3)*0.10

        stick_x = max(0, stx + proj_wt // 4)
        stick_w = max(1, proj_wt // 2)
        # Iron bracket
        pygame.draw.rect(surf, (42, 38, 48),
            (stick_x - max(1, stick_w), sty + proj_ht//2, stick_w * 3, max(1, proj_ht//8)))
        # Wooden stick
        pygame.draw.rect(surf, (62, 40, 16),
            (stick_x, sty + proj_ht//2, stick_w, max(1, proj_ht//2)))

        flame_h = max(1, proj_ht // 2)
        # Determine torch type based on position for variety
        is_green_torch = (tc + tr) % 3 == 0
        for fi in range(flame_h):
            ratio = fi / max(flame_h, 1)
            if is_green_torch:
                fr = min(255, int((40 + 60 * ratio) * flick_v))
                fg = min(255, int((220 - 100*ratio) * flick_v))
                fb = min(255, int((80 - 40*ratio) * flick_v))
            else:
                fr = min(255, int(255 * flick_v))
                fg = min(255, int((140 - 90*ratio) * flick_v))
                fb = min(255, int(18 * flick_v))
            fw = max(1, int(proj_wt * (1.0 - ratio * 0.55)))
            fxs = stx + (proj_wt - fw) // 2
            if 0 <= fxs < RW and 0 <= sty + fi < RH:
                pygame.draw.rect(surf, (fr, fg, fb), (fxs, sty + fi, fw, 1))

    # ── Weapon — large, anchored bottom-right, FPS style ──
    sw_w  = max(8, RW // 5)
    sw_h  = max(16, HALF_H // 2 + HALF_H // 4)
    bob_y = int(math.sin(player.bob) * max(2, RH // 55))
    bx_sw = RW - sw_w + sw_w // 3     # right side, partially cropped
    by_sw = RH - sw_h + sw_h // 5 + bob_y  # bottom anchored

    blade_w = max(3, sw_w // 3)
    blade_h = sw_h * 3 // 4
    guard_h = max(4, sw_h // 7)
    grip_w  = max(2, sw_w // 4)
    grip_h  = max(4, sw_h // 4)
    blade_x = bx_sw + (sw_w - blade_w) // 2
    guard_y = by_sw + blade_h
    grip_x  = bx_sw + (sw_w - grip_w) // 2
    grip_y  = guard_y + guard_h

    # Blade — dark steel with cold sheen
    pygame.draw.rect(surf, (90, 88, 98), (blade_x, by_sw, blade_w, blade_h))
    pygame.draw.rect(surf, (160, 165, 178),
        (blade_x + blade_w//3, by_sw + 2, max(1, blade_w//3), blade_h - 4))
    pygame.draw.rect(surf, (48, 46, 54), (blade_x, by_sw, 1, blade_h))
    pygame.draw.rect(surf, (48, 46, 54), (blade_x + blade_w - 1, by_sw, 1, blade_h))

    # Cross-guard — dark iron with purple tint
    gw = sw_w
    pygame.draw.rect(surf, (72, 58, 48),   (bx_sw, guard_y, gw, guard_h))
    pygame.draw.rect(surf, (110, 90, 72), (bx_sw, guard_y, gw, 2))
    pygame.draw.rect(surf, (38, 30, 24),   (bx_sw, guard_y + guard_h - 2, gw, 2))

    # Grip — dark leather with purple wrap
    pygame.draw.rect(surf, (42, 28, 32), (grip_x, grip_y, grip_w, grip_h))
    wrap_step = max(2, grip_h // 4)
    for gi in range(0, grip_h, wrap_step):
        pygame.draw.line(surf, (28, 18, 22),
            (grip_x, grip_y+gi), (grip_x+grip_w, grip_y+gi), 1)

    # Pommel — skull-shaped dark iron
    pom_w = grip_w + 4
    pom_h = max(3, grip_h // 3)
    pygame.draw.rect(surf, (82, 74, 68), (grip_x - 2, grip_y + grip_h, pom_w, pom_h))

    # ── Damage flash vignette ──
    if player.flash > 0:
        alpha = int(player.flash / 15 * 120)
        vsurf = pygame.Surface((RW, RH), pygame.SRCALPHA)
        vsurf.fill((180, 20, 20, alpha))
        surf.blit(vsurf, (0, 0))


# ── draw_hud_panel ────────────────────────────────────────────────────────────
def draw_hud_panel(surf, player, buttons, font, sfont):
    pygame.draw.rect(surf, (10, 8, 16), (0, VIEW_H, SW, HUD_H))
    pygame.draw.line(surf, BTN_BD, (0, VIEW_H),   (SW, VIEW_H),   3)
    pygame.draw.line(surf, BTN_HL, (0, VIEW_H+3), (SW, VIEW_H+3), 1)
    for cx_, cy_ in [(0, VIEW_H), (SW-8, VIEW_H)]:
        pygame.draw.rect(surf, GOLD, (cx_, cy_, 8, 8))

    bw = int(SW * 0.25)
    draw_bar(surf, 10, VIEW_H + 10, player.hp, player.MAXHP, bw, 18)
    surf.blit(sfont.render("HP", True, GREY), (bw + 18, VIEW_H + 12))

    sc_text = "SCORE {:05d}".format(player.score)
    sc      = font.render(sc_text, True, GOLD)
    sc_x    = SW//2 - sc.get_width()//2
    sc_y    = VIEW_H + 8
    pygame.draw.rect(surf, (6, 4, 10),
        (sc_x - 8, sc_y - 3, sc.get_width() + 16, sc.get_height() + 6))
    pygame.draw.rect(surf, BTN_BD,
        (sc_x - 8, sc_y - 3, sc.get_width() + 16, sc.get_height() + 6), 2)
    surf.blit(sc, (sc_x, sc_y))

    for btn in buttons.values():
        btn.draw(surf, font)

    mm_x  = int(SW * 0.62)
    mm_y  = VIEW_H + 4
    mm_s  = max(2, int(HUD_H * 0.82) // MAP_H)
    mm_w  = mm_s * MAP_W
    mm_h  = mm_s * MAP_H

    pygame.draw.rect(surf, (6, 4, 10), (mm_x - 3, mm_y - 3, mm_w + 6, mm_h + 6))
    for ry in range(MAP_H):
        for rx in range(MAP_W):
            col = (52, 48, 64) if MAP[ry][rx] == '#' else (14, 12, 20)
            pygame.draw.rect(surf, col, (mm_x + rx*mm_s, mm_y + ry*mm_s, mm_s, mm_s))

    for tc_, tr_ in TORCHES:
        pygame.draw.rect(surf, (200, 100, 10),
            (mm_x + tc_*mm_s + mm_s//3, mm_y + tr_*mm_s + mm_s//3,
             max(1, mm_s//2), max(1, mm_s//2)))

    pdx = int(player.x * mm_s)
    pdy = int(player.y * mm_s)
    pygame.draw.rect(surf, (90, 180, 240),
        (mm_x + pdx - mm_s//2, mm_y + pdy - mm_s//2, mm_s, mm_s))
    pygame.draw.line(surf, WHITE,
        (mm_x+pdx, mm_y+pdy),
        (mm_x+pdx + int(math.cos(player.angle)*mm_s*2),
         mm_y+pdy + int(math.sin(player.angle)*mm_s*2)), 1)

    pygame.draw.rect(surf, BTN_BD, (mm_x-3, mm_y-3, mm_w+6, mm_h+6), 2)
    pygame.draw.rect(surf, BTN_HL, (mm_x-5, mm_y-5, mm_w+10, mm_h+10), 1)


# ── draw_bar ──────────────────────────────────────────────────────────────────
def draw_bar(surf, x, y, cur, mx, w, h):
    seg_count = 20
    seg_w     = w // seg_count
    filled    = int(seg_count * cur / mx)
    ratio     = cur / mx
    for i in range(seg_count):
        sx_ = x + i * seg_w
        if ratio > 0.5:
            col = GREEN   if i < filled else (12, 40, 14)
        elif ratio > 0.25:
            col = GOLD    if i < filled else (40, 32, 8)
        else:
            col = RED_LT  if i < filled else (40, 10, 10)
        pygame.draw.rect(surf, col, (sx_ + 1, y + 1, max(1, seg_w - 2), h - 2))
    pygame.draw.rect(surf, GREY, (x, y, seg_count * seg_w, h), 2)


# ── Game Over Screen ──────────────────────────────────────────────────────────
def game_over_screen(surf, font, bfont, score):
    ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 195))
    surf.blit(ov, (0, 0))

    t1 = bfont.render("YOU DIED", True, RED_LT)
    t2 = font.render("Score: {}".format(score), True, GOLD)
    t3 = font.render("Tap ATK to restart", True, WHITE)

    box_x = SW//2 - t1.get_width()//2 - 20
    box_y = SH//2 - 100
    box_w = t1.get_width() + 40
    box_h = 130
    pygame.draw.rect(surf, (18, 4, 10),  (box_x, box_y, box_w, box_h))
    pygame.draw.rect(surf, RED_LT,      (box_x, box_y, box_w, box_h), 3)
    pygame.draw.rect(surf, (65, 16, 16),(box_x+3, box_y+3, box_w-6, box_h-6), 1)

    surf.blit(t1, (SW//2 - t1.get_width()//2, SH//2 - 90))
    surf.blit(t2, (SW//2 - t2.get_width()//2, SH//2))
    surf.blit(t3, (SW//2 - t3.get_width()//2, SH//2 + 50))


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    try:
        font  = pygame.font.SysFont("monospace", max(14, int(SW*0.035)), bold=True)
        bfont = pygame.font.SysFont("monospace", max(36, int(SW*0.10)),  bold=True)
        sfont = pygame.font.SysFont("monospace", max(11, int(SW*0.028)))
    except Exception:
        font = bfont = sfont = pygame.font.Font(None, 28)

    state = {
        'player'    : Player(),
        'enemies'   : [Enemy(x, y) for x, y in ENEMY_STARTS],
        'atk_flash' : 0,
    }
    buttons = make_buttons()
    zbuf    = [MAX_D] * RW
    t       = 0.0

    def do_attack():
        if state['player'].attack(state['enemies']):
            state['atk_flash'] = 8

    def handle_press(x, y, down):
        p = state['player']
        for name, btn in buttons.items():
            if btn.hit(x, y):
                btn.pressed = down
                if down:
                    if name == 'atk':
                        if not p.alive:
                            state['player']  = Player()
                            state['enemies'] = [Enemy(ex, ey) for ex, ey in ENEMY_STARTS]
                        else:
                            do_attack()
                p.move_fwd = buttons['fwd'].pressed
                p.move_bk  = buttons['bk'].pressed
                p.turn_l   = buttons['left'].pressed
                p.turn_r   = buttons['right'].pressed

    fingers = {}

    while True:
        dt  = clock.tick(60) / 1000.0
        t  += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()

            if event.type == pygame.FINGERDOWN:
                fx = int(event.x * SW)
                fy = int(event.y * SH)
                fingers[event.finger_id] = (fx, fy)
                handle_press(fx, fy, True)

            if event.type == pygame.FINGERUP:
                if event.finger_id in fingers:
                    fx, fy = fingers.pop(event.finger_id)
                    handle_press(fx, fy, False)

            if event.type == pygame.FINGERMOTION:
                if event.finger_id in fingers:
                    ox, oy = fingers[event.finger_id]
                    handle_press(ox, oy, False)
                fx = int(event.x * SW)
                fy = int(event.y * SH)
                fingers[event.finger_id] = (fx, fy)
                handle_press(fx, fy, True)

            if event.type == pygame.MOUSEBUTTONDOWN:
                handle_press(*event.pos, True)
            if event.type == pygame.MOUSEBUTTONUP:
                handle_press(*event.pos, False)

        player  = state['player']
        enemies = state['enemies']

        player.update(enemies)
        for e in enemies:
            e.update(player)

        if player.alive and all(not e.alive for e in enemies):
            state['enemies'] = [Enemy(x, y) for x, y in ENEMY_STARTS]
            player.score += 50

        if state['atk_flash'] > 0:
            state['atk_flash'] -= 1

        draw_view(render_surf, player, enemies, zbuf, t)

        pygame.transform.scale(render_surf, (SW, VIEW_H),
                               screen.subsurface((0, 0, SW, VIEW_H)))

        draw_hud_panel(screen, player, buttons, font, sfont)

        if state['atk_flash'] > 0:
            hbtn = buttons['atk']
            rf   = hbtn.r + 7
            pygame.draw.rect(screen, GOLD,
                (hbtn.cx - rf, hbtn.cy - rf, rf*2, rf*2), 3)

        if not player.alive:
            game_over_screen(screen, font, bfont, player.score)

        pygame.display.flip()


if __name__ == "__main__":
    main()
