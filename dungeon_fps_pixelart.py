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

# ── Palette — Dark Stone Dungeon ──────────────────────────────────────────────
SKY     = (10,  12,  14)   # near-black cool stone ceiling
GROUND  = (14,  15,  16)   # near-black cool stone floor
WALL_N  = (52,  56,  60)   # north: cool mid gray stone
WALL_S  = (30,  33,  36)   # south: dark shadowed stone
WALL_E  = (72,  78,  84)   # east:  lighter stone (lit face)
WALL_W  = (44,  48,  52)   # west:  medium stone
MORTAR  = ( 8,   8,   9)   # near-black stone mortar
TORCH_C = (255, 130,  18)  # amber torch flame
GOLD    = (220, 180,  40)  # pixel gold
RED_LT  = (220,  40,  40)  # vivid red
GREEN   = ( 28, 200,  52)  # vivid green
GREY    = (110, 118, 128)  # cool gray text
WHITE   = (220, 225, 230)  # cool near-white
BLACK   = (  0,   0,   0)
BTN_BG  = ( 12,  13,  15)  # button background
BTN_BD  = ( 65,  68,  72)  # button border — stone gray
BTN_HL  = ( 90,  95, 100)  # button highlight

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
        pygame.draw.rect(surf, (4, 4, 5), (rx_ + 4, ry_ + 4, rw_, rh_))
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

    # ── Ceiling — near-black stone ──
    surf.fill(SKY, (0, 0, RW, HALF_H))
    # Subtle lighter band near horizon (ambient stone glow)
    pygame.draw.rect(surf, (16, 18, 20), (0, HALF_H - HALF_H//6, RW, HALF_H//6))

    # ── Floor — dark stone with perspective tile lines ──
    surf.fill(GROUND, (0, HALF_H, RW, RH - HALF_H))
    tile_col = (GROUND[0]+10, GROUND[1]+11, GROUND[2]+12)
    for row_dist in [0.8, 1.2, 1.8, 2.6, 3.8, 5.5, 8.0, 12.0]:
        proj_y = int(HALF_H + (RH - HALF_H) * 0.45 / (row_dist * 0.5 + 0.001))
        proj_y = min(RH - 1, max(HALF_H + 1, proj_y))
        pygame.draw.line(surf, tile_col, (0, proj_y), (RW, proj_y), 1)

    # Torch flicker
    flicker = 1.0 + math.sin(t * 9.1) * 0.06 + math.sin(t * 17.3) * 0.04

    # Torch glow — player-position-based, subtle amber
    raw_glow = 0.0
    for (tc, tr) in TORCHES:
        td = math.hypot(player.x - tc, player.y - tr)
        raw_glow += max(0.0, (1.0 - td / 3.8) * flicker) * 0.4
    raw_glow = min(raw_glow, 0.5)

    # ── Brick constants ──
    BRICK_H  = 0.33   # brick height (3 rows per world-unit wall)
    BRICK_W  = 0.50   # brick width (2 per face)
    MORT_AMT = 32     # mortar darkening amount

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
        shade   = max(0.05, 1.0 - corr / MAX_D)
        shade_q = round(shade * SHADE_STEPS) / SHADE_STEPS

        # Subtle torch amber tint
        glow_q = round(raw_glow * SHADE_STEPS) / SHADE_STEPS
        r = min(int(base[0] * shade_q + TORCH_C[0] * glow_q * 0.15), 255)
        g = min(int(base[1] * shade_q + TORCH_C[1] * glow_q * 0.06), 255)
        b = min(int(base[2] * shade_q), 255)

        # Vertical mortar seam from hit_frac
        seam = hit_frac % BRICK_W
        is_v_seam = seam < 0.032 or seam > (BRICK_W - 0.032)
        if is_v_seam:
            r = max(r - MORT_AMT, 0)
            g = max(g - MORT_AMT, 0)
            b = max(b - MORT_AMT, 0)

        wall_col = (r, g, b)
        mort_col = (max(r - MORT_AMT, 0), max(g - MORT_AMT, 0), max(b - MORT_AMT, 0))

        # Solid wall strip
        pygame.draw.rect(surf, wall_col, (col_i, top, 1, wall_h))

        # Horizontal mortar lines (brick rows)
        if wall_h > 5:
            brick_h_px = max(3, int(wall_h * BRICK_H))
            offset = int(hit_frac * brick_h_px * 1.7) % brick_h_px
            by_m = top + (brick_h_px - offset) % brick_h_px
            while by_m < top + wall_h:
                if 0 <= by_m < RH:
                    surf.set_at((col_i, by_m), mort_col)
                by_m += brick_h_px

        # Ambient occlusion at wall top/bottom edges
        if wall_h > 10:
            ao_h = max(1, wall_h // 10)
            ao_c = (max(r-58, 0), max(g-52, 0), max(b-52, 0))
            pygame.draw.rect(surf, ao_c, (col_i, top, 1, ao_h))
            pygame.draw.rect(surf, ao_c, (col_i, top + wall_h - ao_h, 1, ao_h))

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
        skin_raw = (255, 80, 80) if is_hit else (180, 165, 142)
        skin_col = tuple(int(c * sshade) for c in skin_raw)
        robe_col = tuple(int(c * sshade) for c in (26, 22, 18))
        robe_drk = tuple(int(c * sshade) for c in (12, 10, 8))
        eye_col  = (min(int(215*sshade), 255), min(int(75*sshade), 255), 0)

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
            hood = tuple(max(c-70, 0) for c in skin_col)
            pygame.draw.rect(surf, hood, (hxc, hy_, hwc, head_h // 2))
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
                    sc_ = (180, 40, 40) if si < filled else (26, 8, 8)
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
        pygame.draw.rect(surf, (72, 46, 18),
            (stick_x, sty + proj_ht//2, stick_w, max(1, proj_ht//2)))

        flame_h = max(1, proj_ht // 2)
        for fi in range(flame_h):
            ratio = fi / max(flame_h, 1)
            fr    = min(255, int(255 * flick_v))
            fg    = min(255, int((128 - 80*ratio) * flick_v))
            fw    = max(1, int(proj_wt * (1.0 - ratio * 0.55)))
            fxs   = stx + (proj_wt - fw) // 2
            if 0 <= fxs < RW and 0 <= sty + fi < RH:
                pygame.draw.rect(surf, (fr, fg, 12), (fxs, sty + fi, fw, 1))

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

    # Blade — aged iron
    pygame.draw.rect(surf, (105, 100, 88), (blade_x, by_sw, blade_w, blade_h))
    pygame.draw.rect(surf, (185, 178, 158),
        (blade_x + blade_w//3, by_sw + 2, max(1, blade_w//3), blade_h - 4))
    pygame.draw.rect(surf, (58, 54, 46), (blade_x, by_sw, 1, blade_h))
    pygame.draw.rect(surf, (58, 54, 46), (blade_x + blade_w - 1, by_sw, 1, blade_h))

    # Cross-guard — bronze
    gw = sw_w
    pygame.draw.rect(surf, (95, 72, 32),   (bx_sw, guard_y, gw, guard_h))
    pygame.draw.rect(surf, (138, 104, 48), (bx_sw, guard_y, gw, 2))
    pygame.draw.rect(surf, (50, 36, 14),   (bx_sw, guard_y + guard_h - 2, gw, 2))

    # Grip — dark leather
    pygame.draw.rect(surf, (58, 36, 16), (grip_x, grip_y, grip_w, grip_h))
    wrap_step = max(2, grip_h // 4)
    for gi in range(0, grip_h, wrap_step):
        pygame.draw.line(surf, (36, 22, 8),
            (grip_x, grip_y+gi), (grip_x+grip_w, grip_y+gi), 1)

    # Pommel
    pom_w = grip_w + 4
    pom_h = max(3, grip_h // 3)
    pygame.draw.rect(surf, (110, 82, 36), (grip_x - 2, grip_y + grip_h, pom_w, pom_h))

    # ── Damage flash vignette ──
    if player.flash > 0:
        alpha = int(player.flash / 15 * 120)
        vsurf = pygame.Surface((RW, RH), pygame.SRCALPHA)
        vsurf.fill((180, 20, 20, alpha))
        surf.blit(vsurf, (0, 0))


# ── draw_hud_panel ────────────────────────────────────────────────────────────
def draw_hud_panel(surf, player, buttons, font, sfont):
    pygame.draw.rect(surf, (8, 9, 10), (0, VIEW_H, SW, HUD_H))
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
    pygame.draw.rect(surf, (4, 5, 6),
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

    pygame.draw.rect(surf, (4, 5, 6), (mm_x - 3, mm_y - 3, mm_w + 6, mm_h + 6))
    for ry in range(MAP_H):
        for rx in range(MAP_W):
            col = (58, 62, 66) if MAP[ry][rx] == '#' else (14, 15, 16)
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
    pygame.draw.rect(surf, (14, 4, 4),  (box_x, box_y, box_w, box_h))
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
