import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _stage_zoom_template() -> str:
    template_path = Path(__file__).resolve().parents[1] / "assets" / "js" / "line_mark_stage_image_zoom.js"
    return template_path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _stage_hover_template() -> str:
    template_path = Path(__file__).resolve().parents[1] / "assets" / "js" / "line_mark_stage_hover_swap.js"
    return template_path.read_text(encoding="utf-8")


def get_stage_image_zoom_script(zoom_factor: int = 7) -> str:
    return _stage_zoom_template().replace("__ZOOM_FACTOR__", str(int(zoom_factor)))


def get_stage_hover_swap_script(thin_image_url: str, thick_image_url: str) -> str:
    script = _stage_hover_template()
    return (
        script.replace("__THIN_IMAGE_URL__", json.dumps(thin_image_url))
        .replace("__THICK_IMAGE_URL__", json.dumps(thick_image_url))
    )
