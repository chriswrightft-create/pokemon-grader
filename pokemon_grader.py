from __future__ import annotations

import cv2
import numpy as np

from border_measurement import (
    BorderAnalysisDebug,
    BorderRatios,
    analyze_borders,
    calculate_ratios_from_bounds,
    create_visualization,
)
from card_detection import detect_card_and_warp


class CardDetectionError(Exception):
    """Raised when a card cannot be reliably detected in the image."""


def analyze_card_borders(image: np.ndarray) -> BorderRatios:
    result, _ = analyze_card_borders_with_debug(image)
    return result


def analyze_card_borders_with_debug(image: np.ndarray) -> tuple[BorderRatios, BorderAnalysisDebug]:
    card_image = detect_card_and_warp(image)
    return analyze_borders(card_image)


def analyze_adjusted_card_with_debug(image: np.ndarray) -> tuple[BorderRatios, BorderAnalysisDebug]:
    return analyze_borders(image)


def load_image(path: str) -> np.ndarray:
    image = cv2.imread(path)
    if image is None:
        raise FileNotFoundError(f"Could not load image at {path}")
    return image
