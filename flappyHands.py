import pygame
import cv2
import mediapipe as mp
import threading
import math
import sys
import os
import random

# -----------------------------------------------------------
#  Paths
# -----------------------------------------------------------
HERE       = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "hand_landmarker.task")

def check_model():
    if not os.path.exists(MODEL_PATH):
        print("=" * 62)
        print("  ERROR: hand_landmarker.task not found!")
        print("  Download with:")
        print('    curl -o hand_landmarker.task \\')
        print('      "https://storage.googleapis.com/mediapipe-models/')
        print('       hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"')
        print("=" * 62)
        sys.exit(1)

# -----------------------------------------------------------
#  Layout constants
# -----------------------------------------------------------
WIN_W,  WIN_H   = 1000, 800
GAME_W, GAME_H  = 540,  800
GAME_X          = (WIN_W - GAME_W) // 2   # 230 px sidebars

PANEL_W, PANEL_H = 290, 255
PANEL_X = WIN_W - PANEL_W - 8
PANEL_Y = WIN_H - PANEL_H - 8

FPS = 60

# -----------------------------------------------------------
#  Physics
# -----------------------------------------------------------
GRAVITY        = 0.38
FLAP_VEL       = -9.2
MAX_FALL       = 11.0
ANGLE_UP       = -28
ANGLE_DOWN_MAX = 80

# -----------------------------------------------------------
#  Pipes
# -----------------------------------------------------------
PIPE_W        = 72
PIPE_GAP      = 250        # generous gap
PIPE_SPEED    = 3.8
PIPE_INTERVAL = 115
GROUND_H      = 110
GROUND_Y      = GAME_H - GROUND_H

# -----------------------------------------------------------
#  Colour palette  (retro night-sky neon)
# -----------------------------------------------------------
SKY_TOP   = (10,  15,  40)
SKY_MID   = (20,  40,  90)
SKY_BOT   = (40,  80, 130)

PIPE_BODY  = ( 34, 180,  60)
PIPE_SHINE = ( 80, 230, 100)
PIPE_SHADOW= ( 18,  90,  30)
PIPE_CAP   = ( 28, 155,  50)
PIPE_CAP_S = ( 14,  75,  24)

GROUND_TOP   = ( 80,  60,  30)
GROUND_MID   = (110,  80,  40)
GROUND_BASE  = ( 60,  42,  18)
GRASS_GREEN  = ( 60, 160,  50)
GRASS_BRIGHT = ( 90, 210,  70)

BIRD_BODY  = (255, 210,  40)
BIRD_BELLY = (255, 240, 160)
BIRD_WLO   = (200, 140,  10)
BIRD_WHI   = (255, 200,  50)
BIRD_EYE   = (255, 255, 255)
BIRD_PUPIL = ( 20,  20,  20)
BIRD_BEAK  = (255, 130,  20)
BIRD_CHEEK = (255, 100, 100)

WHITE      = (255, 255, 255)
BLACK      = (  0,   0,   0)
GOLD       = (255, 210,  50)
RED_VIVID  = (255,  60,  60)
UI_SHADOW  = ( 15,   8,  35)

STAR_COLS = [(255,255,255),(200,220,255),(255,240,200)]

LM_BONE    = ( 80, 160, 255)
LM_JOINT   = ( 50, 210, 255)
LM_PINCH   = (255,  60,  60)
LM_SPECIAL = (255, 220,   0)

HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),
    (0,17),
]
THUMB_TIP = 4
INDEX_TIP = 8

# -----------------------------------------------------------
#  Helpers
# -----------------------------------------------------------
def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i]-a[i]) * t) for i in range(3))

def make_sky(w, h):
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / h
        if t < 0.5:
            c = lerp_color(SKY_TOP, SKY_MID, t * 2)
        else:
            c = lerp_color(SKY_MID, SKY_BOT, (t - 0.5) * 2)
        pygame.draw.line(surf, c, (0, y), (w, y))
    return surf

def make_sidebar(w, h):
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / h
        c = lerp_color(SKY_TOP, SKY_MID, t)
        pygame.draw.line(surf, c, (0, y), (w, y))
    return surf

def make_stars(w, h, n=80):
    rng = random.Random(42)
    out = []
    for _ in range(n):
        x   = rng.randint(0, w)
        y   = rng.randint(0, int(h * 0.62))
        r   = rng.choice([1, 1, 1, 2])
        col = rng.choice(STAR_COLS)
        off = rng.uniform(0, math.pi * 2)
        out.append((x, y, r, col, off))
    return out

def draw_stars(surf, stars, tick):
    for x, y, r, col, off in stars:
        alpha = 0.5 + 0.5 * math.sin(tick * 0.04 + off)
        c = lerp_color((25, 25, 55), col, alpha)
        pygame.draw.circle(surf, c, (x, y), r)

def draw_outlined_text(surf, font, text, color, x, y, outline=3):
    for dx in range(-outline, outline+1):
        for dy in range(-outline, outline+1):
            if dx or dy:
                s = font.render(text, True, UI_SHADOW)
                surf.blit(s, (x+dx, y+dy))
    surf.blit(font.render(text, True, color), (x, y))

# -----------------------------------------------------------
#  Bird
# -----------------------------------------------------------
def draw_bird(surf, cx, cy, angle, flap_tick):
    bs = pygame.Surface((60, 46), pygame.SRCALPHA)

    # body
    pygame.draw.ellipse(bs, BIRD_BODY,  (2,  8, 48, 30))
    pygame.draw.ellipse(bs, BIRD_BELLY, (10, 16, 26, 16))

    # animated wing
    bob = int(math.sin(flap_tick * 0.28) * 5)
    wp  = [(8,18+bob),(23,10+bob),(32,20+bob),(14,28+bob)]
    pygame.draw.polygon(bs, BIRD_WLO, wp)
    pygame.draw.polygon(bs, BIRD_WHI, [(10,18+bob),(21,12+bob),(28,20+bob)])

    # eye
    pygame.draw.circle(bs, BIRD_EYE,   (39, 14), 7)
    pygame.draw.circle(bs, BIRD_PUPIL, (41, 14), 4)
    pygame.draw.circle(bs, WHITE,      (42, 12), 1)

    # blush
    pygame.draw.circle(bs, (*BIRD_CHEEK, 110), (33, 21), 4)

    # beak
    pygame.draw.polygon(bs, BIRD_BEAK, [(49,14),(60,18),(49,22)])
    pygame.draw.line(bs, (200,90,0), (49,18), (59,18), 1)

    rotated = pygame.transform.rotate(bs, -angle)
    rect    = rotated.get_rect(center=(int(cx), int(cy)))
    surf.blit(rotated, rect)

# -----------------------------------------------------------
#  Pipes
# -----------------------------------------------------------
def draw_pipe(surf, x, gap_top, gap_bot):
    cap_h = 30
    cap_x = x - 5
    cap_w = PIPE_W + 10

    def fill_pipe(rx, ry, rw, rh):
        pygame.draw.rect(surf, PIPE_BODY,   (rx, ry, rw, rh))
        pygame.draw.rect(surf, PIPE_SHINE,  (rx+4, ry, 9, rh))
        pygame.draw.rect(surf, PIPE_SHADOW, (rx+rw-7, ry, 7, rh))

    # top pipe
    if gap_top > 0:
        fill_pipe(x, 0, PIPE_W, gap_top)
        pygame.draw.rect(surf, PIPE_CAP,   (cap_x, gap_top-cap_h, cap_w, cap_h))
        pygame.draw.rect(surf, PIPE_SHINE, (cap_x+4, gap_top-cap_h, 11, cap_h))
        pygame.draw.rect(surf, PIPE_CAP_S, (cap_x+cap_w-7, gap_top-cap_h, 7, cap_h))
        pygame.draw.rect(surf, PIPE_CAP_S, (cap_x, gap_top-3, cap_w, 3))

    # bottom pipe
    bot_h = GAME_H - gap_bot
    if bot_h > 0:
        fill_pipe(x, gap_bot, PIPE_W, bot_h)
        pygame.draw.rect(surf, PIPE_CAP,   (cap_x, gap_bot, cap_w, cap_h))
        pygame.draw.rect(surf, PIPE_SHINE, (cap_x+4, gap_bot, 11, cap_h))
        pygame.draw.rect(surf, PIPE_CAP_S, (cap_x+cap_w-7, gap_bot, 7, cap_h))
        pygame.draw.rect(surf, PIPE_CAP,   (cap_x, gap_bot, cap_w, 3))

# -----------------------------------------------------------
#  Ground
# -----------------------------------------------------------
def draw_ground(surf, offset):
    pygame.draw.rect(surf, GRASS_GREEN,  (0, GROUND_Y, GAME_W, 18))
    ts = 30
    for i in range(-1, GAME_W//ts + 2):
        tx = i*ts - int(offset) % ts
        pygame.draw.ellipse(surf, GRASS_BRIGHT, (tx, GROUND_Y-5, 15, 11))
    pygame.draw.rect(surf, GROUND_MID,  (0, GROUND_Y+18, GAME_W, GROUND_H-18))
    pygame.draw.rect(surf, GROUND_TOP,  (0, GROUND_Y+18, GAME_W, 7))
    pygame.draw.rect(surf, GROUND_BASE, (0, GAME_H-18, GAME_W, 18))
    ps = 44
    for i in range(-1, GAME_W//ps + 2):
        px = i*ps - int(offset*0.6) % ps
        pygame.draw.rect(surf, GROUND_TOP, (px+4, GROUND_Y+32, 20, 5))

def new_pipe():
    margin  = 130
    gap_top = random.randint(margin, GROUND_Y - PIPE_GAP - margin)
    return {"x": float(GAME_W+20), "gap_top": gap_top,
            "gap_bot": gap_top + PIPE_GAP, "scored": False}

# -----------------------------------------------------------
#  Hand panel
# -----------------------------------------------------------
def draw_hand_panel(screen, landmarks, is_pinch, font_sm):
    panel = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
    panel.fill((8, 8, 22, 220))
    bc = (80, 255, 120) if is_pinch else (60, 80, 180)
    pygame.draw.rect(panel, bc, (0, 0, PANEL_W, PANEL_H), 2, border_radius=10)
    pygame.draw.rect(panel, bc, (2, 2, PANEL_W-4, 1))

    lbl = "  LANDMARKS  . PINCH!" if is_pinch else "  HAND LANDMARKS"
    tc  = (80, 255, 120) if is_pinch else (140, 170, 255)
    panel.blit(font_sm.render(lbl, True, tc), (8, 7))

    mg = 16
    dw, dh = PANEL_W - mg*2, PANEL_H - 36
    ox, oy = mg, 34

    if landmarks:
        def tp(lx, ly):
            return (int(ox + lx*dw), int(oy + ly*dh))

        for a, b in HAND_CONNECTIONS:
            if a < len(landmarks) and b < len(landmarks):
                pygame.draw.line(panel, LM_BONE, tp(*landmarks[a]), tp(*landmarks[b]), 2)

        if is_pinch:
            pygame.draw.line(panel, LM_PINCH,
                             tp(*landmarks[THUMB_TIP]), tp(*landmarks[INDEX_TIP]), 3)

        for i, (lx, ly) in enumerate(landmarks):
            px, py = tp(lx, ly)
            if i in (THUMB_TIP, INDEX_TIP):
                c, sz = (LM_PINCH if is_pinch else LM_SPECIAL), 7
            elif i == 0:
                c, sz = (200, 200, 255), 6
            else:
                c, sz = LM_JOINT, 4
            pygame.draw.circle(panel, c,     (px, py), sz)
            pygame.draw.circle(panel, WHITE, (px, py), sz, 1)
    else:
        msg = font_sm.render("No hand detected", True, (100, 110, 150))
        panel.blit(msg, (PANEL_W//2 - msg.get_width()//2,
                         PANEL_H//2 - msg.get_height()//2))

    screen.blit(panel, (PANEL_X, PANEL_Y))

# -----------------------------------------------------------
#  Camera scanner + picker
# -----------------------------------------------------------
def scan_cameras(max_idx=9):
    found = []
    for i in range(max_idx+1):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                found.append(i)
            cap.release()
    return found

def camera_picker(screen, clock):
    W, H = screen.get_size()
    f_title = pygame.font.SysFont("Consolas", 42, bold=True)
    f_med   = pygame.font.SysFont("Consolas", 26, bold=True)
    f_sm    = pygame.font.SysFont("Consolas", 17)

    screen.fill((10, 12, 30))
    t = f_med.render("Scanning cameras...", True, (140, 180, 255))
    screen.blit(t, (W//2 - t.get_width()//2, H//2 - 20))
    pygame.display.flip()

    cameras  = scan_cameras()
    selected = 0
    tick     = 0

    while True:
        tick += 1
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_UP   and cameras:
                    selected = (selected-1) % len(cameras)
                if event.key == pygame.K_DOWN and cameras:
                    selected = (selected+1) % len(cameras)
                if event.key == pygame.K_RETURN and cameras:
                    return cameras[selected]
                if event.key == pygame.K_SPACE:
                    return -1
            if event.type == pygame.MOUSEBUTTONDOWN and cameras:
                mx, my = event.pos
                cx0 = W//2 - 230
                for idx in range(len(cameras)):
                    cy0 = 230 + idx*80
                    if cx0 <= mx <= cx0+460 and cy0 <= my <= cy0+62:
                        return cameras[idx]

        screen.fill((10, 12, 30))
        # subtle grid
        for gx in range(0, W, 40):
            pygame.draw.line(screen, (18, 22, 50), (gx,0), (gx,H))
        for gy in range(0, H, 40):
            pygame.draw.line(screen, (18, 22, 50), (0,gy), (W,gy))

        pulse = 0.75 + 0.25*math.sin(tick*0.06)
        tc    = (int(255*pulse), int(200*pulse), int(50*pulse))
        title = f_title.render("  SELECT CAMERA", True, tc)
        screen.blit(title, (W//2 - title.get_width()//2, 70))

        sub = f_sm.render("UP/DOWN to navigate    ENTER to confirm    SPACE for keyboard-only", True, (70,80,130))
        screen.blit(sub, (W//2 - sub.get_width()//2, 130))

        # divider
        pygame.draw.rect(screen, (*tc, 80), (W//2-180, 160, 360, 2))

        if not cameras:
            msg = f_med.render("No cameras found -- press SPACE for keyboard mode", True, (255,80,80))
            screen.blit(msg, (W//2 - msg.get_width()//2, H//2 - 16))
        else:
            cx0 = W//2 - 230
            for idx, cam_id in enumerate(cameras):
                cy0    = 230 + idx*80
                is_sel = (idx == selected)
                bg     = (30, 55, 110) if is_sel else (18, 22, 48)
                border = (80, 200, 120) if is_sel else (40, 50, 100)
                pygame.draw.rect(screen, bg,     (cx0, cy0, 460, 62), border_radius=12)
                pygame.draw.rect(screen, border, (cx0, cy0, 460, 62), 2, border_radius=12)
                if is_sel:
                    sh = pygame.Surface((460, 3), pygame.SRCALPHA)
                    sh.fill((255,255,255,15))
                    screen.blit(sh, (cx0, cy0+2))
                label = f"Camera  {cam_id}" + ("   <-- selected" if is_sel else "")
                col   = (80, 255, 130) if is_sel else (160, 170, 220)
                lt    = f_med.render(label, True, col)
                screen.blit(lt, (cx0+22, cy0 + 62//2 - lt.get_height()//2))

        kb = f_sm.render("No webcam? Press SPACE -> keyboard only (SPACE key = flap)", True, (55,65,100))
        screen.blit(kb, (W//2 - kb.get_width()//2, H-50))
        pygame.display.flip()

# -----------------------------------------------------------
#  Gesture detector
# -----------------------------------------------------------
class GestureDetector:
    PINCH_THRESHOLD = 0.07

    def __init__(self, camera_index=0):
        self.pinch_detected = False
        self._prev_pinch    = False
        self.pinch_event    = threading.Event()
        self._lock          = threading.Lock()
        self._running       = True
        self._cap           = None
        self._recognizer    = None
        self.landmarks      = []
        self._cam_idx       = camera_index

        BaseOptions        = mp.tasks.BaseOptions
        HandLandmarker     = mp.tasks.vision.HandLandmarker
        HandLandmarkerOpts = mp.tasks.vision.HandLandmarkerOptions
        RunningMode        = mp.tasks.vision.RunningMode

        opts = HandLandmarkerOpts(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=RunningMode.LIVE_STREAM,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            result_callback=self._on_result,
        )
        self._recognizer = HandLandmarker.create_from_options(opts)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _on_result(self, result, output_image, timestamp_ms):
        if not result.hand_landmarks:
            with self._lock:
                self.pinch_detected = False
                self.landmarks = []
            return
        lm    = result.hand_landmarks[0]
        dist  = math.hypot(lm[THUMB_TIP].x - lm[INDEX_TIP].x,
                           lm[THUMB_TIP].y - lm[INDEX_TIP].y)
        is_p  = dist < self.PINCH_THRESHOLD
        with self._lock:
            if is_p and not self._prev_pinch:
                self.pinch_event.set()
            self.pinch_detected = is_p
            self._prev_pinch    = is_p
            self.landmarks      = [(1.0 - p.x, p.y) for p in lm]

    def _run(self):
        self._cap = cv2.VideoCapture(self._cam_idx)
        if not self._cap.isOpened():
            print(f"WARNING: Camera {self._cam_idx} unavailable. SPACE to play.")
            return
        ts = 0
        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                continue
            rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts    += 33
            self._recognizer.detect_async(mp_img, ts)

    def consume_pinch(self):
        if self.pinch_event.is_set():
            self.pinch_event.clear()
            return True
        return False

    def get_landmarks(self):
        with self._lock:
            return list(self.landmarks), self.pinch_detected

    def stop(self):
        self._running = False
        if self._cap:        self._cap.release()
        if self._recognizer: self._recognizer.close()

# -----------------------------------------------------------
#  Main
# -----------------------------------------------------------
def main():
    check_model()
    pygame.init()

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Flappy Bird -- Gesture Edition")
    clock  = pygame.time.Clock()

    f_huge = pygame.font.SysFont("Consolas", 64, bold=True)
    f_big  = pygame.font.SysFont("Consolas", 38, bold=True)
    f_med  = pygame.font.SysFont("Consolas", 26, bold=True)
    f_sm   = pygame.font.SysFont("Consolas", 15)

    cam_idx = camera_picker(screen, clock)

    sky_surf  = make_sky(GAME_W, GAME_H)
    stars     = make_stars(GAME_W, GAME_H)
    game_surf = pygame.Surface((GAME_W, GAME_H))

    sb_w     = GAME_X
    left_sb  = make_sidebar(sb_w,          WIN_H)
    right_sb = make_sidebar(WIN_W-GAME_X-GAME_W, WIN_H)

    print("Starting gesture detector...")
    gesture = GestureDetector(camera_index=max(cam_idx, 0))
    if cam_idx < 0:
        print("Keyboard-only mode.")
    else:
        print(f"Camera {cam_idx} ready. Pinch to flap!")

    def reset():
        return dict(
            bx=GAME_W//4, by=GAME_H//2,
            vy=0.0, angle=0.0,
            pipes=[], ptimer=0, goff=0.0,
            score=0, state="start", dtimer=0,
            tick=0, flaptick=0, flap_cd=0,
        )

    g    = reset()
    best = 0

    running = True
    while running:
        clock.tick(FPS)
        g["tick"]     += 1
        g["flaptick"] += 1
        if g["flap_cd"] > 0:
            g["flap_cd"] -= 1

        # events
        flap = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                if event.key == pygame.K_SPACE:  flap = True

        if gesture.consume_pinch():
            flap = True

        # state machine
        if g["state"] == "start":
            g["by"] = GAME_H//2 + math.sin(g["tick"] * 0.07) * 9
            if flap:
                g["state"]   = "play"
                g["vy"]      = FLAP_VEL
                g["flap_cd"] = 10

        elif g["state"] == "play":
            if flap and g["flap_cd"] == 0:
                g["vy"]      = FLAP_VEL
                g["flaptick"]= 0
                g["flap_cd"] = 10

            g["vy"] = min(g["vy"] + GRAVITY, MAX_FALL)
            g["by"] += g["vy"]

            # smooth angle lerp
            target = ANGLE_UP if g["vy"] < 0 else min(ANGLE_DOWN_MAX, g["vy"] * 6.5)
            g["angle"] += (target - g["angle"]) * 0.18

            if g["by"] >= GROUND_Y - 20:
                g["by"]    = GROUND_Y - 20
                g["state"] = "dead"
                g["dtimer"]= 0

            if g["by"] <= 20:
                g["by"] = 20
                g["vy"] = 0.0

            g["ptimer"] += 1
            if g["ptimer"] >= PIPE_INTERVAL:
                g["pipes"].append(new_pipe())
                g["ptimer"] = 0

            for p in g["pipes"]:
                p["x"] -= PIPE_SPEED
                if not p["scored"] and p["x"] + PIPE_W < g["bx"]:
                    p["scored"] = True
                    g["score"] += 1
                    best = max(best, g["score"])
                bx, by = g["bx"], g["by"]
                hr = 16
                if bx+hr > p["x"]+5 and bx-hr < p["x"]+PIPE_W-5:
                    if by-hr < p["gap_top"] or by+hr > p["gap_bot"]:
                        g["state"]  = "dead"
                        g["dtimer"] = 0

            g["pipes"] = [p for p in g["pipes"] if p["x"] > -PIPE_W-20]
            g["goff"]  = (g["goff"] + PIPE_SPEED) % 40

        elif g["state"] == "dead":
            g["vy"]    = min(g["vy"] + GRAVITY*1.5, MAX_FALL*1.2)
            g["by"]    = min(g["by"] + g["vy"], GROUND_Y - 20)
            g["angle"] = min(g["angle"] + 5, 90)
            g["dtimer"]+= 1
            if g["dtimer"] > 80 and flap:
                best = max(best, g["score"])
                g = reset()
                g["state"] = "start"

        # ---- render game canvas ----
        game_surf.blit(sky_surf, (0, 0))
        draw_stars(game_surf, stars, g["tick"])

        for p in g["pipes"]:
            draw_pipe(game_surf, int(p["x"]), p["gap_top"], p["gap_bot"])

        draw_ground(game_surf, g["goff"])
        draw_bird(game_surf, g["bx"], g["by"], g["angle"], g["flaptick"])

        # score
        sc_str = str(g["score"])
        sw     = f_huge.size(sc_str)[0]
        draw_outlined_text(game_surf, f_huge, sc_str, GOLD,
                           GAME_W//2 - sw//2, 18, outline=3)

        if g["state"] == "start":
            card = pygame.Surface((GAME_W-60, 165), pygame.SRCALPHA)
            card.fill((10, 12, 35, 210))
            pygame.draw.rect(card, GOLD, (0,0,GAME_W-60,165), 2, border_radius=14)
            game_surf.blit(card, (30, GAME_H//3 - 22))

            tw = f_big.size("FLAPPY BIRD")[0]
            draw_outlined_text(game_surf, f_big, "FLAPPY BIRD", GOLD,
                               GAME_W//2-tw//2, GAME_H//3-8, outline=2)
            hw = f_sm.size("Pinch index+thumb  or  SPACE to flap")[0]
            draw_outlined_text(game_surf, f_sm, "Pinch index+thumb  or  SPACE to flap",
                               (200,230,255), GAME_W//2-hw//2, GAME_H//3+62, outline=1)
            if best > 0:
                bw = f_sm.size(f"Best: {best}")[0]
                draw_outlined_text(game_surf, f_sm, f"Best: {best}", GOLD,
                                   GAME_W//2-bw//2, GAME_H//3+90, outline=1)

        if g["state"] == "dead":
            card = pygame.Surface((GAME_W-60, 175), pygame.SRCALPHA)
            card.fill((30, 5, 5, 215))
            pygame.draw.rect(card, RED_VIVID, (0,0,GAME_W-60,175), 2, border_radius=14)
            game_surf.blit(card, (30, GAME_H//3 - 22))

            gw = f_big.size("GAME  OVER")[0]
            draw_outlined_text(game_surf, f_big, "GAME  OVER", RED_VIVID,
                               GAME_W//2-gw//2, GAME_H//3-8, outline=2)
            scs = f"Score: {g['score']}   Best: {best}"
            scw = f_med.size(scs)[0]
            draw_outlined_text(game_surf, f_med, scs, GOLD,
                               GAME_W//2-scw//2, GAME_H//3+60, outline=2)
            if g["dtimer"] > 80:
                a   = int(128 + 127*math.sin(g["dtimer"]*0.12))
                rw  = f_sm.size("Pinch or SPACE to restart")[0]
                draw_outlined_text(game_surf, f_sm, "Pinch or SPACE to restart",
                                   (a,a,a), GAME_W//2-rw//2, GAME_H//3+110, outline=1)

        # ---- compose window ----
        screen.blit(left_sb,  (0, 0))
        screen.blit(right_sb, (GAME_X + GAME_W, 0))
        screen.blit(game_surf, (GAME_X, 0))

        # subtle edge lines
        pygame.draw.line(screen, (50,70,150), (GAME_X,0),        (GAME_X,WIN_H),        1)
        pygame.draw.line(screen, (50,70,150), (GAME_X+GAME_W,0), (GAME_X+GAME_W,WIN_H), 1)

        # hand landmark panel
        landmarks, is_pinch = gesture.get_landmarks()
        draw_hand_panel(screen, landmarks, is_pinch, f_sm)

        # pinch indicator dot
        dot = (50,255,80) if is_pinch else (55,65,110)
        pygame.draw.circle(screen, dot,   (WIN_W-26, 26), 13)
        pygame.draw.circle(screen, WHITE, (WIN_W-26, 26), 13, 2)

        pygame.display.flip()

    gesture.stop()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()