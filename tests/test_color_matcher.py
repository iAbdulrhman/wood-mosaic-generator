"""Tests for mosaic color quantization."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from modules.color_matcher import (
    calculate_luminance,
    quantize_grid_image,
    rgb_to_hex,
    validate_color_count,
)


def create_four_color_image() -> Image.Image:
    """Create an image containing four exact colors."""

    pixels = np.array(
        [
            [
                [0, 0, 0],
                [0, 0, 0],
                [255, 0, 0],
                [255, 0, 0],
            ],
            [
                [0, 0, 0],
                [0, 0, 0],
                [255, 0, 0],
                [255, 0, 0],
            ],
            [
                [0, 255, 0],
                [0, 255, 0],
                [255, 255, 255],
                [255, 255, 255],
            ],
            [
                [0, 255, 0],
                [0, 255, 0],
                [255, 255, 255],
                [255, 255, 255],
            ],
        ],
        dtype=np.uint8,
    )

    return Image.fromarray(
        pixels,
        mode="RGB",
    )


def test_rgb_to_hex():
    """Convert RGB values to hexadecimal strings."""

    assert rgb_to_hex((0, 0, 0)) == "#000000"
    assert rgb_to_hex((255, 255, 255)) == "#FFFFFF"
    assert rgb_to_hex((35, 110, 170)) == "#236EAA"


def test_rgb_to_hex_rejects_invalid_channels():
    """Reject RGB channels outside the valid range."""

    with pytest.raises(ValueError):
        rgb_to_hex((256, 0, 0))


def test_luminance_orders_dark_before_light():
    """Return a lower luminance for darker colors."""

    black = calculate_luminance(
        (0, 0, 0)
    )

    white = calculate_luminance(
        (255, 255, 255)
    )

    assert black < white


@pytest.mark.parametrize(
    "color_count",
    [
        0,
        1,
        -5,
        257,
    ],
)
def test_invalid_color_count_values(color_count):
    """Reject unsupported color counts."""

    with pytest.raises(ValueError):
        validate_color_count(color_count)


@pytest.mark.parametrize(
    "color_count",
    [
        4.5,
        "8",
        True,
    ],
)
def test_non_integer_color_count(color_count):
    """Reject non-integer color counts."""

    with pytest.raises(TypeError):
        validate_color_count(color_count)


def test_quantize_four_exact_colors():
    """Preserve an image containing four requested colors."""

    image = create_four_color_image()

    result = quantize_grid_image(
        grid_image=image,
        color_count=4,
        preview_cell_size=10,
    )

    assert result.requested_color_count == 4
    assert result.actual_color_count == 4
    assert result.total_pieces == 16
    assert result.columns == 4
    assert result.rows == 4

    assert result.quantized_image.size == (4, 4)
    assert result.preview_image.size == (40, 40)

    assert len(result.palette) == 4

    assert sum(
        entry.piece_count
        for entry in result.palette
    ) == 16


def test_color_ids_are_sequential():
    """Generate sequential C01, C02 color identifiers."""

    result = quantize_grid_image(
        grid_image=create_four_color_image(),
        color_count=4,
    )

    color_ids = [
        entry.color_id
        for entry in result.palette
    ]

    assert color_ids == [
        "C01",
        "C02",
        "C03",
        "C04",
    ]


def test_palette_is_sorted_by_luminance():
    """Sort the generated palette from dark to light."""

    result = quantize_grid_image(
        grid_image=create_four_color_image(),
        color_count=4,
    )

    luminances = [
        entry.luminance
        for entry in result.palette
    ]

    assert luminances == sorted(luminances)


def test_piece_percentages_total_one_hundred():
    """Ensure all color percentages total approximately 100%."""

    result = quantize_grid_image(
        grid_image=create_four_color_image(),
        color_count=4,
    )

    percentage_total = sum(
        entry.percentage
        for entry in result.palette
    )

    assert percentage_total == pytest.approx(100.0)


def test_requested_colors_are_limited_by_unique_colors():
    """Avoid creating more clusters than unique image colors."""

    image = Image.new(
        mode="RGB",
        size=(10, 10),
        color=(20, 40, 60),
    )

    result = quantize_grid_image(
        grid_image=image,
        color_count=8,
    )

    assert result.requested_color_count == 8
    assert result.actual_color_count == 1
    assert len(result.palette) == 1
    assert result.palette[0].piece_count == 100


def test_quantization_is_repeatable():
    """Produce the same result when random state is unchanged."""

    image = create_four_color_image()

    first_result = quantize_grid_image(
        grid_image=image,
        color_count=3,
        random_state=42,
    )

    second_result = quantize_grid_image(
        grid_image=image,
        color_count=3,
        random_state=42,
    )

    assert np.array_equal(
        np.asarray(
            first_result.quantized_image
        ),
        np.asarray(
            second_result.quantized_image
        ),
    )

    assert first_result.palette_rows() == (
        second_result.palette_rows()
    )


def test_color_index_grid_matches_image_size():
    """Create one color index for every wooden piece."""

    image = create_four_color_image()

    result = quantize_grid_image(
        grid_image=image,
        color_count=3,
    )

    assert result.color_index_grid.shape == (4, 4)

    assert result.color_index_grid.min() >= 0

    assert (
        result.color_index_grid.max()
        < result.actual_color_count
    )


def test_metadata_is_serializable():
    """Create a metadata dictionary for the UI and exports."""

    result = quantize_grid_image(
        grid_image=create_four_color_image(),
        color_count=4,
    )

    metadata = result.metadata()

    assert metadata["requested_color_count"] == 4
    assert metadata["actual_color_count"] == 4
    assert metadata["total_pieces"] == 16
    assert len(metadata["palette"]) == 4

    assert metadata["palette"][0][
        "color_id"
    ] == "C01"
