import hashlib
from typing import Callable, Optional

import numpy as np
import streamlit as st


def get_cached_warped_card(
    image_bytes: bytes,
    image_bgr: np.ndarray,
    final_points: list[tuple[float, float]],
    warp_from_edges: Callable[[np.ndarray, list[tuple[float, float]]], Optional[np.ndarray]],
) -> Optional[np.ndarray]:
    points_key = tuple((round(point[0], 3), round(point[1], 3)) for point in final_points)
    image_hash = hashlib.sha1(image_bytes).hexdigest()[:16]
    cache_key = (image_hash, points_key)
    cached_key = st.session_state.get("line_warp_cache_key")
    cached_card = st.session_state.get("line_warp_cache_card")
    if cached_key == cache_key and isinstance(cached_card, np.ndarray):
        return cached_card
    warped_card = warp_from_edges(image_bgr, final_points)
    if isinstance(warped_card, np.ndarray):
        st.session_state["line_warp_cache_key"] = cache_key
        st.session_state["line_warp_cache_card"] = warped_card
    return warped_card
