import os
import cv2
import numpy as np
import logging
from typing import Optional, List, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class FaceExtractor(ABC):
    """Base class for modular face extraction."""

    @abstractmethod
    def extract_faces(self, frame: np.ndarray, max_faces: int = 1) -> List[np.ndarray]:
        """
        Extract faces from a BGR/RGB frame.

        Args:
            frame: Input image as numpy array
            max_faces: Maximum number of faces to extract (sorted by size/confidence)

        Returns:
            List of cropped and resized face images as numpy arrays,
            or empty list if no faces found.
        """
        pass


class OpenCVDNNFaceExtractor(FaceExtractor):
    """
    Modern Face Extractor using OpenCV's DNN module with a ResNet-10 SSD face model.
    Significantly more robust than legacy Haar cascades.
    """

    def __init__(
        self,
        target_size: Tuple[int, int] = (224, 224),
        margin: float = 0.2,
        confidence_threshold: float = 0.5
    ):
        """
        Initialize the CNN face detector.

        Args:
            target_size: Output resolution for the crop, defaults to EfficientNet's 224x224
            margin: Extra padding around the bounding box (fraction of width/height)
            confidence_threshold: Minimum confidence to consider a bounding box a face
        """
        self.target_size = target_size
        self.margin = margin
        self.confidence_threshold = confidence_threshold
        self.net = self._load_model()

    def _load_model(self) -> cv2.dnn_Net:
        """Loads and returns the pre-trained Caffe model."""
        base_dir = os.path.join(os.path.dirname(__file__), "assets")
        os.makedirs(base_dir, exist_ok=True)

        prototxt_path = os.path.join(base_dir, "deploy.prototxt")
        model_path = os.path.join(base_dir, "res10_300x300_ssd_iter_140000.caffemodel")

        # We download them if they don't exist during runtime setup,
        # but in production these should be bundled.
        if not os.path.exists(prototxt_path) or not os.path.exists(model_path):
            import urllib.request
            logger.info("Downloading OpenCV DNN face detector models...")
            proto_url = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
            model_url = "https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"
            try:
                urllib.request.urlretrieve(proto_url, prototxt_path)
                urllib.request.urlretrieve(model_url, model_path)
            except Exception as e:
                logger.error(f"Failed to download models: {e}")
                raise

        try:
            return cv2.dnn.readNetFromCaffe(prototxt_path, model_path)
        except Exception as e:
            logger.error(f"Failed to load OpenCV DNN model: {e}")
            raise

    def extract_faces(self, frame: np.ndarray, max_faces: int = 1) -> List[np.ndarray]:
        """
        Extract and return cropped, padded faces.
        Handles missing faces, multiple faces, and bad frames safely.
        """
        if frame is None or frame.size == 0 or len(frame.shape) != 3:
            return []

        h, w = frame.shape[:2]

        # The ResNet-10 model expects a 300x300 input with mean subtraction (104, 117, 123)
        # Note: Mean values are for BGR format. If the frame is RGB, we use swapRB=True.
        # But we'll assume the frame is RGB (since PIL/PyTorch usually provide RGB).
        try:
            blob = cv2.dnn.blobFromImage(
                frame, 1.0, (300, 300),
                (104.0, 117.0, 123.0),
                swapRB=True, crop=False
            )
            self.net.setInput(blob)
            detections = self.net.forward()
        except Exception as e:
            logger.warning(f"DNN forward pass failed: {e}")
            return []

        faces = []
        # detections shape is (1, 1, N, 7)
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]

            if confidence > self.confidence_threshold:
                # Get absolute box coordinates
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")

                # Compute width and height
                box_w = endX - startX
                box_h = endY - startY

                # Filter out degenerate boxes
                if box_w <= 10 or box_h <= 10:
                    continue

                area = box_w * box_h
                faces.append({
                    "box": (startX, startY, box_w, box_h),
                    "confidence": confidence,
                    "area": area
                })

        if not faces:
            return []

        # Sort faces deterministically: primary heuristic is area.
        # In a deepfake detection scenario, we usually care about the largest, most prominent face.
        faces.sort(key=lambda f: f["area"], reverse=True)
        faces = faces[:max_faces]

        results = []
        for face in faces:
            startX, startY, box_w, box_h = face["box"]

            # Add configurable margin
            pad_x = int(box_w * self.margin)
            pad_y = int(box_h * self.margin)

            # Add margin but keep within frame bounds
            c_startX = max(0, startX - pad_x)
            c_startY = max(0, startY - pad_y)
            c_endX = min(w, startX + box_w + pad_x)
            c_endY = min(h, startY + box_h + pad_y)

            # Crop region
            face_img = frame[c_startY:c_endY, c_startX:c_endX]

            # Double check valid region
            if face_img.size == 0 or 0 in face_img.shape:
                continue

            # Resize to the target square (e.g. 224x224 for EfficientNet)
            resized_face = cv2.resize(face_img, self.target_size, interpolation=cv2.INTER_AREA)
            results.append(resized_face)

        return results
