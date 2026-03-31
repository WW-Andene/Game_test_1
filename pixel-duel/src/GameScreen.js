/**
 * PIXEL DUEL — GameScreen.js
 *
 * Gestures:
 *   Tap                   → Basic attack
 *   Swipe (any dir)       → Dash
 *   Two quick swipes      → Slash attack (moving projectile, passes through)
 *   Swipe → hold → release→ Thrust (lunge, pogo bounce off enemy)
 *
 * Web keyboard (bonus):
 *   A/D or ←/→  Move      Z  Basic attack
 *   W or ↑      Jump      X  Thrust        C  Slash
 */

import React, { useRef, useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, PanResponder, Dimensions, Platform,
} from 'react-native';
import Svg, { Rect, G, Circle, Polygon } from 'react-native-svg';

// ─── SCREEN ──────────────────────────────────────────────────────────────────
const { width: SW, height: SH } = Dimensions.get('window');

// ─── PIXEL ART ───────────────────────────────────────────────────────────────
const PS   = 5;        // real pixels per sprite-pixel
const SPW  = 8;        // sprite width  in sprite-pixels
const SPH  = 12;       // sprite height in sprite-pixels
const CW   = SPW * PS; // character width  = 40 real px
const CH   = SPH * PS; // character height = 60 real px

// ─── WORLD ───────────────────────────────────────────────────────────────────
const GW      = SW;
const GH      = SH;
const FLOOR_Y = GH * 0.78;      // y where characters' feet rest
const WALL_L  = 5;
const WALL_R  = GW - CW - 5;
const SKY_H   = FLOOR_Y;

// ─── PHYSICS ─────────────────────────────────────────────────────────────────
const GRAVITY    = 0.55;
const FRIC_GND   = 0.82;
const FRIC_AIR   = 0.96;

// ─── COMBAT ──────────────────────────────────────────────────────────────────
const DASH_SPD    = 15;
const DASH_FRAMES = 13;

const ATK_BASIC  = { dmg: 12, kbX:  9, kbY:  -3, range: CW * 1.6, dur: 22, window: [5, 15] };
const ATK_SLASH  = { dmg: 20, kbX: 13, kbY:  -6, speed: 10,        dur: 38 };
const ATK_THRUST = { dmg: 28, kbX:  0, kbY: -15, lunge: 16,        dur: 14 };

const EN_SPEED    = 1.4;
const EN_ATK_DIST = CW * 1.9;
const EN_ATK_CD   = 85;
const EN_ATK_DMG  = 14;
const EN_ATK_DUR  = 32;

// ─── GESTURE THRESHOLDS ──────────────────────────────────────────────────────
const SWIPE_MIN    = 28;   // px minimum to register swipe
const SWIPE_MAX_MS = 340;  // swipe must start within this time
const DOUBLE_MS    = 430;  // max gap between two swipes → slash
const HOLD_MS      = 370;  // hold after swipe → thrust
const TAP_MAX_PX   = 14;   // max drift to count as tap

// ─── COLOUR PALETTE ──────────────────────────────────────────────────────────
const PAL = {
  '.': null,
  // Hero
  'H': '#2D1B00',  // dark hair
  'S': '#F5C19E',  // skin
  'k': '#111111',  // dark outline / eyes
  'J': '#3B82F6',  // jacket blue
  'j': '#1E40AF',  // jacket shadow
  'W': '#D1D5DB',  // sword silver
  'G': '#F59E0B',  // gold guard
  'P': '#1E293B',  // pants
  // Enemy
  'R': '#EF4444',  // red
  'r': '#B91C1C',  // dark red
  'E': '#FECACA',  // highlight/skin
  'D': '#7F1D1D',  // deep red
};

// ─── SPRITES (8 × 12, each char = colour key) ────────────────────────────────
// Hero faces RIGHT by default; flip horizontally when facing left.
const HERO_ROWS = [
  '..HHHH..',
  '.HSSSSH.',
  '.HSkSSH.',
  '.HSSSSWk',
  '.kSSSSWG',
  '.JjJJGk.',
  'jJjjJJk.',
  'jJjjJJk.',
  '.JjJJk..',
  '.kPPPk..',
  '.kPPPk..',
  '.kk.kk..',
];

// Enemy also defined facing RIGHT; flip when facing left.
const ENEMY_ROWS = [
  '..RRRR..',
  '.kRrErk.',
  '.kRkEkk.',
  '.kRrErk.',
  '..kRRk..',
  '.DRRRRk.',
  'DRRRRRRk',
  'DRRRRRRk',
  '.DRRRRk.',
  '.kRRkRk.',
  '.kRRkRk.',
  '.kk.kk..',
];

// ─── SPRITE RENDERER ─────────────────────────────────────────────────────────
function renderSprite(rows, x, y, flipX) {
  const out = [];
  for (let row = 0; row < rows.length; row++) {
    const str = rows[row];
    for (let col = 0; col < str.length; col++) {
      const color = PAL[str[col]];
      if (!color) continue;
      const drawCol = flipX ? (SPW - 1 - col) : col;
      out.push(
        <Rect
          key={`${row}-${col}`}
          x={x + drawCol * PS}
          y={y + row  * PS}
          width={PS}
          height={PS}
          fill={color}
        />
      );
    }
  }
  return out;
}

// ─── INITIAL GAME STATE ───────────────────────────────────────────────────────
function mkPlayer() {
  return {
    x: WALL_L + 30, y: FLOOR_Y - CH,
    vx: 0, vy: 0,
    onGround: true,
    facing: 1,              // 1 = right, -1 = left
    state: 'idle',          // idle | dash | attack | slash | thrust | hurt
    stateTimer: 0,
    dashDir: { x: 1, y: 0 },
    dashTimer: 0,
    atkActive: false,       // hitbox is hot
    slashOn: false,
    slashX: 0, slashY: 0,
    slashVx: 0, slashVy: 0,
    slashTimer: 0,
    slashHit: false,        // slash can hit once; stays on screen
    hp: 100, maxHp: 100,
    invincible: 0,
  };
}

function mkEnemy() {
  return {
    x: WALL_R - 30, y: FLOOR_Y - CH,
    vx: 0, vy: 0,
    onGround: true,
    facing: -1,
    state: 'walk',          // walk | attack | hurt | stagger | launched | grounded
    stateTimer: 0,
    atkCd: EN_ATK_CD,
    hp: 150, maxHp: 150,
    invincible: 0,
  };
}

function mkGame() {
  return {
    player: mkPlayer(),
    enemy: mkEnemy(),
    effects: [],
    stars: Array.from({ length: 40 }, () => ({
      x: Math.random() * GW,
      y: Math.random() * SKY_H * 0.85,
      r: Math.random() < 0.3 ? 2 : 1,
    })),
    frame: 0,
    gameOver: false,
    winner: null,
  };
}

// ─── HELPERS ─────────────────────────────────────────────────────────────────
function angleToDir(angle) {
  const snap = Math.round(angle / (Math.PI / 4)) * (Math.PI / 4);
  return {
    x: Math.round(Math.cos(snap)),
    y: Math.round(Math.sin(snap)),
  };
}

function spawnHit(gs, x, y) {
  for (let i = 0; i < 9; i++) {
    const angle = (Math.PI * 2 * i) / 9 + Math.random() * 0.4;
    const speed = 2 + Math.random() * 3;
    gs.effects.push({
      x, y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 2,
      life: 18, maxLife: 18,
      color: i % 2 === 0 ? '#FDE047' : '#F97316',
      size: 4,
    });
  }
}

function spawnDust(gs, x, y) {
  for (let i = 0; i < 5; i++) {
    gs.effects.push({
      x: x + (Math.random() - 0.5) * CW,
      y,
      vx: (Math.random() - 0.5) * 3,
      vy: -Math.random() * 2,
      life: 14, maxLife: 14,
      color: '#9CA3AF',
      size: 3,
    });
  }
}

// ─── HIT ENEMY ───────────────────────────────────────────────────────────────
function hitEnemy(gs, atk, playerFacing) {
  const EN = gs.enemy;
  if (EN.invincible > 0 || EN.hp <= 0) return false;

  EN.hp = Math.max(0, EN.hp - atk.dmg);
  EN.invincible = 28;
  EN.vx = playerFacing * atk.kbX;
  EN.vy = atk.kbY;

  if (atk.kbY < -12) {
    EN.state = 'launched';
    EN.onGround = false;
  } else if (atk.kbX > 12) {
    EN.state = 'stagger';
    EN.stateTimer = 35;
  } else {
    EN.state = 'hurt';
    EN.stateTimer = 18;
  }

  spawnHit(gs, EN.x + CW / 2, EN.y + CH / 3);
  return true;
}

// ─── APPLY GESTURE ───────────────────────────────────────────────────────────
function applyGesture(gs, gesture) {
  if (!gesture) return;
  const P = gs.player;

  // Game over: any tap restarts
  if (gs.gameOver) {
    if (gesture.type === 'tap') Object.assign(gs, mkGame());
    return;
  }

  // Can't start new attack during active attack (dash can always interrupt)
  if (gesture.type !== 'dash' && ['attack', 'slash', 'thrust'].includes(P.state)) return;

  switch (gesture.type) {

    case 'tap':
      P.state = 'attack';
      P.stateTimer = ATK_BASIC.dur;
      P.atkActive = false; // activated mid-animation below
      break;

    case 'dash':
      if (['attack', 'slash'].includes(P.state)) return;
      P.state = 'dash';
      P.dashDir = gesture.dir;
      P.dashTimer = DASH_FRAMES;
      if (gesture.dir.x !== 0) P.facing = gesture.dir.x;
      break;

    case 'slash': {
      P.state = 'slash';
      P.stateTimer = ATK_SLASH.dur;
      const dir = gesture.dir;
      const dirX = dir.x !== 0 ? dir.x : P.facing;
      const dirY = dir.y;
      const mag = Math.hypot(dirX, dirY) || 1;
      P.slashOn  = true;
      P.slashX   = P.x + (P.facing > 0 ? CW + 5 : -5);
      P.slashY   = P.y + CH * 0.3;
      P.slashVx  = (dirX / mag) * ATK_SLASH.speed;
      P.slashVy  = (dirY / mag) * ATK_SLASH.speed;
      P.slashTimer = ATK_SLASH.dur;
      P.slashHit = false;
      if (dirX !== 0) P.facing = dirX;
      break;
    }

    case 'thrust': {
      P.state = 'thrust';
      P.stateTimer = ATK_THRUST.dur;
      const tDirX = gesture.dir.x !== 0 ? gesture.dir.x : P.facing;
      const tDirY = gesture.dir.y;
      const tMag  = Math.hypot(tDirX, tDirY) || 1;
      P.vx = (tDirX / tMag) * ATK_THRUST.lunge;
      P.vy = (tDirY / tMag) * ATK_THRUST.lunge * 0.4 - 5;
      P.onGround = false;
      if (tDirX !== 0) P.facing = tDirX;
      break;
    }
  }
}

// ─── MAIN UPDATE ─────────────────────────────────────────────────────────────
function updateGame(gs, gesture, keysHeld) {
  if (gs.gameOver) {
    applyGesture(gs, gesture);
    return;
  }

  gs.frame++;
  const P  = gs.player;
  const EN = gs.enemy;

  // ── Apply gesture ─────────────────────────────────────────────────────────
  applyGesture(gs, gesture);

  // ── Keyboard movement (web) ───────────────────────────────────────────────
  if (keysHeld && keysHeld.size > 0) {
    const movL = keysHeld.has('arrowleft')  || keysHeld.has('a');
    const movR = keysHeld.has('arrowright') || keysHeld.has('d');
    const jump = keysHeld.has('arrowup')    || keysHeld.has('w');
    if (!['attack','slash','thrust'].includes(P.state)) {
      if (movL) { P.vx = -8; P.facing = -1; }
      if (movR) { P.vx =  8; P.facing =  1; }
    }
    if (jump && P.onGround) { P.vy = -11; P.onGround = false; }
  }

  // ════════════════════ PLAYER ════════════════════════════════════════════════

  // Dash override velocity
  if (P.dashTimer > 0) {
    P.dashTimer--;
    P.vx = P.dashDir.x * DASH_SPD;
    if (P.dashDir.y < 0) P.vy = P.dashDir.y * DASH_SPD * 0.55;
    if (P.dashTimer === 0 && P.state === 'dash') P.state = 'idle';
  }

  // Gravity
  if (!P.onGround) P.vy += GRAVITY;

  P.x += P.vx;
  P.y += P.vy;

  // Ground
  if (P.y >= FLOOR_Y - CH) {
    P.y = FLOOR_Y - CH;
    P.vy = 0;
    P.onGround = true;
  } else {
    P.onGround = false;
  }

  // Walls
  P.x = Math.max(WALL_L, Math.min(WALL_R, P.x));

  // Friction
  P.vx *= P.onGround ? FRIC_GND : FRIC_AIR;
  if (Math.abs(P.vx) < 0.1) P.vx = 0;

  // State / attack timers
  if (P.stateTimer > 0) {
    P.stateTimer--;

    // Basic attack hit window
    if (P.state === 'attack') {
      const elapsed = ATK_BASIC.dur - P.stateTimer;
      P.atkActive = elapsed >= ATK_BASIC.window[0] && elapsed <= ATK_BASIC.window[1];
    }

    if (P.stateTimer === 0) {
      P.state    = 'idle';
      P.atkActive = false;
      P.slashOn  = false;
    }
  }

  if (P.invincible > 0) P.invincible--;

  // ── Slash projectile ──────────────────────────────────────────────────────
  if (P.slashOn) {
    P.slashX += P.slashVx;
    P.slashY += P.slashVy;
    P.slashTimer--;
    if (P.slashTimer <= 0) {
      P.slashOn = false;
    } else if (!P.slashHit && EN.invincible <= 0) {
      if (P.slashX > EN.x && P.slashX < EN.x + CW &&
          P.slashY > EN.y && P.slashY < EN.y + CH) {
        hitEnemy(gs, ATK_SLASH, P.facing);
        P.slashHit = true; // passes through — can only register once
      }
    }
  }

  // ── Basic attack hitbox ───────────────────────────────────────────────────
  if (P.state === 'attack' && P.atkActive && EN.invincible <= 0) {
    const atkL = P.facing > 0 ? P.x + CW         : P.x - ATK_BASIC.range;
    const atkR = P.facing > 0 ? P.x + CW + ATK_BASIC.range : P.x;
    if (atkR > EN.x && atkL < EN.x + CW &&
        P.y + CH * 0.7 > EN.y && P.y + CH * 0.2 < EN.y + CH) {
      hitEnemy(gs, ATK_BASIC, P.facing);
      P.atkActive = false;
    }
  }

  // ── Thrust collision ──────────────────────────────────────────────────────
  if (P.state === 'thrust' && EN.invincible <= 0) {
    if (Math.abs(P.x - EN.x) < CW * 1.3 && Math.abs(P.y - EN.y) < CH * 0.9) {
      hitEnemy(gs, ATK_THRUST, P.facing);
      // Pogo bounce: player rebounds in opposite direction
      P.vx = -P.facing * 11;
      P.vy = -9;
      P.state    = 'idle';
      P.stateTimer = 0;
    }
  }

  // ════════════════════ ENEMY ═════════════════════════════════════════════════

  if (!EN.onGround) EN.vy += GRAVITY;

  EN.x += EN.vx;
  EN.y += EN.vy;

  // Ground
  if (EN.y >= FLOOR_Y - CH) {
    EN.y = FLOOR_Y - CH;
    if (EN.state === 'launched' && Math.abs(EN.vy) > 5) {
      // Street-of-Rage bounce on landing
      EN.vy = -Math.abs(EN.vy) * 0.42;
      EN.vx *= 0.65;
      spawnDust(gs, EN.x + CW / 2, FLOOR_Y);
    } else {
      EN.vy = 0;
      EN.onGround = true;
      if (EN.state === 'launched') {
        EN.state = 'grounded';
        EN.stateTimer = 52;
        spawnDust(gs, EN.x + CW / 2, FLOOR_Y);
      }
    }
  } else {
    EN.onGround = false;
  }

  // Walls — bounce back
  if (EN.x < WALL_L) { EN.x = WALL_L; EN.vx =  Math.abs(EN.vx) * 0.4; }
  if (EN.x > WALL_R) { EN.x = WALL_R; EN.vx = -Math.abs(EN.vx) * 0.4; }

  EN.vx *= EN.onGround ? FRIC_GND : FRIC_AIR;
  if (EN.invincible > 0) EN.invincible--;

  // ── Enemy AI (Street-of-Rage style) ──────────────────────────────────────
  switch (EN.state) {
    case 'walk': {
      if (!EN.onGround) break;
      const dx = P.x - EN.x;
      EN.facing = dx > 0 ? 1 : -1;
      EN.vx = EN.facing * EN_SPEED;
      if (EN.atkCd > 0) EN.atkCd--;
      if (Math.abs(dx) < EN_ATK_DIST && EN.atkCd <= 0) {
        EN.state = 'attack';
        EN.stateTimer = EN_ATK_DUR;
        EN.atkCd = EN_ATK_CD;
      }
      break;
    }
    case 'attack': {
      EN.vx *= 0.7;
      // Hit window: midpoint of attack animation
      const hitFrame = Math.floor(EN_ATK_DUR * 0.4);
      if (EN.stateTimer === hitFrame && P.invincible <= 0) {
        const dx = Math.abs(EN.x - P.x);
        if (dx < EN_ATK_DIST * 1.2) {
          P.hp = Math.max(0, P.hp - EN_ATK_DMG);
          P.vx = -EN.facing * 9;
          P.vy = -5;
          P.onGround  = false;
          P.invincible = 42;
          spawnHit(gs, P.x + CW / 2, P.y + CH / 3);
        }
      }
      EN.stateTimer--;
      if (EN.stateTimer <= 0) EN.state = 'walk';
      break;
    }
    case 'hurt':
    case 'stagger':
      EN.stateTimer--;
      if (EN.stateTimer <= 0) EN.state = 'walk';
      break;
    case 'launched':
      break; // pure physics in the air
    case 'grounded':
      EN.vx *= 0.78;
      EN.stateTimer--;
      if (EN.stateTimer <= 0) EN.state = 'walk';
      break;
  }

  // ── Effects ───────────────────────────────────────────────────────────────
  gs.effects = gs.effects
    .map(e => ({
      ...e,
      x: e.x + e.vx,
      y: e.y + e.vy,
      vy: e.vy + 0.25,
      life: e.life - 1,
    }))
    .filter(e => e.life > 0);

  // ── Win/lose ──────────────────────────────────────────────────────────────
  if (!gs.gameOver) {
    if (EN.hp <= 0) { gs.gameOver = true; gs.winner = 'player'; }
    if (P.hp  <= 0) { gs.gameOver = true; gs.winner = 'enemy';  }
  }
}

// ─── COMPONENT ───────────────────────────────────────────────────────────────
export default function GameScreen() {
  const gsRef        = useRef(mkGame());
  const keysHeld     = useRef(new Set());
  const [tick, setTick] = useState(0);
  const gestQ        = useRef([]);

  const enqueue = useCallback((g) => { gestQ.current.push(g); }, []);

  // ── Game loop ─────────────────────────────────────────────────────────────
  useEffect(() => {
    let raf;
    let lastT = performance.now();

    const loop = (t) => {
      const dt = t - lastT;
      if (dt >= 14) {
        lastT = t;
        const gesture = gestQ.current.shift() || null;
        updateGame(gsRef.current, gesture, keysHeld.current);
        setTick(n => n + 1);
      }
      raf = requestAnimationFrame(loop);
    };

    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  // ── Keyboard controls (web) ───────────────────────────────────────────────
  useEffect(() => {
    if (Platform.OS !== 'web') return;

    const onDown = (e) => {
      const key = e.key.toLowerCase();
      keysHeld.current.add(key);
      if (key === 'z') enqueue({ type: 'tap' });
      if (key === 'x') enqueue({ type: 'thrust', dir: { x: gsRef.current.player.facing, y: 0 } });
      if (key === 'c') enqueue({ type: 'slash',  dir: { x: gsRef.current.player.facing, y: 0 } });
    };
    const onUp = (e) => keysHeld.current.delete(e.key.toLowerCase());

    window.addEventListener('keydown', onDown);
    window.addEventListener('keyup',   onUp);
    return () => {
      window.removeEventListener('keydown', onDown);
      window.removeEventListener('keyup',   onUp);
    };
  }, [enqueue]);

  // ── PanResponder (touch) ──────────────────────────────────────────────────
  const grRef = useRef({
    startX: 0, startY: 0, startTime: 0,
    moved: false, totalDx: 0, totalDy: 0,
    swipeDir: null,
    thrustReady: false,
    holdTimeout: null,
    lastSwipeTime: 0,
  });

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder:  () => true,

      onPanResponderGrant: (_, g) => {
        const gr = grRef.current;
        gr.startX    = g.x0;
        gr.startY    = g.y0;
        gr.startTime = Date.now();
        gr.moved      = false;
        gr.totalDx    = 0;
        gr.totalDy    = 0;
        gr.swipeDir   = null;
        gr.thrustReady = false;
        if (gr.holdTimeout) { clearTimeout(gr.holdTimeout); gr.holdTimeout = null; }
      },

      onPanResponderMove: (_, g) => {
        const gr = grRef.current;
        gr.totalDx = g.dx;
        gr.totalDy = g.dy;
        const dist = Math.hypot(g.dx, g.dy);

        if (!gr.moved && dist >= SWIPE_MIN) {
          const elapsed = Date.now() - gr.startTime;
          if (elapsed < SWIPE_MAX_MS) {
            gr.moved    = true;
            gr.swipeDir = angleToDir(Math.atan2(g.dy, g.dx));
            // Hold timer: if finger stays down after swipe → thrust
            gr.holdTimeout = setTimeout(() => {
              gr.thrustReady  = true;
              gr.holdTimeout  = null;
            }, HOLD_MS);
          }
        }
      },

      onPanResponderRelease: () => {
        const gr = grRef.current;
        if (gr.holdTimeout) { clearTimeout(gr.holdTimeout); gr.holdTimeout = null; }

        const dist = Math.hypot(gr.totalDx, gr.totalDy);

        if (!gr.moved && dist < TAP_MAX_PX) {
          // ── TAP ──
          enqueue({ type: 'tap' });
          gr.lastSwipeTime = 0;

        } else if (gr.moved && gr.swipeDir) {

          if (gr.thrustReady) {
            // ── SWIPE + HOLD + RELEASE → thrust ──
            enqueue({ type: 'thrust', dir: gr.swipeDir });
            gr.lastSwipeTime = 0;

          } else {
            const now = Date.now();
            if (gr.lastSwipeTime > 0 && now - gr.lastSwipeTime < DOUBLE_MS) {
              // ── DOUBLE SWIPE → slash ──
              enqueue({ type: 'slash', dir: gr.swipeDir });
              gr.lastSwipeTime = 0;
            } else {
              // ── SINGLE SWIPE → dash ──
              enqueue({ type: 'dash', dir: gr.swipeDir });
              gr.lastSwipeTime = now;
            }
          }
        }

        gr.moved       = false;
        gr.swipeDir    = null;
        gr.thrustReady = false;
      },

      onPanResponderTerminate: () => {
        const gr = grRef.current;
        if (gr.holdTimeout) { clearTimeout(gr.holdTimeout); gr.holdTimeout = null; }
      },
    })
  ).current;

  // ─── RENDER ──────────────────────────────────────────────────────────────
  const gs = gsRef.current;
  const P  = gs.player;
  const EN = gs.enemy;
  const pFlash = P.invincible > 0 && P.invincible % 4 < 2;
  const eFlash = EN.invincible > 0 && EN.invincible % 4 < 2;

  // Slash trail colours cycle
  const slashCol = gs.frame % 6 < 3 ? '#FDE047' : '#FFFFFF';

  return (
    <View style={styles.root} {...panResponder.panHandlers}>
      <Svg width={GW} height={GH} style={StyleSheet.absoluteFill}>

        {/* ── Sky ── */}
        <Rect x={0} y={0} width={GW} height={GH} fill="#0F172A" />

        {/* ── Stars ── */}
        {gs.stars.map((s, i) => (
          <Rect key={i} x={s.x} y={s.y} width={s.r} height={s.r} fill="#E2E8F0" opacity={0.5} />
        ))}

        {/* ── Background buildings (pixel art) ── */}
        {[0.12, 0.28, 0.54, 0.70, 0.88].map((rx, i) => {
          const bx = rx * GW;
          const bh = 60 + (i % 3) * 30;
          const by = FLOOR_Y - bh;
          const bw = 28 + (i % 2) * 18;
          return (
            <G key={i}>
              <Rect x={bx} y={by} width={bw} height={bh} fill="#1E293B" />
              {/* windows */}
              {[0, 1, 2].map(row =>
                [0, 1].map(col => (
                  <Rect
                    key={`${row}-${col}`}
                    x={bx + 4 + col * 10}
                    y={by + 6 + row * 14}
                    width={6} height={6}
                    fill={gs.frame % 120 < 60 + i * 10 ? '#FBBF24' : '#334155'}
                    opacity={0.8}
                  />
                ))
              )}
            </G>
          );
        })}

        {/* ── Ground ── */}
        <Rect x={0} y={FLOOR_Y} width={GW} height={GH - FLOOR_Y} fill="#1F2937" />
        <Rect x={0} y={FLOOR_Y} width={GW} height={3} fill="#4B5563" />
        {/* ground texture lines */}
        {Array.from({ length: Math.ceil(GW / 30) }).map((_, i) => (
          <Rect key={i} x={i * 30} y={FLOOR_Y + 3} width={15} height={1} fill="#374151" />
        ))}

        {/* ── Particle effects ── */}
        {gs.effects.map((ef, i) => (
          <Rect
            key={i}
            x={ef.x - ef.size / 2}
            y={ef.y - ef.size / 2}
            width={ef.size}
            height={ef.size}
            fill={ef.color}
            opacity={ef.life / ef.maxLife}
          />
        ))}

        {/* ── Slash projectile ── */}
        {P.slashOn && (
          <G>
            {/* horizontal bar */}
            <Rect x={P.slashX - 12} y={P.slashY - 2} width={24} height={4} fill={slashCol} opacity={0.9} />
            {/* vertical bar */}
            <Rect x={P.slashX - 2} y={P.slashY - 12} width={4} height={24} fill={slashCol} opacity={0.9} />
            {/* centre glow */}
            <Rect x={P.slashX - 5} y={P.slashY - 5} width={10} height={10} fill="#FFFFFF" opacity={0.7} />
          </G>
        )}

        {/* ── Player ── */}
        <G opacity={pFlash ? 0.35 : 1}>
          {renderSprite(HERO_ROWS, P.x, P.y, P.facing < 0)}
          {/* Basic attack flash */}
          {P.state === 'attack' && P.atkActive && (
            <Rect
              x={P.facing > 0 ? P.x + CW : P.x - CW * 0.9}
              y={P.y + CH * 0.2}
              width={CW * 0.9}
              height={CH * 0.45}
              fill="#FDE047"
              opacity={0.45}
            />
          )}
          {/* Thrust lunge glow */}
          {P.state === 'thrust' && (
            <Rect
              x={P.facing > 0 ? P.x + CW * 0.5 : P.x - CW * 0.5}
              y={P.y + CH * 0.1}
              width={CW * 0.6}
              height={CH * 0.6}
              fill="#60A5FA"
              opacity={0.35}
            />
          )}
        </G>

        {/* ── Enemy ── */}
        <G opacity={eFlash ? 0.35 : 1}>
          {renderSprite(ENEMY_ROWS, EN.x, EN.y, EN.facing > 0)}
          {/* Enemy attack flash */}
          {EN.state === 'attack' && EN.stateTimer < EN_ATK_DUR - 5 && EN.stateTimer > 8 && (
            <Rect
              x={EN.facing > 0 ? EN.x + CW : EN.x - CW * 0.9}
              y={EN.y + CH * 0.2}
              width={CW * 0.9}
              height={CH * 0.45}
              fill="#EF4444"
              opacity={0.35}
            />
          )}
        </G>

      </Svg>

      {/* ── HP Bars (View overlay) ── */}
      <View style={styles.hud}>
        <View style={styles.hpGroup}>
          <Text style={[styles.hpLabel, { color: '#60A5FA' }]}>YOU</Text>
          <View style={styles.hpTrack}>
            <View style={[styles.hpBar, {
              width: `${(P.hp / P.maxHp) * 100}%`,
              backgroundColor: P.hp > 50 ? '#22C55E' : P.hp > 25 ? '#F59E0B' : '#EF4444',
            }]} />
          </View>
          <Text style={styles.hpNum}>{P.hp}</Text>
        </View>

        <Text style={styles.vs}>VS</Text>

        <View style={[styles.hpGroup, { alignItems: 'flex-end' }]}>
          <Text style={[styles.hpLabel, { color: '#F87171' }]}>ENEMY</Text>
          <View style={styles.hpTrack}>
            <View style={[styles.hpBar, {
              width: `${(EN.hp / EN.maxHp) * 100}%`,
              backgroundColor: '#EF4444',
              alignSelf: 'flex-end',
            }]} />
          </View>
          <Text style={styles.hpNum}>{EN.hp}</Text>
        </View>
      </View>

      {/* ── Controls hint ── */}
      {gs.frame < 180 && !gs.gameOver && (
        <View style={styles.hint}>
          <Text style={styles.hintText}>TAP attack  ·  SWIPE dash  ·  2× SWIPE slash  ·  SWIPE+HOLD thrust</Text>
          {Platform.OS === 'web' && (
            <Text style={styles.hintText}>⌨  A/D move  ·  W jump  ·  Z attack  ·  X thrust  ·  C slash</Text>
          )}
        </View>
      )}

      {/* ── Game Over screen ── */}
      {gs.gameOver && (
        <View style={styles.overlay}>
          <Text style={styles.goTitle}>
            {gs.winner === 'player' ? '⚔  YOU WIN!' : '💀  GAME OVER'}
          </Text>
          <Text style={styles.goSub}>TAP TO RESTART</Text>
        </View>
      )}
    </View>
  );
}

// ─── STYLES ──────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0F172A' },

  hud: {
    position: 'absolute',
    top: 10, left: 12, right: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  hpGroup:  { width: '42%' },
  hpLabel:  { fontSize: 10, fontFamily: Platform.OS === 'web' ? 'monospace' : 'Courier', fontWeight: 'bold', marginBottom: 3 },
  hpTrack:  { height: 8, backgroundColor: '#1E293B', borderRadius: 2, overflow: 'hidden', borderWidth: 1, borderColor: '#334155' },
  hpBar:    { height: '100%', borderRadius: 2 },
  hpNum:    { fontSize: 9, color: '#94A3B8', fontFamily: Platform.OS === 'web' ? 'monospace' : 'Courier', marginTop: 2 },
  vs:       { color: '#475569', fontSize: 11, fontFamily: Platform.OS === 'web' ? 'monospace' : 'Courier' },

  hint: { position: 'absolute', bottom: 20, left: 0, right: 0, alignItems: 'center' },
  hintText: { color: '#475569', fontSize: 10, fontFamily: Platform.OS === 'web' ? 'monospace' : 'Courier' },

  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.72)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  goTitle: { color: '#FDE047', fontSize: 40, fontFamily: Platform.OS === 'web' ? 'monospace' : 'Courier', fontWeight: 'bold', letterSpacing: 3 },
  goSub:   { color: '#94A3B8', fontSize: 16, fontFamily: Platform.OS === 'web' ? 'monospace' : 'Courier', marginTop: 18 },
});
