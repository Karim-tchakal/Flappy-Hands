# 🐦 Flappy Bird — Hand Gesture Edition

A pixel-perfect Flappy Bird clone controlled by your webcam using **MediaPipe hand landmarks**.  
Pinch your **index finger + thumb** together to make the bird jump.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Pygame](https://img.shields.io/badge/Pygame-2.5%2B-green)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10%2B-orange)

---

## ✨ Features

- Classic Flappy Bird gameplay at **1000×800**
- **Real-time hand landmark overlay** — see your hand skeleton live in the bottom-right corner
- **Camera picker screen** — automatically detects all connected cameras so you can choose the right one (no more hardcoded index `0`)
- Falls back to **SPACE key** if no webcam is available
- Uses the modern **MediaPipe Tasks API** (`mp.tasks`) — not the deprecated `mp.solutions`

---

## 🖥️ Requirements

- Python **3.8+**
- A webcam (optional — keyboard fallback available)

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/flappy-gesture.git
cd flappy-gesture
```

### 2. (Recommended) Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download the MediaPipe hand landmarker model

The model file is **not included** in the repo (it's ~9 MB).  
Run this once to download it into the project folder:

**macOS / Linux:**
```bash
curl -o hand_landmarker.task \
  "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
```

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" -OutFile "hand_landmarker.task"
```

**Or with Python (any OS):**
```bash
python -c "import urllib.request; urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task', 'hand_landmarker.task')"
```

---

## ▶️ Running the game

```bash
python flappy_gesture.py
```

On launch you will see a **camera selection screen** that automatically scans all available cameras (indices 0–9) and lists the ones that work.  
Use **↑ / ↓** to highlight a camera and press **ENTER** to confirm.  
Press **SPACE** to skip camera selection and play with keyboard only.

---

## 🎮 Controls

| Action | Input |
|---|---|
| Jump / Flap | Pinch index finger + thumb |
| Jump (fallback) | SPACE |
| Quit | ESC |

---

## 📁 Project structure

```
flappy-gesture/
├── flappy_gesture.py      # Main game
├── hand_landmarker.task   # MediaPipe model (download separately)
├── requirements.txt       # Python dependencies
└── README.md
```

---

## 🤝 Contributing

Pull requests are welcome! Open an issue first to discuss what you'd like to change.

---

## 📄 License

MIT