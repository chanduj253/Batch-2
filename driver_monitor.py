import cv2
import mediapipe as mp
import math
import time
import winsound
import threading

mp_face_mesh = mp.solutions.face_mesh
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


def distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def eye_aspect_ratio(points):
    vertical_1 = distance(points[1], points[5])
    vertical_2 = distance(points[2], points[4])
    horizontal = distance(points[0], points[3])
    if horizontal == 0:
        return 0.0
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


def emergency_warning(frame, message):
    height, width = frame.shape[:2]
    cv2.rectangle(frame, (0, 55), (width, 145), (0, 0, 200), -1)
    cv2.putText(frame, "SAFETY WARNING!", (20, 90), cv2.FONT_HERSHEY_SIMPLEX,
                0.9, (255, 255, 255), 2)
    cv2.putText(frame, message[:45], (20, 125), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (255, 255, 255), 2)


class DriverMonitor:
    """Frame-by-frame GuardianDriveAI engine for use by Streamlit."""

    def __init__(self, camera_index=0):
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            self.cap.release()
            raise RuntimeError("Could not open webcam. Check that it is connected and not in use by another app.")

        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5,
        )
        self.hands = mp_hands.Hands(
            max_num_hands=2, min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.eye_closed_since = None
        self.yawn_since = None
        self.distracted_since = None
        self.hand_near_face_since = None
        self.last_beep_time = 0.0
        self.beep_interval = 2.0
        self.closed = False

        self.EAR_THRESHOLD = 0.21
        self.EYE_CLOSED_SECONDS = 1.5
        self.MAR_THRESHOLD = 0.55
        self.YAWN_SECONDS = 1.0
        self.DISTRACTION_SECONDS = 1.5
        self.HAND_WARNING_SECONDS = 1.0

    def process_frame(self):
        if self.closed:
            raise RuntimeError("Monitoring engine is closed. Start monitoring again.")
        success, frame = self.cap.read()
        if not success:
            raise RuntimeError("Could not read webcam frame.")

        frame = cv2.flip(frame, 1)
        height, width = frame.shape[:2]
        now = time.monotonic()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_result = self.face_mesh.process(rgb)
        hand_result = self.hands.process(rgb)
        alerts = []
        face_points = face_result.multi_face_landmarks[0].landmark if face_result.multi_face_landmarks else None
        ear = 0.0
        mar = 0.0

        if face_points:
            def point(index):
                landmark = face_points[index]
                return int(landmark.x * width), int(landmark.y * height)

            left_eye = [point(i) for i in [33, 160, 158, 133, 153, 144]]
            right_eye = [point(i) for i in [362, 385, 387, 263, 373, 380]]
            ear = (eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2.0
            if ear < self.EAR_THRESHOLD:
                if self.eye_closed_since is None:
                    self.eye_closed_since = now
                elif now - self.eye_closed_since >= self.EYE_CLOSED_SECONDS:
                    alerts.append("DROWSINESS WARNING - EYES CLOSED")
            else:
                self.eye_closed_since = None

            upper_lip, lower_lip = point(13), point(14)
            left_mouth, right_mouth = point(78), point(308)
            mouth_width = distance(left_mouth, right_mouth)
            mouth_opening = distance(upper_lip, lower_lip)
            mar = mouth_opening / mouth_width if mouth_width else 0.0
            if mar > self.MAR_THRESHOLD:
                if self.yawn_since is None:
                    self.yawn_since = now
                elif now - self.yawn_since >= self.YAWN_SECONDS:
                    alerts.append("POSSIBLE YAWN DETECTED")
            else:
                self.yawn_since = None

            nose = face_points[1]
            off_center = abs(nose.x - 0.5) > 0.18 or abs(nose.y - 0.5) > 0.22
            if off_center:
                if self.distracted_since is None:
                    self.distracted_since = now
                elif now - self.distracted_since >= self.DISTRACTION_SECONDS:
                    alerts.append("POSSIBLE DISTRACTION")
            else:
                self.distracted_since = None

            for index in [1, 13, 14, 33, 133, 263, 362]:
                cv2.circle(frame, point(index), 3, (0, 255, 0), -1)
            cv2.putText(frame, f"EAR: {ear:.2f}  MAR: {mar:.2f}",
                        (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (255, 255, 255), 2)
        else:
            self.eye_closed_since = None
            self.yawn_since = None
            self.distracted_since = None
            alerts.append("FACE NOT DETECTED")

        hand_near_face = False
        if face_points and hand_result.multi_hand_landmarks:
            face_refs = [face_points[1], face_points[13]]
            for hand in hand_result.multi_hand_landmarks:
                candidates = [hand.landmark[i] for i in [0, 4, 8, 12]]
                for hp in candidates:
                    for fp in face_refs:
                        if math.hypot(hp.x - fp.x, hp.y - fp.y) < 0.18:
                            hand_near_face = True
                mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

        if hand_near_face:
            if self.hand_near_face_since is None:
                self.hand_near_face_since = now
            elif now - self.hand_near_face_since >= self.HAND_WARNING_SECONDS:
                alerts.append("HAND NEAR FACE - CHECK PHONE USE")
        else:
            self.hand_near_face_since = None

        safety_level = 1
        safety_message = "NORMAL - KEEP MONITORING"
        if any("DROWSINESS WARNING" in alert for alert in alerts):
            safety_level = 3
            safety_message = "CRITICAL - DROWSINESS"
        elif any(word in alert for alert in alerts for word in ["YAWNING", "DISTRACTION", "HAND NEAR FACE"]):
            safety_level = 2
            safety_message = "CAUTION - CHECK DRIVER"

        cv2.rectangle(frame, (10, 10), (width - 10, 48), (35, 35, 35), -1)
        cv2.putText(frame, "GuardianDriveAI - Driver Monitor", (20, 36),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        emergency = self.eye_closed_since is not None and now - self.eye_closed_since >= 3.0
        if emergency:
            emergency_warning(frame, "PERSISTENT EYE CLOSURE")
            if now - self.last_beep_time >= self.beep_interval:
                threading.Thread(target=winsound.Beep, args=(1200, 300), daemon=True).start()
                self.last_beep_time = now

        if not alerts:
            alerts.append("STATUS: MONITORING")
        for i, alert in enumerate(alerts):
            color = (0, 200, 0) if alert == "STATUS: MONITORING" else (0, 0, 255)
            cv2.putText(frame, alert, (20, 80 + i * 35), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, color, 2)
        level_colors = {1: (0, 200, 0), 2: (0, 165, 255), 3: (0, 0, 255)}
        cv2.putText(frame, f"SAFETY LEVEL {safety_level}: {safety_message}",
                    (20, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    level_colors[safety_level], 2)

        results = {
            "safety_level": safety_level,
            "safety_message": safety_message,
            "alerts": alerts,
            "ear": ear,
            "mar": mar,
            "emergency": emergency,
        }
        return frame, results

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.cap.release()
        finally:
            self.face_mesh.close()
            self.hands.close()


def run_driver_monitor(camera_index=0):
    """Optional standalone mode; press q to quit."""
    monitor = DriverMonitor(camera_index=camera_index)
    try:
        while True:
            frame, _results = monitor.process_frame()
            cv2.imshow("GuardianDriveAI", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        monitor.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    run_driver_monitor()
