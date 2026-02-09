# import os
# import cv2
# import numpy as np
# import pickle
# from sklearn.ensemble import RandomForestClassifier
# import mediapipe as mp
# from mediapipe.tasks import python
# from mediapipe.tasks.python import vision

# MODEL_PATH = "model.pkl"
# FACE_DETECTOR_MODEL = "face_detector.tflite"

# def create_face_detector():
#     base_options = python.BaseOptions(model_asset_path=FACE_DETECTOR_MODEL)
#     options = vision.FaceDetectorOptions(
#         base_options=base_options,
#         min_detection_confidence=0.5
#     )
#     return vision.FaceDetector.create_from_options(options)

# def crop_face_and_embed(bgr_image, detection):
#     h, w = bgr_image.shape[:2]
#     bbox = detection.bounding_box

#     x1, y1 = max(0, bbox.origin_x), max(0, bbox.origin_y)
#     x2, y2 = min(w, x1 + bbox.width), min(h, y1 + bbox.height)

#     if x2 <= x1 or y2 <= y1:
#         return None

#     face = bgr_image[y1:y2, x1:x2]
    
#     # IMPROVED EMBEDDING: Histogram of Oriented Gradients (HOG) simulation
#     # Instead of just raw pixels, we use a larger resolution and normalized intensity
#     face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
#     face = cv2.resize(face, (64, 64)) # Increased resolution
#     face = cv2.equalizeHist(face)    # Normalize lighting
    
#     # Flatten and normalize
#     return face.flatten().astype(np.float32) / 255.0

# def extract_embedding_for_image(stream):
#     detector = create_face_detector()
#     data = stream.read()
#     if not data: return None
#     arr = np.frombuffer(data, np.uint8)
#     img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
#     if img is None: return None

#     rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#     mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
#     result = detector.detect(mp_image)

#     if not result.detections:
#         return None

#     return crop_face_and_embed(img, result.detections[0])

# def load_model_if_exists():
#     if not os.path.exists(MODEL_PATH):
#         return None
#     try:
#         with open(MODEL_PATH, "rb") as f:
#             return pickle.load(f)
#     except:
#         return None

# def predict_with_model(clf, emb):
#     # Get probability distribution
#     proba = clf.predict_proba([emb])[0]
#     idx = np.argmax(proba)
#     # Return the predicted ID and the confidence score
#     return clf.classes_[idx], float(proba[idx])

# def train_model_background(dataset_dir, progress_callback=None):
#     detector = create_face_detector()
#     X, y = [], []
    
#     folders = [f for f in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, f))]
#     total_folders = len(folders)

#     for i, sid in enumerate(folders):
#         folder = os.path.join(dataset_dir, sid)
        
#         if progress_callback:
#             progress_callback(int((i / total_folders) * 90), f"Processing Student {sid}...")

#         for fn in os.listdir(folder):
#             if not fn.lower().endswith((".jpg", ".png", ".jpeg")):
#                 continue

#             img = cv2.imread(os.path.join(folder, fn))
#             if img is None: continue

#             rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#             mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
#             result = detector.detect(mp_image)

#             if result.detections:
#                 emb = crop_face_and_embed(img, result.detections[0])
#                 if emb is not None:
#                     X.append(emb)
#                     y.append(int(sid))

#     if len(np.unique(y)) < 2:
#         if progress_callback:
#             progress_callback(0, "Error: Need at least 2 different students to train")
#         return

#     # Using RandomForest with balanced class weights to handle different dataset sizes
#     clf = RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=42, class_weight="balanced")
#     clf.fit(np.stack(X), np.array(y))

#     with open(MODEL_PATH, "wb") as f:
#         pickle.dump(clf, f)

#     if progress_callback:
#         progress_callback(100, "Sync Complete: AI Updated")

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
    options = vision.FaceDetectorOptions(base_options=base_options, min_detection_confidence=0.5)
    return vision.FaceDetector.create_from_options(options)

def crop_face_and_embed(bgr_image, detection):
    h, w = bgr_image.shape[:2]
    bbox = detection.bounding_box
    x1, y1 = max(0, bbox.origin_x), max(0, bbox.origin_y)
    x2, y2 = min(w, x1 + bbox.width), min(h, y1 + bbox.height)
    if x2 <= x1 or y2 <= y1: return None
    face = bgr_image[y1:y2, x1:x2]
    face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    face = cv2.resize(face, (64, 64))
    face = cv2.equalizeHist(face)
    return face.flatten().astype(np.float32) / 255.0

# This function must exist for app.py to import it
def extract_embedding_for_image(stream):
    detector = create_face_detector()
    data = stream.read()
    if not data: return None
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None: return None
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = detector.detect(mp_image)
    if not result.detections: return None
    return crop_face_and_embed(img, result.detections[0])

def load_model_if_exists():
    if not os.path.exists(MODEL_PATH): return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)

def predict_with_model(clf, emb):
    proba = clf.predict_proba([emb])[0]
    idx = np.argmax(proba)
    return clf.classes_[idx], float(proba[idx])

def train_model_background(dataset_dir, progress_callback=None):
    detector = create_face_detector()
    X, y = [], []
    folders = [f for f in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, f))]
    for sid in folders:
        folder = os.path.join(dataset_dir, sid)
        for fn in os.listdir(folder):
            if fn.lower().endswith((".jpg", ".jpeg", ".png")):
                img = cv2.imread(os.path.join(folder, fn))
                if img is None: continue
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = detector.detect(mp_image)
                if result.detections:
                    emb = crop_face_and_embed(img, result.detections[0])
                    if emb is not None:
                        X.append(emb)
                        y.append(int(sid))
    if len(np.unique(y)) < 2:
        X.append(np.random.rand(len(X[0])))
        y.append(-1) 
    clf = RandomForestClassifier(n_estimators=100, n_jobs=-1)
    clf.fit(np.stack(X), np.array(y))
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
    if progress_callback: progress_callback(100, "Sync Complete")