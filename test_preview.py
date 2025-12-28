"""
CENTER STAGE ULTRA - Test Preview
===================================
Press Q to quit
"""

import time
import cv2

# === CONFIG ===
CAM_ID = 0
CAM_W, CAM_H = 1920, 1080  # 1080p
DETECT_INTERVAL = 2
SMOOTH = 0.06              # Smoother
MIN_CROP = 0.65
PADDING = 1.5
DEADZONE = 0.02
ZOOM_DEADZONE = 0.05       # Prevent erratic zoom
FACE_PERSIST = 15

# === FACE DETECT ===
frontal = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
profile = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
last_face = None
no_face_count = 0

def detect(frame):
    global last_face, no_face_count
    h, w = frame.shape[:2]
    s = 320 / w  # Larger for 1080p stability
    small = cv2.resize(frame, (320, int(h*s)), interpolation=cv2.INTER_LINEAR)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    
    faces = frontal.detectMultiScale(gray, 1.1, 4, minSize=(25,25))
    if len(faces) == 0:
        faces = profile.detectMultiScale(gray, 1.1, 4, minSize=(25,25))
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

def ease(c, t, s):
    d = t - c
    return c + d * s * (2 - abs(d))

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
        if abs(nw-tw) > ZOOM_DEADZONE: tw, th = nw, nh
    else:
        tx, ty, tw, th = 0, 0, 1, 1
    cx, cy = ease(cx, tx, SMOOTH), ease(cy, ty, SMOOTH)
    cw, ch = ease(cw, tw, SMOOTH*0.7), ease(ch, th, SMOOTH*0.7)

def apply_crop(frame, out_w, out_h):
    h, w = frame.shape[:2]
    x1, y1 = max(0,int(cx*w)), max(0,int(cy*h))
    x2, y2 = min(w,int((cx+cw)*w)), min(h,int((cy+ch)*h))
    if x2>x1 and y2>y1:
        return cv2.resize(frame[y1:y2,x1:x2], (out_w,out_h))
    return cv2.resize(frame, (out_w,out_h))

# === MAIN ===
def run():
    print("="*45)
    print("  CENTER STAGE ULTRA - Preview (1080p)")
    print("="*45)
    print("Press Q to quit\n")
    
    cap = cv2.VideoCapture(CAM_ID, cv2.CAP_DSHOW)
    cap.set(3,CAM_W); cap.set(4,CAM_H)
    if not cap.isOpened(): return print("No camera!")
    print(f"[✓] Camera ready")
    
    cv2.namedWindow("Center Stage", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Center Stage", 960, 540)
    
    n, fps_t, fps_c, fps = 0, time.time(), 0, 0
    while True:
        ok, frame = cap.read()
        if not ok: continue
        n += 1; fps_c += 1
        
        face = detect(frame) if n % DETECT_INTERVAL == 0 else last_face
        update_crop(face)
        out = apply_crop(frame, 960, 540)
        
        status = "TRACKING" if face else "IDLE"
        cv2.rectangle(out, (10,10), (220,50), (0,0,0), -1)
        cv2.putText(out, f"{status} {fps}fps 1080p", (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 
                    (0,255,0) if face else (128,128,128), 2)
        
        cv2.imshow("Center Stage", out)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
        
        if time.time() - fps_t >= 1:
            fps, fps_c, fps_t = fps_c, 0, time.time()
    
    cap.release()
    cv2.destroyAllWindows()
    print("[✓] Done!")

if __name__ == "__main__": run()
