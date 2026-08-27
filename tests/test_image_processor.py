"""Tests for image-processing functions."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from modules.image_processor import (
    calculate_center_crop_box,
    create_pixel_preview,
    crop_image_to_grid_ratio,
    load_image,
    process_image,
    resize_image_to_grid,
    validate_grid_dimensions,
)


def create_test_image(
    width: int = 400,
    height: int = 300,
    color: tuple[int, int, int] = (120, 80, 40),
) -> Image.Image:
    """Create an RGB test image."""

    return Image.new(
        mode="RGB",
        size=(width, height),
        color=color,
    )


def image_to_bytes(
    image: Image.Image,
    image_format: str = "PNG",
) -> io.BytesIO:
    """Save a Pillow image to an in-memory binary file."""

    buffer = io.BytesIO()
    image.save(buffer, format=image_format)
    buffer.seek(0)

    return buffer


def test_load_image_from_binary_file():
    """Load an image from a file-like object."""

    source = create_test_image(
        width=320,
        height=240,
    )

    loaded = load_image(
        image_to_bytes(source)
    )

    assert loaded.mode == "RGB"
    assert loaded.size == (320, 240)


def test_load_image_converts_rgba_to_rgb():
    """Convert images containing alpha transparency to RGB."""

    source = Image.new(
        mode="RGBA",
        size=(100, 80),
        color=(255, 0, 0, 120),
    )

    loaded = load_image(
        image_to_bytes(source)
    )

    assert loaded.mode == "RGB"
    assert loaded.size == (100, 80)


def test_load_invalid_image():
    """Reject a non-image binary file."""

    invalid_file = io.BytesIO(
        b"This is not a valid image."
    )

    with pytest.raises(
        ValueError,
        match="could not be opened",
    ):
        load_image(invalid_file)


def test_wide_image_is_cropped_horizontally():
    """Crop both sides of an image that is too wide."""

    crop_box = calculate_center_crop_box(
        image_width=400,
        image_height=200,
        target_ratio=1.0,
    )

    assert crop_box == (100, 0, 300, 200)


def test_tall_image_is_cropped_vertically():
    """Crop the top and bottom of an image that is too tall."""

    crop_box = calculate_center_crop_box(
        image_width=200,
        image_height=400,
        target_ratio=1.0,
    )

    assert crop_box == (0, 100, 200, 300)


def test_matching_ratio_does_not_crop():
    """Keep the complete image when ratios already match."""

    crop_box = calculate_center_crop_box(
        image_width=400,
        image_height=200,
        target_ratio=2.0,
    )

    assert crop_box == (0, 0, 400, 200)


def test_crop_image_matches_grid_ratio():
    """Crop an image to match a 4 by 3 grid."""

    image = create_test_image(
        width=1000,
        height=1000,
    )

    cropped, crop_box = crop_image_to_grid_ratio(
        image=image,
        columns=4,
        rows=3,
    )

    assert crop_box == (0, 125, 1000, 875)
    assert cropped.size == (1000, 750)
    assert cropped.width / cropped.height == pytest.approx(
        4 / 3
    )


def test_resize_image_to_exact_grid():
    """Create exactly one pixel for each grid position."""

    image = create_test_image(
        width=800,
        height=600,
    )

    grid_image = resize_image_to_grid(
        image=image,
        columns=40,
        rows=30,
    )

    assert grid_image.size == (40, 30)


def test_pixel_preview_uses_integer_scaling():
    """Enlarge each grid pixel to a visible square."""

    grid_image = create_test_image(
        width=40,
        height=30,
    )

    preview = create_pixel_preview(
        grid_image=grid_image,
        cell_display_size=10,
    )

    assert preview.size == (400, 300)


def test_pixel_preview_respects_maximum_dimensions():
    """Prevent previews from becoming excessively large."""

    grid_image = create_test_image(
        width=100,
        height=80,
    )

    preview = create_pixel_preview(
        grid_image=grid_image,
        cell_display_size=20,
        maximum_width=500,
        maximum_height=400,
    )

    assert preview.size == (500, 400)


@pytest.mark.parametrize(
    "columns,rows",
    [
        (0, 10),
        (-1, 10),
        (10, 0),
        (10, -1),
    ],
)
def test_invalid_grid_dimensions(columns, rows):
    """Reject zero or negative grid dimensions."""

    with pytest.raises(ValueError):
        validate_grid_dimensions(
            columns=columns,
            rows=rows,
        )


@pytest.mark.parametrize(
    "columns,rows",
    [
        (10.5, 10),
        (10, 20.5),
        ("10", 10),
        (10, "20"),
        (True, 10),
    ],
)
def test_non_integer_grid_dimensions(columns, rows):
    """Reject non-integer grid dimensions."""

    with pytest.raises(TypeError):
        validate_grid_dimensions(
            columns=columns,
            rows=rows,
        )


def test_complete_processing_pipeline():
    """Run the complete image-processing pipeline."""

    source = create_test_image(
        width=1200,
        height=800,
        color=(30, 110, 170),
    )

    result = process_image(
        source=image_to_bytes(source),
        columns=50,
        rows=35,
        preview_cell_size=10,
    )

    assert result.original_image.size == (1200, 800)
    assert result.grid_image.size == (50, 35)
    assert result.preview_image.size == (500, 350)

    assert result.columns == 50
    assert result.rows == 35
    assert result.total_pixels == 1750

    assert result.cropped_ratio == pytest.approx(
        result.grid_ratio,
        abs=0.002,
    )


def test_processing_metadata():
    """Return JSON-compatible image metadata."""

    source = create_test_image(
        width=400,
        height=300,
    )

    result = process_image(
        source=image_to_bytes(source),
        columns=20,
        rows=10,
    )

    metadata = result.metadata()

    assert metadata["original_width_px"] == 400
    assert metadata["original_height_px"] == 300
    assert metadata["columns"] == 20
    assert metadata["rows"] == 10
    assert metadata["total_pixels"] == 200
    assert isinstance(metadata["crop_box"], dict)
