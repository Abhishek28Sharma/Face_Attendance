import os
import cv2
import numpy as np
import pickle
from sklearn.ensemble import RandomForestClassifier

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Configuration constants
MODEL_PATH = "model.pkl"
FACE_DETECTOR_MODEL = "face_detector.tflite"

def create_face_detector():
    """Initializes the MediaPipe Face Detector task."""
    base_options = python.BaseOptions(model_asset_path=FACE_DETECTOR_MODEL)
    options = vision.FaceDetectorOptions(
        base_options=base_options,
        min_detection_confidence=0.5
    )
    return vision.FaceDetector.create_from_options(options)

def crop_face_and_embed(bgr_image, detection):
    """
    Crops the detected face and creates a simple flattened pixel embedding.
    Standardizes the image to 32x32 grayscale for the classifier.
    """
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

    # Normalize pixel values to [0, 1]
    return face.flatten().astype(np.float32) / 255.0

def extract_embedding_for_image(stream):
    """Processes a single image stream for live recognition."""
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
    """Loads the trained Random Forest model from disk."""
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)

def predict_with_model(clf, emb):
    """Predicts the student identity and returns confidence score."""
    proba = clf.predict_proba([emb])[0]
    idx = np.argmax(proba)
    return clf.classes_[idx], float(proba[idx])

# --- UPDATED RECURSIVE TRAINING LOGIC ---
def train_model_background(dataset_dir, progress_callback=None):
    """
    Scans dataset_dir recursively using os.walk to find images in nested folders.
    The immediate parent folder name (Roll Number) is used as the label.
    """
    detector = create_face_detector()
    X, y = [], []

    # Step 1: Collect all valid image paths across all nested subfolders
    all_files = []
    for root, dirs, files in os.walk(dataset_dir):
        for fn in files:
            if fn.lower().endswith((".jpg", ".png", ".jpeg")):
                all_files.append(os.path.join(root, fn))
    
    total_files = len(all_files)
    if total_files == 0:
        if progress_callback:
            progress_callback(0, "No images found in dataset. Check folder structure.")
        return

    # Step 2: Process each image to extract facial features
    processed = 0
    for file_path in all_files:
        # The immediate parent folder name is the student identifier (Roll Number)
        # Structure: dataset/YEAR/MONTH/SEMESTER/BRANCH/ROLL_NO/image.jpg
        root_dir = os.path.dirname(file_path)
        student_roll = os.path.basename(root_dir)

        img = cv2.imread(file_path)
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
        # Labels are strings to support alphanumeric roll numbers
        y.append(str(student_roll))

        processed += 1
        if progress_callback and processed % 5 == 0:
            percent = int((processed / total_files) * 100)
            progress_callback(percent, f"Processing {processed}/{total_files} images...")

    if not X:
        if progress_callback:
            progress_callback(0, "No valid faces detected. Training aborted.")
        return

    # Step 3: Train the Random Forest Classifier
    if progress_callback:
        progress_callback(90, "Fitting AI model...")
        
    clf = RandomForestClassifier(n_estimators=150, n_jobs=-1, random_state=42)
    clf.fit(np.stack(X), np.array(y))

    # Step 4: Save the model to disk
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)

    if progress_callback:
        progress_callback(100, "Training complete!")