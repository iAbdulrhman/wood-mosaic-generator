"""Tests for manufacturing piece generation."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from modules.color_matcher import quantize_grid_image
from modules.grid_calculator import calculate_grid
from modules.piece_generator import (
    create_piece_id_grid,
    generate_piece_records,
    piece_records_to_rows,
    summarize_pieces_by_color,
)


def create_test_results():
    """Create matching grid and color results."""

    grid = calculate_grid(
        board_width_mm=41,
        board_height_mm=41,
        piece_size_mm=20,
        gap_mm=1,
    )

    pixels = np.array(
        [
            [
                [0, 0, 0],
                [255, 255, 255],
            ],
            [
                [255, 255, 255],
                [0, 0, 0],
            ],
        ],
        dtype=np.uint8,
    )

    image = Image.fromarray(pixels)

    colors = quantize_grid_image(
        grid_image=image,
        color_count=2,
        preview_cell_size=10,
    )

    return grid, colors


def test_generate_one_record_per_piece():
    """Generate one record for every grid cell."""

    grid, colors = create_test_results()

    records = generate_piece_records(
        grid=grid,
        colors=colors,
    )

    assert len(records) == 4
    assert len(records) == grid.total_pieces


def test_piece_identifiers():
    """Create row-and-column identifiers."""

    grid, colors = create_test_results()

    records = generate_piece_records(
        grid=grid,
        colors=colors,
    )

    assert records[0].piece_id == "R001-C001"
    assert records[1].piece_id == "R001-C002"
    assert records[2].piece_id == "R002-C001"
    assert records[3].piece_id == "R002-C002"


def test_piece_sequences_are_incremental():
    """Number records sequentially."""

    grid, colors = create_test_results()

    records = generate_piece_records(
        grid=grid,
        colors=colors,
    )

    assert [
        record.sequence
        for record in records
    ] == [1, 2, 3, 4]


def test_piece_coordinates():
    """Calculate physical coordinates on the board."""

    grid, colors = create_test_results()

    records = generate_piece_records(
        grid=grid,
        colors=colors,
    )

    assert records[0].x_mm == 0
    assert records[0].y_mm == 0

    assert records[1].x_mm == 21
    assert records[1].y_mm == 0

    assert records[2].x_mm == 0
    assert records[2].y_mm == 21


def test_piece_center_coordinates():
    """Calculate the center point of every piece."""

    grid, colors = create_test_results()

    records = generate_piece_records(
        grid=grid,
        colors=colors,
    )

    assert records[0].center_x_mm == 10
    assert records[0].center_y_mm == 10

    assert records[3].center_x_mm == 31
    assert records[3].center_y_mm == 31


def test_piece_dimensions():
    """Store the physical piece dimensions."""

    grid, colors = create_test_results()

    records = generate_piece_records(
        grid=grid,
        colors=colors,
    )

    assert all(
        record.width_mm == 20
        for record in records
    )

    assert all(
        record.height_mm == 20
        for record in records
    )


def test_piece_colors_match_palette():
    """Associate every piece with a valid palette entry."""

    grid, colors = create_test_results()

    records = generate_piece_records(
        grid=grid,
        colors=colors,
    )

    palette_ids = {
        entry.color_id
        for entry in colors.palette
    }

    assert all(
        record.color_id in palette_ids
        for record in records
    )


def test_piece_records_to_rows():
    """Convert records to dictionaries."""

    grid, colors = create_test_results()

    records = generate_piece_records(
        grid=grid,
        colors=colors,
    )

    rows = piece_records_to_rows(records)

    assert len(rows) == 4
    assert rows[0]["piece_id"] == "R001-C001"
    assert rows[0]["row"] == 1
    assert rows[0]["column"] == 1


def test_summarize_pieces_by_color():
    """Count records by color."""

    grid, colors = create_test_results()

    records = generate_piece_records(
        grid=grid,
        colors=colors,
    )

    summary = summarize_pieces_by_color(records)

    assert len(summary) == 2

    assert sum(
        item["piece_count"]
        for item in summary
    ) == 4


def test_create_piece_id_grid():
    """Create a two-dimensional identifier grid."""

    grid, colors = create_test_results()

    records = generate_piece_records(
        grid=grid,
        colors=colors,
    )

    identifier_grid = create_piece_id_grid(
        records=records,
        rows=2,
        columns=2,
    )

    assert identifier_grid.shape == (2, 2)
    assert identifier_grid[0, 0] == "R001-C001"
    assert identifier_grid[1, 1] == "R002-C002"


def test_reject_mismatched_grid_dimensions():
    """Reject incompatible physical and color grids."""

    grid = calculate_grid(
        board_width_mm=62,
        board_height_mm=41,
        piece_size_mm=20,
        gap_mm=1,
    )

    image = Image.new(
        mode="RGB",
        size=(2, 2),
        color=(100, 100, 100),
    )

    colors = quantize_grid_image(
        grid_image=image,
        color_count=2,
    )

    with pytest.raises(
        ValueError,
        match="columns",
    ):
        generate_piece_records(
            grid=grid,
            colors=colors,
        )


def test_reject_invalid_identifier_grid_size():
    """Reject incompatible record and grid counts."""

    grid, colors = create_test_results()

    records = generate_piece_records(
        grid=grid,
        colors=colors,
    )

    with pytest.raises(
        ValueError,
        match="Record count",
    ):
        create_piece_id_grid(
            records=records,
            rows=3,
            columns=2,
        )
