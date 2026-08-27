"""Image processing utilities for the Wood Mosaic Generator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError


ImageSource = str | Path | BinaryIO


@dataclass(frozen=True)
class ImageProcessingResult:
    """Images and measurements produced during processing."""

    original_image: Image.Image
    cropped_image: Image.Image
    grid_image: Image.Image
    preview_image: Image.Image

    original_width_px: int
    original_height_px: int

    cropped_width_px: int
    cropped_height_px: int

    columns: int
    rows: int

    crop_left_px: int
    crop_top_px: int
    crop_right_px: int
    crop_bottom_px: int

    @property
    def original_ratio(self) -> float:
        """Return the original image aspect ratio."""

        return self.original_width_px / self.original_height_px

    @property
    def cropped_ratio(self) -> float:
        """Return the cropped image aspect ratio."""

        return self.cropped_width_px / self.cropped_height_px

    @property
    def grid_ratio(self) -> float:
        """Return the target grid aspect ratio."""

        return self.columns / self.rows

    @property
    def total_pixels(self) -> int:
        """Return the number of cells in the mosaic grid."""

        return self.columns * self.rows

    def metadata(self) -> dict:
        """Return serializable information about the processing result."""

        return {
            "original_width_px": self.original_width_px,
            "original_height_px": self.original_height_px,
            "original_ratio": round(self.original_ratio, 6),
            "cropped_width_px": self.cropped_width_px,
            "cropped_height_px": self.cropped_height_px,
            "cropped_ratio": round(self.cropped_ratio, 6),
            "columns": self.columns,
            "rows": self.rows,
            "grid_ratio": round(self.grid_ratio, 6),
            "total_pixels": self.total_pixels,
            "crop_box": {
                "left": self.crop_left_px,
                "top": self.crop_top_px,
                "right": self.crop_right_px,
                "bottom": self.crop_bottom_px,
            },
        }


def load_image(source: ImageSource) -> Image.Image:
    """
    Load an image, apply its EXIF orientation, and convert it to RGB.

    The source can be a local path or a file-like object such as a
    Streamlit UploadedFile.
    """

    if hasattr(source, "seek"):
        source.seek(0)

    try:
        with Image.open(source) as opened_image:
            corrected_image = ImageOps.exif_transpose(opened_image)
            return corrected_image.convert("RGB").copy()

    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValueError(
            "The selected file could not be opened as an image."
        ) from error


def validate_grid_dimensions(
    columns: int,
    rows: int,
) -> None:
    """Validate the requested pixel-grid dimensions."""

    if isinstance(columns, bool) or not isinstance(columns, int):
        raise TypeError("Columns must be an integer.")

    if isinstance(rows, bool) or not isinstance(rows, int):
        raise TypeError("Rows must be an integer.")

    if columns <= 0:
        raise ValueError("Columns must be greater than zero.")

    if rows <= 0:
        raise ValueError("Rows must be greater than zero.")


def calculate_center_crop_box(
    image_width: int,
    image_height: int,
    target_ratio: float,
) -> tuple[int, int, int, int]:
    """
    Calculate a centered crop box matching the requested aspect ratio.

    The returned tuple is:
    left, top, right, bottom.
    """

    if image_width <= 0 or image_height <= 0:
        raise ValueError(
            "Image width and height must be greater than zero."
        )

    if target_ratio <= 0:
        raise ValueError(
            "Target aspect ratio must be greater than zero."
        )

    source_ratio = image_width / image_height

    if abs(source_ratio - target_ratio) < 1e-9:
        return 0, 0, image_width, image_height

    if source_ratio > target_ratio:
        crop_width = max(
            1,
            min(
                image_width,
                round(image_height * target_ratio),
            ),
        )

        left = (image_width - crop_width) // 2
        right = left + crop_width

        return left, 0, right, image_height

    crop_height = max(
        1,
        min(
            image_height,
            round(image_width / target_ratio),
        ),
    )

    top = (image_height - crop_height) // 2
    bottom = top + crop_height

    return 0, top, image_width, bottom


def crop_image_to_grid_ratio(
    image: Image.Image,
    columns: int,
    rows: int,
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Center-crop an image to match the grid aspect ratio."""

    validate_grid_dimensions(columns, rows)

    target_ratio = columns / rows

    crop_box = calculate_center_crop_box(
        image_width=image.width,
        image_height=image.height,
        target_ratio=target_ratio,
    )

    cropped_image = image.crop(crop_box)

    return cropped_image, crop_box


def resize_image_to_grid(
    image: Image.Image,
    columns: int,
    rows: int,
) -> Image.Image:
    """
    Resize an image so every resulting pixel represents one wood piece.
    """

    validate_grid_dimensions(columns, rows)

    return image.resize(
        (columns, rows),
        resample=Image.Resampling.LANCZOS,
    )


def create_pixel_preview(
    grid_image: Image.Image,
    cell_display_size: int = 16,
    maximum_width: int = 1400,
    maximum_height: int = 1000,
) -> Image.Image:
    """
    Enlarge a grid image without smoothing for a pixel-art preview.
    """

    if cell_display_size <= 0:
        raise ValueError(
            "Cell display size must be greater than zero."
        )

    if maximum_width <= 0 or maximum_height <= 0:
        raise ValueError(
            "Preview limits must be greater than zero."
        )

    scale_by_width = maximum_width // grid_image.width
    scale_by_height = maximum_height // grid_image.height

    scale = max(
        1,
        min(
            cell_display_size,
            scale_by_width,
            scale_by_height,
        ),
    )

    preview_width = grid_image.width * scale
    preview_height = grid_image.height * scale

    return grid_image.resize(
        (preview_width, preview_height),
        resample=Image.Resampling.NEAREST,
    )


def process_image(
    source: ImageSource,
    columns: int,
    rows: int,
    preview_cell_size: int = 16,
) -> ImageProcessingResult:
    """
    Run the complete first-stage image-processing pipeline.

    Steps:
    1. Load and orient the source image.
    2. Center-crop it to the grid ratio.
    3. Resize it to one pixel per wooden piece.
    4. Create a larger unsmoothed preview.
    """

    validate_grid_dimensions(columns, rows)

    original_image = load_image(source)

    cropped_image, crop_box = crop_image_to_grid_ratio(
        image=original_image,
        columns=columns,
        rows=rows,
    )

    grid_image = resize_image_to_grid(
        image=cropped_image,
        columns=columns,
        rows=rows,
    )

    preview_image = create_pixel_preview(
        grid_image=grid_image,
        cell_display_size=preview_cell_size,
    )

    left, top, right, bottom = crop_box

    return ImageProcessingResult(
        original_image=original_image,
        cropped_image=cropped_image,
        grid_image=grid_image,
        preview_image=preview_image,
        original_width_px=original_image.width,
        original_height_px=original_image.height,
        cropped_width_px=cropped_image.width,
        cropped_height_px=cropped_image.height,
        columns=columns,
        rows=rows,
        crop_left_px=left,
        crop_top_px=top,
        crop_right_px=right,
        crop_bottom_px=bottom,
    )
