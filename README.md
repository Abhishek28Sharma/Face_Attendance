# ATTENDIQ

<img width="1919" height="993" alt="image" src="https://github.com/Abhishek28Sharma/Face_Attendance/blob/main/bg.png" />

# Face Recognition Based Attendance System

A real-time face recognition–based attendance system using **MediaPipe**, **Random Forest Classifier**, and **OpenCV**. The system detects faces from a live camera feed, identifies students with high confidence, and automatically marks attendance.

---

## Features

- Real-time face detection using MediaPipe  
- Robust facial embedding extraction  
- Identity classification using Random Forest  
- Confidence-based attendance validation  
- CPU-efficient (no GPU required)  
- Persistent trained model for reuse  

---

## Face Detection Methodology

### MediaPipe Face Detection

MediaPipe Face Detection is selected due to its high accuracy, low computational overhead, and real-time performance on CPU. It provides pre-trained TensorFlow Lite (TFLite) models optimized for fast inference and efficient deployment.

**Advantages:**
- High detection accuracy under varying lighting and poses  
- Low latency suitable for live video streams  
- Lightweight and CPU-friendly  
- No GPU dependency  

---

### Detection Process

1. Input image is converted to RGB format  
2. MediaPipe detects faces and returns bounding boxes  
3. Only detections above the confidence threshold are considered  

```python
min_detection_confidence = 0.5


## 7. Machine Learning Algorithm Used

### Random Forest Classifier

The Random Forest classifier is used as the core machine learning algorithm for identity recognition. It is an ensemble learning method that combines multiple decision trees to improve classification accuracy and robustness.

By aggregating the predictions of several independent decision trees, Random Forest reduces the risk of overfitting and provides stable and reliable classification results.

---

### Key Characteristics

- Uses **bagging (bootstrap aggregation)** to create diverse decision trees  
- Reduces variance and overfitting compared to single decision trees  
- Works efficiently with high-dimensional feature vectors such as facial embeddings  
- Naturally supports **multi-class classification**, making it suitable for identifying multiple students  

---

### Why Random Forest Over Deep Learning?

Random Forest is preferred over deep learning models due to the following reasons:

- Requires a **smaller dataset** for effective training  
- Faster training and inference time  
- No dependency on GPU hardware  
- Provides better **interpretability** through feature importance  

---

## 8. Model Training Process

### Training Workflow

The model training process follows a structured pipeline:

1. Load the student image dataset  
2. Detect faces in each image using a face detection model  
3. Extract and normalize facial embeddings  
4. Assign class labels corresponding to student IDs  
5. Train the Random Forest classifier using the labeled embeddings  
6. Save the trained model using Pickle  

---

### Model Persistence

After training, the model is saved as `model.pkl`. This allows the system to reuse the trained classifier without retraining each time the application runs.

This approach improves efficiency and supports incremental dataset updates when new student data is added.

---

## 10. Real-Time Prediction & Attendance Marking

During attendance marking, the trained model is deployed for real-time face recognition using a live camera feed. The system ensures that attendance is recorded only when predictions are reliable.

---

### Real-Time Prediction Workflow

1. Live camera feed is captured continuously  
2. Faces are detected in each frame  
3. Facial embeddings are generated in real time  
4. The trained model predicts the student identity and confidence score  
5. Attendance is marked only if the confidence exceeds a predefined threshold  

---

### Real-Time Attendance Flow Diagram

```mermaid
flowchart TD
    A[Live Camera Feed] --> B[Face Detection<br/>(MediaPipe)]
    B --> C[Face Embedding Extraction]
    C --> D[Random Forest Classifier]
    D --> E{Confidence > Threshold?}
    E -- Yes --> F[Mark Attendance]
    E -- No --> G[Ignore Prediction]
```
Prediction Output

For each valid recognition, the system produces:

Student ID – The unique identifier of the recognized student

Prediction Confidence – A score representing prediction reliability
✅ Provides real-time data & analytics 📈
✅ Scalable for institutions of any size 🌍
