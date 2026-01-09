import os
import cv2
import numpy as np
import pickle
from sklearn.ensemble import RandomForestClassifier

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_PATH = "model.pkl"
FACE_DETECTOR_MODEL = "face_detector.tflite"

def create_face_detector():
    base_options = python.BaseOptions(model_asset_path=FACE_DETECTOR_MODEL)
    options = vision.FaceDetectorOptions(
        base_options=base_options,
        min_detection_confidence=0.5
    )
    return vision.FaceDetector.create_from_options(options)

def crop_face_and_embed(bgr_image, detection):
    h, w = bgr_image.shape[:2]
    bbox = detection.bounding_box

    x1 = max(0, bbox.origin_x)
    y1 = max(0, bbox.origin_y)
    x2 = min(w, x1 + bbox.width)
    y2 = min(h, y1 + bbox.height)

    if x2 <= x1 or y2 <= y1:
        return None

    face = bgr_image[y1:y2, x1:x2]
    face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    face = cv2.resize(face, (32, 32))

    return face.flatten().astype(np.float32) / 255.0

def extract_embedding_for_image(stream):
    detector = create_face_detector()
    arr = np.frombuffer(stream.read(), np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = detector.detect(mp_image)

    if not result.detections:
        return None

    return crop_face_and_embed(img, result.detections[0])

def load_model_if_exists():
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)

def predict_with_model(clf, emb):
    proba = clf.predict_proba([emb])[0]
    idx = np.argmax(proba)
    return clf.classes_[idx], float(proba[idx])

def train_model_background(dataset_dir, progress_callback=None):
    detector = create_face_detector()
    X, y = [], []

    for sid in os.listdir(dataset_dir):
        folder = os.path.join(dataset_dir, sid)
        if not os.path.isdir(folder):
            continue

        for fn in os.listdir(folder):
            if not fn.lower().endswith((".jpg", ".png", ".jpeg")):
                continue

            img = cv2.imread(os.path.join(folder, fn))
            if img is None:
                continue

            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect(mp_image)

            if not result.detections:
                continue

            emb = crop_face_and_embed(img, result.detections[0])
            if emb is None:
                continue

            X.append(emb)
            y.append(int(sid))

    if not X:
        return

    clf = RandomForestClassifier(n_estimators=150, n_jobs=-1, random_state=42)
    clf.fit(np.stack(X), np.array(y))

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)

    if progress_callback:
        progress_callback(100, "Training complete")
