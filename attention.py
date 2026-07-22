import cv2
import numpy as np
from config import COLORS

KP_NOSE       = 0
KP_LEFT_EYE   = 1
KP_RIGHT_EYE  = 2
KP_LEFT_EAR   = 3
KP_RIGHT_EAR  = 4
KP_L_SHOULDER = 5
KP_R_SHOULDER = 6

YAW_DISTRACTED_DEG  = 25
YAW_AWAY_DEG        = 50
PITCH_SLEEPING_DEG  = 30
EAR_CLOSED_FRAMES   = 8
MIN_FACE_CONF       = 0.50
MIN_AVG_CONF        = 0.35
FACE_SIZE_MIN_PX    = 25

def estimate_head_pose(kp) -> tuple[float, float, bool]:


    def vis(i): return float(kp[i][2]) > MIN_FACE_CONF
    def pt(i):  return np.array([float(kp[i][0]), float(kp[i][1])])

    nose_v  = vis(KP_NOSE)
    l_eye_v = vis(KP_LEFT_EYE)
    r_eye_v = vis(KP_RIGHT_EYE)
    l_ear_v = vis(KP_LEFT_EAR)
    r_ear_v = vis(KP_RIGHT_EAR)

    yaw, pitch = 0.0, 0.0
    yaw_ok = pitch_ok = False

    if nose_v and l_eye_v and r_eye_v:
        eye_mid  = (pt(KP_LEFT_EYE) + pt(KP_RIGHT_EYE)) / 2
        eye_span = float(np.linalg.norm(pt(KP_LEFT_EYE) - pt(KP_RIGHT_EYE)))

        if eye_span >= FACE_SIZE_MIN_PX:

            horiz_offset = pt(KP_NOSE)[0] - eye_mid[0]
            yaw = float(np.degrees(np.arctan2(horiz_offset, eye_span * 0.6)))
            yaw_ok = True

            vert_offset = pt(KP_NOSE)[1] - eye_mid[1]
            pitch = float(np.degrees(np.arctan2(vert_offset, eye_span * 0.5)))
            pitch_ok = True


    elif l_ear_v and r_ear_v and not nose_v:

        ear_dx = pt(KP_LEFT_EAR)[0] - pt(KP_RIGHT_EAR)[0]
        yaw    = 85.0 * float(np.sign(ear_dx))
        yaw_ok = True

    elif l_ear_v and not r_ear_v and not l_eye_v and not nose_v:
        yaw = 80.0
        yaw_ok = True

    elif r_ear_v and not l_ear_v and not r_eye_v and not nose_v:
        yaw = -80.0
        yaw_ok = True

    if vis(KP_L_SHOULDER) or vis(KP_R_SHOULDER):
        if not nose_v and not l_eye_v and not r_eye_v:
            pitch    = -90.0
            pitch_ok = True

    reliable = yaw_ok or pitch_ok
    return yaw, pitch, reliable


def estimate_eye_state(kp) -> tuple[float, bool]:

    l_conf    = float(kp[KP_LEFT_EYE][2])
    r_conf    = float(kp[KP_RIGHT_EYE][2])
    nose_conf = float(kp[KP_NOSE][2])

    if nose_conf < 0.25:
        return 0.5, True

    avg_eye  = (l_conf + r_conf) / 2.0
    ratio    = avg_eye / max(nose_conf, 0.01)
    # Ratio > 0.55 → eyes open  |  Ratio < 0.35 → eyes closed
    eyes_open = ratio > 0.40
    return ratio, eyes_open

def score_attention_v2(
    keypoints: np.ndarray,
    has_phone: bool,
    closed_eye_streak: int = 0,
) -> tuple[int, str, dict]:

    kp = keypoints


    face_confs = [float(kp[i][2]) for i in range(5)]
    avg_conf   = float(np.mean(face_confs))
    max_conf   = float(np.max(face_confs))

    if max_conf < 0.22:

        return 10, 'UNCERTAIN', {
            'yaw': 0, 'pitch': 0, 'eyes_open': False,
            'avg_conf': avg_conf, 'reason': 'camera_quality'
        }

    yaw, pitch, pose_ok = estimate_head_pose(kp)

    ear_ratio, eyes_open = estimate_eye_state(kp)
    eyes_closed_long     = closed_eye_streak >= EAR_CLOSED_FRAMES

    score = 0

    if max_conf > MIN_FACE_CONF:
        score += 25

    if pose_ok:
        abs_yaw = abs(yaw)
        if abs_yaw < YAW_DISTRACTED_DEG:
            score += 45
        elif abs_yaw < YAW_AWAY_DEG:
            score += 20
        else:
            score += 0

        if pitch < -PITCH_SLEEPING_DEG:
            score = min(score, 12)
    else:

        score = min(score, 20)


    if eyes_open and not eyes_closed_long:
        score += 20
    elif eyes_closed_long:
        score = min(score, 12)

    if avg_conf >= MIN_AVG_CONF:
        scale = 0.5 + 0.5 * min(1.0, (avg_conf - MIN_AVG_CONF) / (1.0 - MIN_AVG_CONF))
    else:
        scale = 0.40
    score = int(score * scale)

    if has_phone:
        score = min(score, 25)

    score = max(0, min(100, score))

    if has_phone:
        state = 'PHONE'
    elif eyes_closed_long or (pitch < -PITCH_SLEEPING_DEG and pose_ok):
        state = 'SLEEPING'
    elif abs(yaw) > YAW_AWAY_DEG and pose_ok:
        state = 'DISTRACTED'
    elif score >= 65:
        state = 'ATTENTIVE'
    elif score >= 30:
        state = 'DISTRACTED'
    else:
        state = 'SLEEPING'

    debug = {
        'yaw':      round(yaw, 1),
        'pitch':    round(pitch, 1),
        'eyes_open': eyes_open,
        'ear':      round(ear_ratio, 3),
        'avg_conf': round(avg_conf, 3),
        'streak':   closed_eye_streak,
        'reliable': pose_ok,
    }
    return score, state, debug

class AttentionEngine:

    def __init__(self):
        self._eye_streaks: dict[int, int] = {}

    @staticmethod
    def _corner_brackets(img, pt1, pt2, color, size=14, t=2):
        x1, y1 = pt1; x2, y2 = pt2
        for x, y, dx, dy in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
            cv2.line(img, (x, y), (x+dx*size, y), color, t)
            cv2.line(img, (x, y), (x, y+dy*size), color, t)

    @staticmethod
    def _draw_skeleton(img, kp, color):
        LINKS = [
            (KP_NOSE, KP_LEFT_EYE), (KP_NOSE, KP_RIGHT_EYE),
            (KP_LEFT_EYE, KP_RIGHT_EYE),
            (KP_LEFT_EYE, KP_LEFT_EAR), (KP_RIGHT_EYE, KP_RIGHT_EAR),
            (KP_L_SHOULDER, KP_R_SHOULDER),
        ]
        for a, b in LINKS:
            if kp[a][2] > MIN_FACE_CONF and kp[b][2] > MIN_FACE_CONF:
                cv2.line(img,
                         (int(kp[a][0]), int(kp[a][1])),
                         (int(kp[b][0]), int(kp[b][1])),
                         color, 1, cv2.LINE_AA)

    @staticmethod
    def _boxes_near(b1, b2, margin=90) -> bool:
        x1a,y1a,x2a,y2a = b1; x1b,y1b,x2b,y2b = b2
        return not (x2a+margin < x1b or x2b+margin < x1a or
                    y2a+margin < y1b or y2b+margin < y1a)

    @staticmethod
    def _draw_header(img, students):
        h, w = img.shape[:2]
        cv2.rectangle(img, (0, 0), (w, 42), (10, 10, 20), -1)
        cv2.line(img, (0, 42), (w, 42), (0, 215, 255), 1)
        n         = len(students)
        attentive = sum(1 for s in students if s['state'] == 'ATTENTIVE')
        avg       = int(np.mean([s['score'] for s in students])) if students else 0
        col       = (57,255,20) if avg>=65 else (0,215,255) if avg>=40 else (0,50,255)
        cv2.putText(img, 'ClassPulse v2', (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0,215,255), 2, cv2.LINE_AA)
        cv2.putText(img, f'Students:{n}  Attentive:{attentive}  Avg:{avg}%',
                    (w//2-170, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, col, 1, cv2.LINE_AA)

    def process(self, frame, pose_results, obj_results):
        annotated = frame.copy()
        students  = []

        phone_boxes = []
        if obj_results and obj_results[0].boxes is not None:
            for box in obj_results[0].boxes:
                if int(box.cls[0]) == 67:
                    x1,y1,x2,y2 = box.xyxy[0].cpu().numpy().astype(int)
                    phone_boxes.append((x1,y1,x2,y2))
                    cv2.rectangle(annotated,(x1,y1),(x2,y2),(0,80,255),2)
                    cv2.putText(annotated,'PHONE',(x1,y1-6),
                                cv2.FONT_HERSHEY_SIMPLEX,0.42,(0,80,255),1)

        if (pose_results and
                pose_results[0].keypoints is not None and
                pose_results[0].keypoints.data.shape[0] > 0):

            kps_all   = pose_results[0].keypoints.data.cpu().numpy()
            boxes_all = pose_results[0].boxes
            ids_raw   = boxes_all.id

            for i, (kp, box) in enumerate(zip(kps_all, boxes_all)):
                bx1,by1,bx2,by2 = box.xyxy[0].cpu().numpy().astype(int)
                track_id = int(ids_raw[i]) if ids_raw is not None else i+1

                has_phone = any(self._boxes_near((bx1,by1,bx2,by2), pb)
                                for pb in phone_boxes)

                streak              = self._eye_streaks.get(track_id, 0)
                score, state, dbg   = score_attention_v2(kp, has_phone, streak)


                self._eye_streaks[track_id] = (streak+1 if not dbg['eyes_open']
                                               else 0)

                students.append({
                    'id': track_id, 'score': score,
                    'state': state, 'has_phone': has_phone, 'debug': dbg
                })

                color = COLORS.get(state, (120,120,120))
                cv2.rectangle(annotated,(bx1,by1),(bx2,by2),color,1)
                self._corner_brackets(annotated,(bx1,by1),(bx2,by2),color)


                lbl = f"S{track_id} {state} {score}%  yaw:{dbg['yaw']:+.0f}\u00b0"
                (lw,_),_ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
                cv2.rectangle(annotated,(bx1,by1-20),(bx1+lw+8,by1),color,-1)
                cv2.putText(annotated, lbl, (bx1+4,by1-5),
                            cv2.FONT_HERSHEY_SIMPLEX,0.40,(10,10,10),1,cv2.LINE_AA)


                for ki in range(5):
                    if kp[ki][2] > MIN_FACE_CONF:
                        cv2.circle(annotated,(int(kp[ki][0]),int(kp[ki][1])),
                                   3, color, -1, cv2.LINE_AA)
                self._draw_skeleton(annotated, kp, color)

                dinfo = (f"conf:{dbg['avg_conf']:.2f} "
                         f"pitch:{dbg['pitch']:+.0f}\u00b0 "
                         f"eyes:{'O' if dbg['eyes_open'] else 'X'}")
                cv2.putText(annotated, dinfo, (bx1+2, by2-4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.30, color, 1)


        if pose_results and pose_results[0].boxes is not None:
            ids_raw = pose_results[0].boxes.id
            active  = ({int(i) for i in ids_raw} if ids_raw is not None else set())
            self._eye_streaks = {k:v for k,v in self._eye_streaks.items()
                                 if k in active}

        self._draw_header(annotated, students)
        return students, annotated
