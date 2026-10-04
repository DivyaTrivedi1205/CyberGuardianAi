"""
Advanced Video Deepfake Analysis Module

Phase 8: Frame-level analysis with face detection and temporal analysis.
Uses OpenCV for video frame extraction and Haar Cascade for face detection.

This module extends the basic Phase 7 deepfake analyzer to provide:
- Controlled frame sampling
- Face detection and face-region analysis
- Temporal consistency checking
- Evidence-based aggregation
"""

import hashlib
import os
import io
import tempfile
import shutil
import numpy as np
import cv2
from PIL import Image
from typing import Dict, Any, List, Tuple, Optional
from scipy.ndimage import laplace
from torchvision import transforms
import torch


# Configuration for video analysis
MAX_VIDEO_DURATION = 60.0  # seconds
MAX_FRAMES_TO_ANALYZE = 15
FRAME_SAMPLE_INTERVAL = 5  # sample every N seconds for short videos
FRAME_SAMPLE_INTERVAL_LONG = 15  # for longer videos


# Common metadata signatures/markers for AI image/video generators and editors
AI_SIGNATURES = [
    b"dall-e",
    b"midjourney",
    b"stable diffusion",
    b"comfyui",
    b"automatic1111",
    b"adobe firefly",
    b"photoshop",
    b"generative ai",
    b"artificial intelligence",
    b"deepfacelab",
    b"faceswap",
    b"ebsynth",
    b"deepfake",
    b"runwayml",
    b"pika labs",
]


# Face detection configuration
def _get_haar_cascade_path() -> str:
    """Get path to Haar Cascade XML file."""
    cascade_dir = os.path.join(os.path.dirname(__file__), "assets")
    os.makedirs(cascade_dir, exist_ok=True)
    custom_path = os.path.join(cascade_dir, "haarcascade_frontalface_default.xml")

    # Try OpenCV's default locations
    import cv2
    if hasattr(cv2, 'data') and cv2.data.haarcascades:
        default_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
        if os.path.exists(default_path):
            if not os.path.exists(custom_path):
                shutil.copy2(default_path, custom_path)
            return custom_path

    return custom_path


def _detect_faces_cv2(img: np.ndarray) -> List[Dict[str, Any]]:
    """
    Detect faces using OpenCV Haar Cascade.

    Args:
        img: RGB image as numpy array

    Returns:
        List of face dictionaries with bounding box and confidence
    """
    try:
        cascade_path = _get_haar_cascade_path()
        if not os.path.exists(cascade_path):
            return []

        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            return []

        # Convert RGB to BGR for OpenCV
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        face_regions = []
        for (x, y, w, h) in faces:
            face_regions.append({
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h),
                'confidence': 1.0,
                'area': int(w * h)
            })

        return face_regions
    except Exception:
        return []


def _extract_face_region(img: np.ndarray, face: Dict[str, Any], padding: float = 0.3) -> np.ndarray:
    """
    Extract face region with padding.

    Args:
        img: Full image as numpy array
        face: Face bounding box dictionary
        padding: Extra padding as fraction of face size

    Returns:
        Cropped face region as numpy array
    """
    x, y = face['x'], face['y']
    w, h = face['width'], face['height']

    # Add padding
    pad_x = int(w * padding)
    pad_y = int(h * padding)

    # Calculate crop coordinates
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(img.shape[1], x + w + pad_x)
    y2 = min(img.shape[0], y + h + pad_y)

    return img[y1:y2, x1:x2]


def _compute_face_region_forensics(face_img: np.ndarray) -> Dict[str, int]:
    """
    Compute forensic features specifically for face regions.

    Args:
        face_img: Face region image as numpy array

    Returns:
        Dictionary of face-region forensic scores
    """
    try:
        face_gray = cv2.cvtColor(face_img, cv2.COLOR_RGB2GRAY)
        face_gray_256 = cv2.resize(face_gray, (256, 256))

        # Compute noise in face region
        res = laplace(face_gray_256.astype(np.float32))
        h, w = res.shape
        block_h, block_w = h // 8, w // 8
        variances = []
        for i in range(8):
            for j in range(8):
                block = res[i * block_h:(i + 1) * block_h, j * block_w:(j + 1) * block_w]
                variances.append(np.var(block))
        variances = np.array(variances)
        mean_var = np.mean(variances)
        std_var = np.std(variances)
        noise_inconsistency = std_var / (mean_var + 1e-6)

        # Compute ELA on face region
        img_pil = Image.fromarray(face_img)
        buf = io.BytesIO()
        img_pil.save(buf, format="JPEG", quality=90)
        buf.seek(0)
        compressed_img = Image.open(buf)
        orig_arr = np.array(img_pil).astype(np.float32)
        comp_arr = np.array(compressed_img).astype(np.float32)
        diff = np.abs(orig_arr - comp_arr)
        diff_gray = np.mean(diff, axis=2)
        diff_gray_resized = np.array(
            Image.fromarray(diff_gray.astype(np.uint8)).resize((128, 128))
        )
        h, w = diff_gray_resized.shape
        block_h, block_w = h // 8, w // 8
        ela_variances = []
        for i in range(8):
            for j in range(8):
                block = diff_gray_resized[i * block_h:(i + 1) * block_h, j * block_w:(j + 1) * block_w]
                ela_variances.append(np.var(block))
        ela_variances = np.array(ela_variances)
        ela_mean = np.mean(ela_variances)
        ela_std = np.std(ela_variances)
        ela_inconsistency = ela_std / (ela_mean + 1e-6)

        # Face-specific anomaly scores
        face_blending_score = int(np.clip((noise_inconsistency - 0.3) / 0.4 * 100 + 10, 5, 95))
        face_ela_score = int(np.clip((ela_inconsistency - 0.4) / 0.4 * 100 + 10, 5, 95))
        skin_smoothness = int(np.clip(70 - mean_var * 20, 5, 95))

        return {
            'face_blending_score': face_blending_score,
            'face_ela_score': face_ela_score,
            'face_skin_smoothness': skin_smoothness,
            'face_noise_inconsistency': float(noise_inconsistency),
            'face_ela_inconsistency': float(ela_inconsistency)
        }
    except Exception:
        return {
            'face_blending_score': 50,
            'face_ela_score': 50,
            'face_skin_smoothness': 50,
            'face_noise_inconsistency': 0.0,
            'face_ela_inconsistency': 0.0
        }


def _analyze_image_for_video(
    img: Image.Image,
    file_hash: str
) -> Dict[str, Any]:
    """
    Run image analysis on a single frame for video processing.

    Args:
        img: PIL Image
        file_hash: File hash for metadata

    Returns:
        Dictionary with analysis results
    """
    feedback: List[str] = []
    features: Dict[str, int] = {}

    # EXIF analysis
    has_genuine_camera = False
    camera_tags = []
    try:
        exif = img.getexif()
        if exif:
            for tag_id, val in exif.items():
                val_str = str(val).strip()
                if not val_str:
                    continue
                if tag_id == 271:
                    camera_tags.append(f"Make: {val_str}")
                    if any(brand in val_str.lower() for brand in [
                        "canon", "nikon", "sony", "apple", "samsung", "google",
                        "huawei", "oneplus", "xiaomi", "oppo", "vivo", "fujifilm",
                        "leica", "panasonic", "olympus"
                    ]):
                        has_genuine_camera = True
                elif tag_id == 272:
                    camera_tags.append(f"Model: {val_str}")
                    has_genuine_camera = True
    except Exception:
        pass
    has_exif = len(camera_tags) > 0

    # Forensic features
    img_gray = img.convert("L")
    img_gray_256 = np.array(img_gray.resize((256, 256)))

    # FFT analysis
    f = np.fft.fft2(img_gray_256)
    fshift = np.fft.fftshift(f)
    magnitude = np.abs(fshift)
    y, x = np.indices(magnitude.shape)
    cy, cx = magnitude.shape[0] // 2, magnitude.shape[1] // 2
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    high_freq_vals = magnitude[r > 90]
    if len(high_freq_vals) > 0:
        papr = float(np.max(high_freq_vals) / (np.mean(high_freq_vals) + 1e-6))
    else:
        papr = 1.0

    # Noise analysis
    res = laplace(img_gray_256.astype(np.float32))
    h, w = res.shape
    block_h, block_w = h // 8, w // 8
    variances = []
    for i in range(8):
        for j in range(8):
            block = res[i * block_h:(i + 1) * block_h, j * block_w:(j + 1) * block_w]
            variances.append(np.var(block))
    variances = np.array(variances)
    mean_var = np.mean(variances)
    std_var = np.std(variances)
    noise_inconsistency = std_var / (mean_var + 1e-6)

    # ELA
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    compressed_img = Image.open(buf)
    orig_arr = np.array(img.convert("RGB")).astype(np.float32)
    comp_arr = np.array(compressed_img).astype(np.float32)
    diff = np.abs(orig_arr - comp_arr)
    diff_gray = np.mean(diff, axis=2)
    diff_gray_resized = np.array(Image.fromarray(diff_gray.astype(np.uint8)).resize((256, 256)))
    h, w = diff_gray_resized.shape
    block_h, block_w = h // 8, w // 8
    ela_variances = []
    for i in range(8):
        for j in range(8):
            block = diff_gray_resized[i * block_h:(i + 1) * block_h, j * block_w:(j + 1) * block_w]
            ela_variances.append(np.var(block))
    ela_variances = np.array(ela_variances)
    ela_mean = np.mean(ela_variances)
    ela_std = np.std(ela_variances)
    ela_inconsistency = ela_std / (ela_mean + 1e-6)

    # Channel correlation
    img_arr = np.array(img).astype(np.float32)
    r_chan = img_arr[:, :, 0].ravel()
    g_chan = img_arr[:, :, 1].ravel()
    b_chan = img_arr[:, :, 2].ravel()

    if len(r_chan) > 1 and np.std(r_chan) > 0 and np.std(g_chan) > 0 and np.std(b_chan) > 0:
        corr_rg = np.corrcoef(r_chan, g_chan)[0, 1]
        corr_gb = np.corrcoef(g_chan, b_chan)[0, 1]
        corr_br = np.corrcoef(b_chan, r_chan)[0, 1]
        min_corr = min(corr_rg, corr_gb, corr_br)
    else:
        min_corr = 1.0

    # Compute scores
    edge_blending_score = int(np.clip((noise_inconsistency - 0.45) / 0.6 * 80 + 10, 5, 95))
    eye_reflection_score = int(np.clip((1.0 - min_corr) * 150, 5, 95))
    skin_smooth_score = int(70 - np.clip((mean_var - 0.5) / 8.0 * 65, 0, 65))
    bg_warping_score = int(np.clip((ela_inconsistency - 0.55) / 0.6 * 80 + 10, 5, 95))

    metadata_score = 10
    if not has_exif:
        metadata_score = 45
        feedback.append("Missing EXIF Metadata: File lacks standard camera capture tags.")

    if papr > 15.0:
        metadata_score = max(metadata_score, 70)
        feedback.append(f"Fourier Grid Spikes: FFT power spectrum shows sharp periodic peaks (PAPR: {papr:.1f}).")

    features["Edge Blending"] = edge_blending_score
    features["Eye Reflection Asymmetry"] = eye_reflection_score
    features["Skin Texture Smoothness"] = skin_smooth_score
    features["Background Warping"] = bg_warping_score
    features["Metadata Anomalies"] = metadata_score

    # Load CNN model
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from services.deepfake_model import DeepfakeCNN

        model = DeepfakeCNN()
        cnn_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "models", "deepfake_cnn.pth")
        )

        if os.path.exists(cnn_path):
            try:
                state_dict = torch.load(cnn_path, map_location=torch.device('cpu'), weights_only=True)
                model.load_state_dict(state_dict)
                model.eval()
            except Exception:
                model.load_state_dict(torch.load(cnn_path, map_location=torch.device('cpu')))
                model.eval()

        transform = transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        input_tensor = transform(img).unsqueeze(0)
        with torch.no_grad():
            outputs = model(input_tensor)
            probs = torch.softmax(outputs, dim=1).numpy()[0]

        cnn_risk_score = int(probs[1] * 100)
    except Exception:
        cnn_risk_score = 50

    # Combine scores
    raw_risk = cnn_risk_score
    forensics_anomaly_avg = (edge_blending_score + bg_warping_score) / 2.0
    if forensics_anomaly_avg > 80 and raw_risk < 50:
        raw_risk = int(raw_risk * 0.6 + forensics_anomaly_avg * 0.4)
        feedback.append("Localized Compression/Noise Mismatch: Pixel structures suggest manipulation.")

    if has_genuine_camera and raw_risk < 85:
        raw_risk = max(3, int(raw_risk * 0.3))

    risk_score = int(np.clip(raw_risk, 0, 100))

    if risk_score >= 65:
        prediction = "AI Generated"
    elif risk_score >= 35:
        prediction = "Suspicious"
    else:
        prediction = "Authentic"

    if edge_blending_score >= 65:
        feedback.append("Double Edge Boundaries: High noise variance around boundaries.")
    if eye_reflection_score >= 65:
        feedback.append("Color Spectrum Discrepancy: Abnormal channel correlations.")
    if skin_smooth_score >= 65:
        feedback.append("Ultra-Smooth Textures: Unnatural skin smoothing detected.")
    if bg_warping_score >= 65:
        feedback.append("JPEG Compression Boundary: ELA indicates secondary compression.")

    if not feedback:
        feedback.append("No obvious AI anomalies detected.")

    return {
        'risk_score': risk_score,
        'prediction': prediction,
        'feedback': feedback,
        'features': features,
        'has_genuine_camera': has_genuine_camera
    }


def _sample_video_frames(
    video_bytes: bytes,
    file_name: str,
    max_duration: float = MAX_VIDEO_DURATION,
    max_frames: int = MAX_FRAMES_TO_ANALYZE
) -> List[Tuple[np.ndarray, float, int]]:
    """
    Sample video frames at controlled intervals.

    Args:
        video_bytes: Video file bytes
        file_name: Original file name
        max_duration: Maximum duration to process in seconds
        max_frames: Maximum number of frames to extract

    Returns:
        List of (frame_array, timestamp_seconds, frame_index) tuples
    """
    temp_dir = None
    frames = []

    try:
        temp_dir = tempfile.mkdtemp()
        video_path = os.path.join(temp_dir, f"temp_video_{hashlib.md5(video_bytes[:100]).hexdigest()[:8]}.mp4")

        with open(video_path, 'wb') as f:
            f.write(video_bytes)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("Failed to open video file")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        duration = total_frames / fps

        duration = min(duration, max_duration)
        max_frame_to_process = int(duration * fps)

        if duration <= 30:
            sample_interval = 1
        elif duration <= 60:
            sample_interval = max(1, int(fps / 3))
        else:
            sample_interval = max(1, int(fps * FRAME_SAMPLE_INTERVAL_LONG / 60))

        frame_indices = list(range(0, min(max_frame_to_process, total_frames), sample_interval))

        if len(frame_indices) > max_frames:
            step = len(frame_indices) / max_frames
            frame_indices = [int(i * step) for i in range(max_frames)]

        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()

            if not ret:
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            timestamp = idx / fps

            frames.append((frame_rgb, timestamp, idx))

        cap.release()

    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    return frames


def _calculate_temporal_consistency(frame_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze temporal consistency across frames.

    Args:
        frame_results: List of frame analysis results

    Returns:
        Dictionary with temporal analysis results
    """
    if len(frame_results) < 2:
        return {
            'is_consistent': True,
            'anomalies_found': 0,
            'explanations': ['Insufficient frames for temporal analysis'],
            'frames_analyzed': len(frame_results)
        }

    anomalies = []
    explanations = []

    risk_scores = [f['risk_score'] for f in frame_results]
    mean_risk = np.mean(risk_scores)
    std_risk = np.std(risk_scores)

    if std_risk > 25:
        anomalies.append({
            'type': 'risk_score_variance',
            'value': float(std_risk),
            'severity': 'high' if std_risk > 40 else 'medium'
        })
        explanations.append(
            f"High risk score variance detected across frames (std: {std_risk:.1f}). "
            "Normal videos typically have more consistent risk profiles."
        )

    face_frames = [f for f in frame_results if f.get('has_face', False)]
    if len(face_frames) > 1:
        face_risks = [f['risk_score'] for f in face_frames]
        face_std = np.std(face_risks)

        if face_std > 20:
            anomalies.append({
                'type': 'face_risk_variance',
                'value': float(face_std),
                'severity': 'medium'
            })
            explanations.append(
                f"Face region analysis shows inconsistent risk scores (std: {face_std:.1f}). "
                "Verify if face characteristics remain consistent throughout the video."
            )

    face_detection_consistent = all(f.get('faces_detected', 0) == face_frames[0].get('faces_detected', 0)
                                     for f in face_frames) if face_frames else True

    if not face_detection_consistent:
        anomalies.append({
            'type': 'face_detection_inconsistency',
            'value': 'variable',
            'severity': 'medium'
        })
        explanations.append(
            "Number of detected faces varies across frames. "
            "This could indicate frame manipulation or face swapping."
        )

    return {
        'is_consistent': len(anomalies) == 0,
        'anomalies_found': len(anomalies),
        'anomaly_details': anomalies,
        'explanations': explanations if explanations else ['Temporal analysis shows consistent patterns'],
        'frames_analyzed': len(frame_results),
        'risk_mean': float(mean_risk),
        'risk_std': float(std_risk)
    }


def _aggregate_video_score(
    frame_results: List[Dict[str, Any]],
    temporal_analysis: Dict[str, Any],
    ai_signatures: List[str],
    file_hash: str
) -> Dict[str, Any]:
    """
    Aggregate frame-level results into video-level assessment.

    Args:
        frame_results: List of frame analysis results
        temporal_analysis: Temporal consistency results
        ai_signatures: Detected AI signatures
        file_hash: File hash

    Returns:
        Dictionary with aggregated video score and evidence
    """
    if not frame_results:
        return {
            'risk_score': 50,
            'prediction': 'Inconclusive',
            'frames_analyzed': 0,
            'total_frames': 0,
            'evidence': {
                'metadata': [],
                'forensics': [],
                'model': [],
                'faces': [],
                'temporal': []
            },
            'suspicious_frames': [],
            'explanations': ['No frames were successfully analyzed']
        }

    risk_scores = [f['risk_score'] for f in frame_results]
    median_risk = int(np.median(risk_scores))
    mean_risk = int(np.mean(risk_scores))
    max_risk = int(np.max(risk_scores))
    min_risk = int(np.min(risk_scores))

    suspicious_count = sum(1 for r in risk_scores if r >= 35)
    high_risk_count = sum(1 for r in risk_scores if r >= 65)
    suspicious_proportion = suspicious_count / len(risk_scores)

    metadata_evidence = []
    forensics_evidence = []
    model_evidence = []
    face_evidence = []
    temporal_evidence = []

    for frame in frame_results:
        for feedback in frame.get('indicators', []):
            if 'EXIF' in feedback or 'Fourier' in feedback:
                metadata_evidence.append({
                    'frame': frame['frame_index'],
                    'timestamp': frame['timestamp'],
                    'indicator': feedback
                })

        for feature_name, value in frame.get('forensic_features', {}).items():
            if value >= 65:
                forensics_evidence.append({
                    'frame': frame['frame_index'],
                    'timestamp': frame['timestamp'],
                    'feature': feature_name,
                    'value': value
                })

        if frame.get('classification') in ['Suspicious', 'AI Generated']:
            model_evidence.append({
                'frame': frame['frame_index'],
                'timestamp': frame['timestamp'],
                'prediction': frame['classification'],
                'risk_score': frame['risk_score']
            })

        for face in frame.get('face_evidence', []):
            if face.get('composite_face_risk', 0) >= 50:
                face_evidence.append({
                    'frame': frame['frame_index'],
                    'timestamp': frame['timestamp'],
                    'face_index': face.get('face_index', 0),
                    'risk': face.get('composite_face_risk', 0),
                    'indicators': face.get('forensic_scores', {})
                })

        for anomaly in temporal_analysis.get('anomaly_details', []):
            if anomaly['type'] in ['risk_score_variance', 'face_risk_variance']:
                temporal_evidence.append({
                    'anomaly_type': anomaly['type'],
                    'timestamp': frame['timestamp'],
                    'value': anomaly.get('value', 'N/A')
                })

    explanations = []

    if ai_signatures:
        explanations.append(f"AI signature detected in video metadata: {', '.join(set(ai_signatures))}")

    explanations.append(
        f"Analyzed {len(frame_results)} frames. "
        f"Median risk score: {median_risk}/100."
    )

    if suspicious_proportion > 0.5:
        explanations.append(
            f"{suspicious_count}/{len(frame_results)} frames ({suspicious_proportion*100:.0f}%) "
            "show elevated forensic anomalies."
        )

    if face_evidence:
        explanations.append(
            f"Face-region analysis found {len(face_evidence)} frames with "
            "potential face-manipulation artifacts."
        )

    if temporal_analysis.get('anomalies_found', 0) > 0:
        explanations.append(
            f"Temporal analysis identified {temporal_analysis['anomalies_found']} "
            "inconsistencies across frames."
        )

    if not explanations:
        explanations.append("No significant anomalies detected across analyzed frames.")

    # Weighted aggregation
    face_weight = 1.5 if face_evidence else 1.0
    temporal_weight = 1.2 if temporal_analysis.get('anomalies_found', 0) > 0 else 1.0

    weighted_scores = []
    for frame in frame_results:
        base_score = frame['risk_score']
        if any(f.get('frame_index') == frame['frame_index'] for f in face_evidence):
            base_score = min(100, base_score * 1.2)
        weighted_scores.append(base_score)

    final_risk = int(
        0.4 * median_risk +
        0.3 * np.mean(weighted_scores) +
        0.2 * max_risk +
        0.1 * (100 if high_risk_count > 0 else 0)
    )

    if face_evidence:
        final_risk = min(100, final_risk + 10)
    if temporal_analysis.get('anomalies_found', 0) > 1:
        final_risk = min(100, final_risk + 15)

    if final_risk >= 70 or ai_signatures:
        prediction = "AI Generated"
    elif final_risk >= 40:
        prediction = "Suspicious"
    elif final_risk >= 25:
        prediction = "Inconclusive"
    else:
        prediction = "Authentic"

    suspicious_frames = []
    for frame in frame_results:
        if frame['risk_score'] >= 40:
            suspicious_frames.append({
                'timestamp': frame['timestamp'],
                'frame_index': frame['frame_index'],
                'risk_score': frame['risk_score'],
                'indicators': frame.get('indicators', [])[:3]
            })

    return {
        'risk_score': final_risk,
        'prediction': prediction,
        'frames_analyzed': len(frame_results),
        'total_frames': len(frame_results),
        'median_risk': median_risk,
        'max_risk': max_risk,
        'evidence': {
            'metadata': metadata_evidence,
            'forensics': forensics_evidence,
            'model': model_evidence,
            'faces': face_evidence,
            'temporal': temporal_evidence
        },
        'suspicious_frames': suspicious_frames[:5],
        'explanations': explanations,
        'temporal_consistency': temporal_analysis
    }


def analyze_deepfake_video(
    file_bytes: bytes,
    file_name: str,
    content_type: str
) -> Dict[str, Any]:
    """
    Advanced video deepfake analysis with frame-level analysis.

    Args:
        file_bytes: Video file bytes
        file_name: Original file name
        content_type: MIME type

    Returns:
        Dictionary with comprehensive video analysis results
    """
    file_name_lower = file_name.lower()

    is_video = "video" in content_type.lower() or any(
        file_name_lower.endswith(ext)
        for ext in [".mp4", ".mov", ".avi", ".webm", ".mkv"]
    )

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    meta_search_bytes = file_bytes[:65536].lower() + file_bytes[-4096:].lower()
    ai_tag_matches = []
    for sig in AI_SIGNATURES:
        if sig in meta_search_bytes:
            ai_tag_matches.append(sig.decode("utf-8", errors="ignore"))

    if is_video:
        try:
            frames = _sample_video_frames(file_bytes, file_name)

            if not frames:
                return {
                    'prediction': 'Inconclusive',
                    'risk_score': 50,
                    'feedback': ['Failed to extract any frames from video. File may be corrupted.'],
                    'features': {},
                    'file_type': 'video',
                    'metadata': {
                        'file_size_bytes': len(file_bytes),
                        'file_name': file_name,
                        'content_type': content_type,
                        'sha256_hash': file_hash,
                        'frames_analyzed': 0,
                        'duration': 'N/A'
                    },
                    'evidence': {
                        'metadata': [],
                        'forensics': [],
                        'model': [],
                        'faces': [],
                        'temporal': []
                    },
                    'suspicious_frames': []
                }

            frame_results = []
            for idx, (frame_arr, timestamp, frame_idx) in enumerate(frames):
                img = Image.fromarray(frame_arr)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=95)
                frame_bytes_for_analysis = buf.getvalue()

                result = _analyze_single_frame(
                    frame_bytes_for_analysis,
                    frame_idx,
                    timestamp,
                    file_hash
                )
                frame_results.append(result)

            temporal_analysis = _calculate_temporal_consistency(frame_results)
            video_result = _aggregate_video_score(
                frame_results,
                temporal_analysis,
                ai_tag_matches,
                file_hash
            )

            feedback = video_result['explanations'][:]

            if temporal_analysis.get('explanations'):
                feedback.extend(temporal_analysis['explanations'])

            if not feedback:
                feedback.append("No obvious AI anomalies detected in analyzed frames.")

            return {
                'prediction': video_result['prediction'],
                'risk_score': video_result['risk_score'],
                'feedback': feedback,
                'features': {
                    'frames_analyzed': video_result['frames_analyzed'],
                    'median_risk': video_result['median_risk'],
                    'max_risk': video_result['max_risk'],
                    'temporal_consistency': 1 if temporal_analysis['is_consistent'] else 0,
                    'face_evidence_count': len(video_result['evidence']['faces'])
                },
                'file_type': 'video',
                'metadata': {
                    'file_size_bytes': len(file_bytes),
                    'file_name': file_name,
                    'content_type': content_type,
                    'sha256_hash': file_hash,
                    'frames_analyzed': video_result['frames_analyzed'],
                    'duration': 'N/A',
                    'ai_signatures_detected': ai_tag_matches if ai_tag_matches else None
                },
                'evidence': video_result['evidence'],
                'suspicious_frames': video_result['suspicious_frames']
            }

        except Exception as e:
            return {
                'prediction': 'Suspicious',
                'risk_score': 50,
                'feedback': [
                    f"Frame extraction failed: {str(e)[:100]}. "
                    "Falling back to metadata analysis only."
                ],
                'features': {
                    'frames_analyzed': 0,
                    'fallback_reason': str(e)[:100]
                },
                'file_type': 'video',
                'metadata': {
                    'file_size_bytes': len(file_bytes),
                    'file_name': file_name,
                    'content_type': content_type,
                    'sha256_hash': file_hash
                },
                'evidence': {
                    'metadata': [],
                    'forensics': [],
                    'model': [],
                    'faces': [],
                    'temporal': []
                },
                'suspicious_frames': []
            }
    else:
        # Should not reach here, but handle image mode
        return analyze_deepfake_image(file_bytes, file_name, content_type)


def _analyze_single_frame(
    frame_bytes: bytes,
    frame_index: int,
    timestamp: float,
    file_hash: str
) -> Dict[str, Any]:
    """
    Analyze a single frame using the existing Phase 7 image analysis.

    Args:
        frame_bytes: Frame image bytes
        frame_index: Frame number in video
        timestamp: Timestamp in seconds
        file_hash: Hash of the original file

    Returns:
        Dictionary with frame analysis results
    """
    try:
        img = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
        img_arr = np.array(img).astype(np.float32)

        faces = _detect_faces_cv2(img_arr)

        analysis = _analyze_image_for_video(img, file_hash)

        face_evidence = []
        if faces:
            for face_idx, face in enumerate(faces):
                face_region = _extract_face_region(img_arr, face)
                face_forensics = _compute_face_region_forensics(face_region)

                face_evidence.append({
                    'face_index': face_idx,
                    'bounding_box': {
                        'x': face['x'],
                        'y': face['y'],
                        'width': face['width'],
                        'height': face['height']
                    },
                    'forensic_scores': face_forensics,
                    'composite_face_risk': int(
                        (face_forensics['face_blending_score'] +
                         face_forensics['face_ela_score'] +
                         face_forensics['face_skin_smoothness']) / 3
                    )
                })

        return {
            'frame_index': frame_index,
            'timestamp': round(timestamp, 2),
            'risk_score': analysis['risk_score'],
            'classification': analysis['prediction'],
            'indicators': analysis['feedback'],
            'forensic_features': analysis['features'],
            'faces_detected': len(faces),
            'face_evidence': face_evidence,
            'has_face': len(faces) > 0
        }
    except Exception as e:
        return {
            'frame_index': frame_index,
            'timestamp': round(timestamp, 2),
            'risk_score': 50,
            'classification': 'Inconclusive',
            'indicators': [f'Frame analysis error: {str(e)[:100]}'],
            'forensic_features': {},
            'faces_detected': 0,
            'face_evidence': [],
            'has_face': False
        }


def analyze_deepfake_image(
    file_bytes: bytes,
    file_name: str,
    content_type: str
) -> Dict[str, Any]:
    """
    Run Phase 7 image analysis for fallback.

    Args:
        file_bytes: Image file bytes
        file_name: Original file name
        content_type: MIME type

    Returns:
        Dictionary with image analysis results
    """
    return analyze_deepfake_image_original(file_bytes, file_name, content_type)


def analyze_deepfake_image_original(
    file_bytes: bytes,
    file_name: str,
    content_type: str
) -> Dict[str, Any]:
    """
    Original Phase 7 image analysis (for fallback).
    """
    file_name_lower = file_name.lower()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    feedback: List[str] = []
    features: Dict[str, int] = {}

    ai_tag_matches = []
    for sig in AI_SIGNATURES:
        if sig in file_bytes:
            ai_tag_matches.append(sig.decode("utf-8", errors="ignore"))

    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    except Exception:
        return {
            "prediction": "Suspicious",
            "risk_score": 50,
            "feedback": ["Failed to decode image bytes for forensics analysis."],
            "features": {
                "Edge Blending": 50,
                "Eye Reflection Asymmetry": 50,
                "Skin Texture Smoothness": 50,
                "Background Warping": 50,
                "Metadata Anomalies": 50,
            },
            "file_type": "image",
            "metadata": {
                "file_size_bytes": len(file_bytes),
                "file_name": file_name,
                "content_type": content_type,
                "sha256_hash": file_hash,
            },
        }

    has_genuine_camera, camera_tags = extract_exif_metadata(img)
    has_exif = len(camera_tags) > 0

    img_gray = img.convert("L")
    img_gray_256 = np.array(img_gray.resize((256, 256)))

    fft_papr = compute_fft_peak_ratio(img_gray_256)
    noise_inconsistency, noise_mean = compute_noise_inconsistency(img_gray_256)
    ela_inconsistency = compute_ela_features(img)

    img_arr = np.array(img).astype(np.float32)
    r_chan = img_arr[:, :, 0].ravel()
    g_chan = img_arr[:, :, 1].ravel()
    b_chan = img_arr[:, :, 2].ravel()

    if len(r_chan) <= 1 or np.std(r_chan) == 0 or np.std(g_chan) == 0 or np.std(b_chan) == 0:
        min_corr = 1.0
    else:
        corr_rg = np.corrcoef(r_chan, g_chan)[0, 1]
        corr_gb = np.corrcoef(g_chan, b_chan)[0, 1]
        corr_br = np.corrcoef(b_chan, r_chan)[0, 1]
        if np.isnan(corr_rg) or np.isnan(corr_gb) or np.isnan(corr_br):
            min_corr = 1.0
        else:
            min_corr = min(corr_rg, corr_gb, corr_br)

    edge_blending_score = int(
        np.clip((noise_inconsistency - 0.45) / 0.6 * 80 + 10, 5, 95)
    )
    eye_reflection_score = int(np.clip((1.0 - min_corr) * 150, 5, 95))
    skin_smooth_score = int(70 - np.clip((noise_mean - 0.5) / 8.0 * 65, 0, 65))
    bg_warping_score = int(
        np.clip((ela_inconsistency - 0.55) / 0.6 * 80 + 10, 5, 95)
    )
    metadata_score = 10
    if not has_exif:
        metadata_score = 45
        feedback.append(
            "Missing EXIF Metadata: File lacks standard camera capture tags (model, aperture, GPS) typical of genuine device photos."
        )
    elif has_genuine_camera:
        metadata_score = 5

    if fft_papr > 15.0:
        metadata_score = max(metadata_score, 70)
        feedback.append(
            f"Fourier Grid Spikes: FFT power spectrum shows sharp periodic peaks (PAPR: {fft_papr:.1f}), indicating upsampling/dithering patterns."
        )

    features["Edge Blending"] = edge_blending_score
    features["Eye Reflection Asymmetry"] = eye_reflection_score
    features["Skin Texture Smoothness"] = skin_smooth_score
    features["Background Warping"] = bg_warping_score
    features["Metadata Anomalies"] = metadata_score

    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from services.deepfake_model import DeepfakeCNN

        model = DeepfakeCNN()
        cnn_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "models", "deepfake_cnn.pth")
        )

        if os.path.exists(cnn_path):
            try:
                state_dict = torch.load(cnn_path, map_location=torch.device('cpu'), weights_only=True)
                model.load_state_dict(state_dict)
                model.eval()
            except Exception:
                model.load_state_dict(torch.load(cnn_path, map_location=torch.device('cpu')))
                model.eval()

        transform = transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        input_tensor = transform(img).unsqueeze(0)
        with torch.no_grad():
            outputs = model(input_tensor)
            probs = torch.softmax(outputs, dim=1).numpy()[0]

        cnn_risk_score = int(probs[1] * 100)
    except Exception:
        cnn_risk_score = 50

    if ai_tag_matches:
        for match in ai_tag_matches:
            feedback.append(
                f"AI Signature Found: Detected '{match}' metadata string embedded inside the file bytes."
            )
        risk_score = 100
        prediction = "AI Generated"
        for k in features.keys():
            features[k] = max(features[k], 85)
    else:
        raw_risk = cnn_risk_score
        forensics_anomaly_avg = (edge_blending_score + bg_warping_score) / 2.0
        if forensics_anomaly_avg > 80 and raw_risk < 50:
            raw_risk = int(raw_risk * 0.6 + forensics_anomaly_avg * 0.4)
            feedback.append(
                "Localized Compression/Noise Mismatch: Pixel structures suggest copy-paste composition or local manipulation."
            )

        if has_genuine_camera and raw_risk < 85:
            raw_risk = max(3, int(raw_risk * 0.3))

        risk_score = np.clip(raw_risk, 0, 100)

        if risk_score >= 65:
            prediction = "AI Generated"
        elif risk_score >= 35:
            prediction = "Suspicious"
        else:
            prediction = "Authentic"

        if edge_blending_score >= 65:
            feedback.append(
                "Double Edge Boundaries: High noise variance inconsistencies detected around local boundaries."
            )
        if eye_reflection_score >= 65:
            feedback.append(
                "Color Spectrum Discrepancy: Abnormal channel correlations suggest synthetic light vectors."
            )
        if skin_smooth_score >= 65:
            feedback.append(
                "Ultra-Smooth Textures: Lack of natural sensor noise or pore details indicates artificial smoothing."
            )
        if bg_warping_score >= 65:
            feedback.append(
                "JPEG Compression Boundary: ELA block intensity differs, showing evidence of secondary compression."
            )

    if not feedback:
        feedback.append(
            "No obvious AI anomalies or generator signatures were detected in this content."
        )

    meta_info = {
        "file_size_bytes": len(file_bytes),
        "file_name": file_name,
        "content_type": content_type,
        "sha256_hash": file_hash,
    }

    return {
        "prediction": prediction,
        "risk_score": int(risk_score),
        "feedback": feedback,
        "features": features,
        "file_type": "image",
        "metadata": meta_info,
    }


# Re-export for backward compatibility
def extract_exif_metadata(img: Image.Image) -> Tuple[bool, List[str]]:
    has_genuine_camera = False
    camera_tags = []
    try:
        exif = img.getexif()
        if exif:
            for tag_id, val in exif.items():
                val_str = str(val).strip()
                if not val_str:
                    continue
                if tag_id == 271:
                    camera_tags.append(f"Make: {val_str}")
                    if any(
                        brand in val_str.lower()
                        for brand in [
                            "canon",
                            "nikon",
                            "sony",
                            "apple",
                            "samsung",
                            "google",
                            "huawei",
                            "oneplus",
                            "xiaomi",
                            "oppo",
                            "vivo",
                            "fujifilm",
                            "leica",
                            "panasonic",
                            "olympus",
                        ]
                    ):
                        has_genuine_camera = True
                elif tag_id == 272:
                    camera_tags.append(f"Model: {val_str}")
                    has_genuine_camera = True
                elif tag_id == 305:
                    camera_tags.append(f"Software: {val_str}")
    except Exception:
        pass
    return has_genuine_camera, camera_tags


def compute_noise_inconsistency(img_gray_arr: np.ndarray) -> Tuple[float, float]:
    res = laplace(img_gray_arr.astype(np.float32))
    h, w = res.shape
    block_h, block_w = h // 8, w // 8
    variances = []
    for i in range(8):
        for j in range(8):
            block = res[
                i * block_h : (i + 1) * block_h, j * block_w : (j + 1) * block_w
            ]
            variances.append(np.var(block))
    variances = np.array(variances)
    mean_var = np.mean(variances)
    std_var = np.std(variances)
    inconsistency = std_var / (mean_var + 1e-6)
    return float(inconsistency), float(mean_var)


def compute_ela_features(img: Image.Image) -> float:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    compressed_img = Image.open(buf)
    orig_arr = np.array(img.convert("RGB")).astype(np.float32)
    comp_arr = np.array(compressed_img).astype(np.float32)
    diff = np.abs(orig_arr - comp_arr)
    diff_gray = np.mean(diff, axis=2)
    diff_gray_resized = np.array(
        Image.fromarray(diff_gray.astype(np.uint8)).resize((256, 256))
    )
    h, w = diff_gray_resized.shape
    block_h, block_w = h // 8, w // 8
    variances = []
    for i in range(8):
        for j in range(8):
            block = diff_gray_resized[
                i * block_h : (i + 1) * block_h, j * block_w : (j + 1) * block_w
            ]
            variances.append(np.var(block))
    variances = np.array(variances)
    mean_var = np.mean(variances)
    std_var = np.std(variances)
    ela_inconsistency = std_var / (mean_var + 1e-6)
    return float(ela_inconsistency)


def compute_fft_peak_ratio(img_gray_arr: np.ndarray) -> float:
    f = np.fft.fft2(img_gray_arr)
    fshift = np.fft.fftshift(f)
    magnitude = np.abs(fshift)
    y, x = np.indices(magnitude.shape)
    cy, cx = magnitude.shape[0] // 2, magnitude.shape[1] // 2
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    high_freq_vals = magnitude[r > 90]
    if len(high_freq_vals) == 0:
        return 1.0
    max_hf = np.max(high_freq_vals)
    mean_hf = np.mean(high_freq_vals)
    papr = max_hf / (mean_hf + 1e-6)
    return float(papr)
