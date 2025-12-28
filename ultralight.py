"""
CENTER STAGE ULTRA LIGHT
=========================
The LIGHTEST version - minimal CPU, no heating.
Same quality tracking, optimized for performance.

python ultralight.py
"""

import time
import cv2

try:
    import pyvirtualcam
except:
    pyvirtualcam = None

# === ULTRA LIGHT CONFIG ===
CAM_ID = 0
CAM_W, CAM_H = 1280, 720   # 720p (less CPU than 1080p)
OUT_W, OUT_H = 1280, 720
FPS = 30
DETECT_INTERVAL = 4        # Less frequent = less CPU
SMOOTH = 0.07
MIN_CROP = 0.65
PADDING = 1.5
DEADZONE = 0.025           # Higher = less updates
FACE_PERSIST = 20          # Hold longer

# === MINIMAL FACE DETECT (frontal only for speed) ===
cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml')
last_face = None
no_face_count = 0

def detect(frame):
    global last_face, no_face_count
    h, w = frame.shape[:2]
    # Small frame = fast detection
    small = cv2.resize(frame, (200, 112), interpolation=cv2.INTER_NEAREST)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    
    faces = cascade.detectMultiScale(gray, 1.2, 4, minSize=(20,20))
    
    if len(faces):
        x, y, fw, fh = max(faces, key=lambda f: f[2]*f[3])
        last_face = (x/200, y/112, fw/200, fh/112)
        no_face_count = 0
    else:
        no_face_count += 1
        if no_face_count > FACE_PERSIST:
            last_face = None
    return last_face

# === SIMPLE SMOOTH CROP ===
cx, cy, cw, ch = 0.0, 0.0, 1.0, 1.0

def update_crop(face):
    global cx, cy, cw, ch
    if face:
        fx, fy, fw, fh = face
        tw = max(MIN_CROP, min(1.0, fw * (1 + PADDING*2)))
        th = tw / (16/9)
        if th > 1: th, tw = 1.0, 16/9
        tx = max(0, min(1-tw, fx + fw/2 - tw/2))
        ty = max(0, min(1-th, fy + fh/2 - th/2))
    else:
        tx, ty, tw, th = 0, 0, 1, 1
    
    # Simple lerp (faster than easing)
    cx += (tx - cx) * SMOOTH
    cy += (ty - cy) * SMOOTH
    cw += (tw - cw) * SMOOTH * 0.7
    ch += (th - ch) * SMOOTH * 0.7

def apply_crop(frame):
    h, w = frame.shape[:2]
    x1, y1 = int(cx*w), int(cy*h)
    x2, y2 = int((cx+cw)*w), int((cy+ch)*h)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 > x1 and y2 > y1:
        return cv2.resize(frame[y1:y2, x1:x2], (OUT_W, OUT_H), interpolation=cv2.INTER_LINEAR)
    return cv2.resize(frame, (OUT_W, OUT_H))

# === MAIN ===
def run():
    print("=" * 45)
    print("  CENTER STAGE ULTRA LIGHT")
    print("  Minimal CPU • No Heating • Smooth")
    print("=" * 45)
    
    cap = cv2.VideoCapture(CAM_ID, cv2.CAP_DSHOW)
    cap.set(3, CAM_W)
    cap.set(4, CAM_H)
    cap.set(5, FPS)
    if not cap.isOpened():
        return print("No camera!")
    print(f"[✓] Camera: {CAM_W}x{CAM_H}")
    
    if not pyvirtualcam:
        return print("No pyvirtualcam!")
    try:
        vcam = pyvirtualcam.Camera(OUT_W, OUT_H, FPS, 
                                    fmt=pyvirtualcam.PixelFormat.BGR, 
                                    backend='unitycapture')
        print(f"[✓] VCam: {vcam.device}")
    except Exception as e:
        cap.release()
        return print(f"VCam error: {e}")
    
    print("\n[✓] RUNNING! Select 'Unity Video Capture' in Teams")
    print("    Ctrl+C to stop\n" + "-" * 45)
    
    n, fps_t, fps_c = 0, time.time(), 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                continue
            n += 1
            fps_c += 1
            
            # Detect only every N frames
            if n % DETECT_INTERVAL == 0:
                detect(frame)
            
            update_crop(last_face)
            vcam.send(apply_crop(frame))
            
            if time.time() - fps_t >= 1:
                status = "TRACK" if last_face else "IDLE"
                print(f"\r[{status}] {fps_c} FPS  ", end="", flush=True)
                fps_c = 0
                fps_t = time.time()
    except KeyboardInterrupt:
        print("\n[✓] Stopped")
    finally:
        cap.release()
        vcam.close()

if __name__ == "__main__":
    run()
