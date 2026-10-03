# ML Evaluation Framework for CyberGuardian AI
# This module provides reproducible evaluation for all detection models

from .base import evaluate_model
from .url_evaluator import evaluate_url_model
from .message_evaluator import evaluate_message_model
from .deepfake_evaluator import evaluate_deepfake_model
from .report import generate_evaluation_report

__all__ = [
    'evaluate_model',
    'evaluate_url_model',
    'evaluate_message_model',
    'evaluate_deepfake_model',
    'generate_evaluation_report'
]
