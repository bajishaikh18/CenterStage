"""
CENTER STAGE ULTRA - Final Version
====================================
Apple-quality + fast detection + profile support
"""

import time
import cv2

try:
    import pyvirtualcam
except:
    pyvirtualcam = None

# === CONFIG ===
CAM_ID = 0
CAM_W, CAM_H = 1920, 1080  # 1080p capture (quality)
OUT_W, OUT_H = 1280, 720   # 720p output (performance)
FPS = 30
DETECT_INTERVAL = 3        # Faster - detect every 3 frames
SMOOTH = 0.06
MIN_CROP = 0.65            # Sweet spot
PADDING = 1.5
DEADZONE = 0.02            # Higher = more stable
ZOOM_DEADZONE = 0.05       # Prevent erratic zoom changes
FACE_PERSIST = 15          # Hold face longer before clearing

# === FACE DETECT (frontal + profile) ===
frontal = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
profile = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
last_face = None
no_face_count = 0

def detect(frame):
    global last_face, no_face_count
    h, w = frame.shape[:2]
    s = 320 / w  # Larger frame for 1080p stability
    small = cv2.resize(frame, (320, int(h*s)), interpolation=cv2.INTER_LINEAR)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    
    # Try frontal first
    faces = frontal.detectMultiScale(gray, 1.1, 4, minSize=(25,25))
    
    # If no frontal, try profile (left-facing)
    if len(faces) == 0:
        faces = profile.detectMultiScale(gray, 1.1, 4, minSize=(25,25))
    
    # If still none, try flipped (right-facing profile)
    if len(faces) == 0:
        flipped = cv2.flip(gray, 1)
        faces = profile.detectMultiScale(flipped, 1.1, 4, minSize=(25,25))
        if len(faces):
            faces = [(320 - x - fw, y, fw, fh) for (x, y, fw, fh) in faces]
    
    if len(faces):
        x, y, fw, fh = max(faces, key=lambda f: f[2]*f[3])
        last_face = (x/320, y/(h*s), fw/320, fh/(h*s))
        no_face_count = 0
    else:
        no_face_count += 1
        if no_face_count > FACE_PERSIST:
            last_face = None
    
    return last_face

# === SMOOTH CROP ===
cx, cy, cw, ch = 0.0, 0.0, 1.0, 1.0
tx, ty, tw, th = 0.0, 0.0, 1.0, 1.0

def ease(current, target, speed):
    diff = target - current
    return current + diff * speed * (2 - abs(diff))

def update_crop(face):
    global tx, ty, tw, th, cx, cy, cw, ch
    if face:
        fx, fy, fw, fh = face
        nw = max(MIN_CROP, min(1.0, fw * (1 + PADDING*2)))
        nh = nw / (16/9)
        if nh > 1: nh, nw = 1.0, 16/9
        nx = max(0, min(1-nw, fx + fw/2 - nw/2))
        ny = max(0, min(1-nh, fy + fh/2 - nh/2))
        if abs(nx-tx) > DEADZONE: tx = nx
        if abs(ny-ty) > DEADZONE: ty = ny
        if abs(nw-tw) > ZOOM_DEADZONE: tw, th = nw, nh  # Use zoom deadzone
    else:
        tx, ty, tw, th = 0, 0, 1, 1
    cx, cy = ease(cx, tx, SMOOTH), ease(cy, ty, SMOOTH)
    cw, ch = ease(cw, tw, SMOOTH*0.7), ease(ch, th, SMOOTH*0.7)

def apply_crop(frame):
    h, w = frame.shape[:2]
    x1, y1 = max(0,int(cx*w)), max(0,int(cy*h))
    x2, y2 = min(w,int((cx+cw)*w)), min(h,int((cy+ch)*h))
    if x2>x1 and y2>y1:
        return cv2.resize(frame[y1:y2,x1:x2], (OUT_W,OUT_H), interpolation=cv2.INTER_LINEAR)
    return cv2.resize(frame, (OUT_W,OUT_H))

# === MAIN ===
def run():
    print("="*45)
    print("  CENTER STAGE ULTRA - Apple Quality")
    print("="*45)
    
    cap = cv2.VideoCapture(CAM_ID, cv2.CAP_DSHOW)
    cap.set(3,CAM_W); cap.set(4,CAM_H); cap.set(5,FPS)
    if not cap.isOpened(): return print("No camera!")
    print(f"[✓] Camera: {CAM_W}x{CAM_H}")
    
    if not pyvirtualcam: return print("No pyvirtualcam!")
    try:
        vcam = pyvirtualcam.Camera(OUT_W,OUT_H,FPS,fmt=pyvirtualcam.PixelFormat.BGR,backend='unitycapture')
        print(f"[✓] VCam: {vcam.device}")
    except Exception as e:
        cap.release(); return print(f"VCam error: {e}")
    
    print("\n[✓] RUNNING! Select 'Unity Video Capture' in Teams")
    print("    Ctrl+C to stop\n" + "-"*45)
    
    n, fps_t, fps_c = 0, time.time(), 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok: continue
            n += 1; fps_c += 1
            
            face = detect(frame) if n % DETECT_INTERVAL == 0 else last_face
            update_crop(face)
            vcam.send(apply_crop(frame))
            
            if time.time() - fps_t >= 1:
                print(f"\r[{'TRACK' if face else 'IDLE'}] {fps_c} FPS  ", end="", flush=True)
                fps_c, fps_t = 0, time.time()
    except KeyboardInterrupt:
        print("\n[✓] Stopped")
    finally:
        cap.release(); vcam.close()

if __name__ == "__main__": run()
