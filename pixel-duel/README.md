# ⚔️ Pixel Duel

A retro pixel-art 2D brawler with Street of Rage–style enemy physics.  
Built with **Expo (React Native)** — runs as a **React web page** and builds as an **Android APK** from the same codebase.

---

## 🎮 Controls

### Touch (mobile / web touch)

| Gesture | Action |
|---|---|
| **Tap** | Basic sword attack |
| **Swipe** (any 360° direction) | Dash in that direction |
| **Two quick swipes** | Slash attack — a glowing projectile flies through the enemy |
| **Swipe → hold → release** | Thrust — lunges into enemy; player pogo-bounces back |

### Keyboard (web desktop bonus)

| Key | Action |
|---|---|
| `A` / `←` `D` / `→` | Move left / right |
| `W` / `↑` | Jump |
| `Z` | Basic attack |
| `X` | Thrust |
| `C` | Slash |

---

## 🌐 Run as a Web Page

```bash
npm install
npx expo start --web
```

Open the printed URL in any browser.

---

## 📱 Build the Android APK

### One-time local setup

```bash
npm install -g eas-cli
eas login              # create a free account at expo.dev if needed
eas build:configure    # generates / updates eas.json (already included)
```

### Build locally

```bash
npm run build:apk
# or: eas build --platform android --profile preview
```

The APK download link appears in your terminal and at **https://expo.dev → your project → Builds**.

---

## 🤖 Automatic APK via GitHub Actions

Every push to `main` triggers the build workflow automatically.

**Required one-time setup:**

1. Go to **expo.dev → Account → Access Tokens** → create a token.
2. In your GitHub repo go to **Settings → Secrets and variables → Actions**.
3. Add a secret named `EXPO_TOKEN` with the value from step 1.

The workflow file is at `.github/workflows/build-apk.yml`.

---

## 🏗️ Project Structure

```
pixel-duel/
├── App.js                          Entry point
├── src/
│   └── GameScreen.js               All game logic, physics, AI, rendering
├── app.json                        Expo config
├── eas.json                        EAS build profiles
├── .github/
│   └── workflows/
│       └── build-apk.yml           GitHub Actions APK build
└── package.json
```

---

## ⚔️ Game Features

- **Pixel-art characters** rendered via SVG rectangles — no image assets needed
- **Street of Rage physics**: knockback, stagger, air launch, ground bounce
- **4 distinct attacks** with different range, damage, and trajectory
- **Particle effects** on every hit
- **Animated background** with blinking city windows
- **HP system** with colour-coded health bars
- Full **game-over / restart** flow
