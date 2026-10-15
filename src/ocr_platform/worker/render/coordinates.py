"""Coordinate transforms and explicit coordinate-system algebra.

The only module permitted to convert a bbox between coordinate systems. Every
other module passes coordinates through with an explicit ``coordinate_system``
attached (see ``schemas/evidence.py``), so a PDF bottom-left box can never be
silently mistaken for an image top-left box.

Systems handled:

* ``pdf_bottom_left_native`` — PDF user space, origin bottom-left, y up.
* ``image_top_left_pixel`` — raster pixel space, origin top-left, y down.
* ``image_top_left_normalized`` — the unit box, page-space storage form.
* ``crop_local_top_left`` — coordinates inside a cropped region; never valid as
  an evidence page-space box.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ocr_platform.schemas.evidence import (
    CROP_LOCAL_TOP_LEFT,
    IMAGE_TOP_LEFT_PIXEL,
    PAGE_SPACE_SYSTEM,
    PDF_BOTTOM_LEFT_NATIVE,
    BBox,
)

Box = tuple[float, float, float, float]


class CoordinateSystemError(ValueError):
    """Raised on an operation that mixes coordinate systems without a conversion."""


@dataclass(frozen=True)
class PageSize:
    """Rendered page dimensions in pixels."""

    width_px: int
    height_px: int

    def __post_init__(self) -> None:
        if self.width_px <= 0 or self.height_px <= 0:
            raise CoordinateSystemError(f"page dimensions must be positive, got {self}")

    @property
    def area(self) -> int:
        return self.width_px * self.height_px


def _check_box(box: Box) -> Box:
    x0, y0, x1, y1 = box
    if x1 < x0 or y1 < y0:
        raise CoordinateSystemError(f"degenerate box {box}: x1/y1 must not precede x0/y0")
    return box


def to_page_normalized(box: Box, page: PageSize) -> Box:
    """Convert image top-left *pixel* space into the unit box.

    Normalized storage form for page-space evidence. Pixel edges are treated as
    inclusive pixel indices, so the far edge is ``(index + 1) / size``.
    """
    x0, y0, x1, y1 = _check_box(box)
    return (
        x0 / page.width_px,
        y0 / page.height_px,
        (x1 + 1) / page.width_px,
        (y1 + 1) / page.height_px,
    )


def to_pixel(box: Box, page: PageSize) -> Box:
    """Convert a normalized page-space box into image top-left *pixel* space.

    Inverse of :func:`to_page_normalized` at pixel granularity: the pixel box is
    floored at the origin and clipped to the last pixel, so the result is always
    addressable. Round-trips within one pixel (epsilon), never bit-exact for
    sub-pixel boxes — quantization is documented here rather than hidden.
    """
    x0, y0, x1, y1 = _check_box(box)
    px0 = max(0, round(x0 * page.width_px))
    py0 = max(0, round(y0 * page.height_px))
    px1 = min(page.width_px - 1, max(px0, round(x1 * page.width_px) - 1))
    py1 = min(page.height_px - 1, max(py0, round(y1 * page.height_px) - 1))
    return (float(px0), float(py0), float(px1), float(py1))


def pdf_rect_to_image_bbox(
    box: Box,
    page: PageSize,
    dpi: int,
    media_box_points: Box,
) -> Box:
    """Convert a PDF bottom-left native rect into image top-left pixels.

    Points are scaled by ``dpi / 72``. The vertical flip is explicit: PDF y is
    measured up from ``media_box_points``'s top edge, image y is measured down
    from the top, so a PDF rect near the top of the page lands near the top of
    the raster.

    ``media_box_points`` is **required**: the PDF→image flip needs the page's
    vertical extent, and guessing it would silently misplace every box on a
    non-zero-origin media box.
    """
    x0, y0, x1, y1 = _check_box(box)
    mx0, _my0, _mx1, my1 = _check_box(media_box_points)
    if dpi <= 0:
        raise CoordinateSystemError("dpi must be positive")
    scale = dpi / 72.0
    # Rebase to the media box so a non-zero PDF origin cannot yield negatives.
    x0 -= mx0
    x1 -= mx0
    # PDF y grows upward from the media box top; image y grows downward.
    box_px = (x0 * scale, (my1 - y1) * scale, x1 * scale, (my1 - y0) * scale)
    _check_box(box_px)
    return box_px


def normalize_page_box(box: Box, page: PageSize) -> Box:
    """Canonical R0 page-box normalize (ADR-002): identity fit to the unit box.

    Pure and explicitly callable — no ambient scale or deskew is applied inside
    OCR. The *result* is recorded in the registration transform so a reviewer
    can see that an identity transform was used.
    """
    return to_page_normalized(_check_box(box), page)


def require_same_system(a: BBox, b: BBox) -> None:
    """Raise unless both boxes are in the same coordinate system."""
    if a.coordinate_system != b.coordinate_system:
        raise CoordinateSystemError(
            f"cannot combine {a.coordinate_system} with {b.coordinate_system}; "
            "convert explicitly first"
        )


def assert_page_space(box: BBox) -> BBox:
    """Raise unless *box* is usable as evidence page-space geometry."""
    if not box.is_page_space:
        raise CoordinateSystemError(
            f"{box.coordinate_system} is not {PAGE_SPACE_SYSTEM}; "
            "crop-local coordinates are never evidence page-space boxes"
        )
    return box


def crop_local_box(x0: float, y0: float, x1: float, y1: float) -> BBox:
    """Tag a crop-local intermediate so it cannot leak into page space."""
    return BBox(x0=x0, y0=y0, x1=x1, y1=y1, coordinate_system=CROP_LOCAL_TOP_LEFT)


def page_space_box(x0: float, y0: float, x1: float, y1: float) -> BBox:
    """Build a normalized page-space bbox."""
    return BBox(x0=x0, y0=y0, x1=x1, y1=y1, coordinate_system=PAGE_SPACE_SYSTEM)


def image_pixel_box(x0: float, y0: float, x1: float, y1: float) -> BBox:
    """Build an image top-left pixel bbox."""
    return BBox(x0=x0, y0=y0, x1=x1, y1=y1, coordinate_system=IMAGE_TOP_LEFT_PIXEL)


def pdf_native_box(x0: float, y0: float, x1: float, y1: float) -> BBox:
    """Build a PDF bottom-left native bbox."""
    return BBox(x0=x0, y0=y0, x1=x1, y1=y1, coordinate_system=PDF_BOTTOM_LEFT_NATIVE)


def round_trip_within_epsilon(box: Box, page: PageSize, epsilon_px: float = 1.0) -> bool:
    """Check the normalized↔pixel round trip stays inside *epsilon_px*."""
    normalized = to_page_normalized(box, page)
    restored = to_pixel(normalized, page)
    return all(abs(a - b) <= epsilon_px for a, b in zip(box, restored))


def known_systems() -> Iterable[str]:
    """The coordinate-system constants this module understands."""
    return (PDF_BOTTOM_LEFT_NATIVE, IMAGE_TOP_LEFT_PIXEL, PAGE_SPACE_SYSTEM, CROP_LOCAL_TOP_LEFT)
