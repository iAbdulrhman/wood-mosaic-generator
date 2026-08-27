"""Tests for the wooden mosaic grid calculator."""

import pytest

from modules.grid_calculator import calculate_grid


def test_standard_board():
    """Calculate a standard 1000 × 700 mm board."""

    result = calculate_grid(
        board_width_mm=1000,
        board_height_mm=700,
        piece_size_mm=20,
        gap_mm=1,
    )

    assert result.columns == 47
    assert result.rows == 33
    assert result.total_pieces == 1551

    assert result.used_width_mm == 986
    assert result.used_height_mm == 692

    assert result.margin_x_mm == 7
    assert result.margin_y_mm == 4


def test_board_without_gaps():
    """Calculate pieces without spaces between them."""

    result = calculate_grid(
        board_width_mm=100,
        board_height_mm=100,
        piece_size_mm=20,
        gap_mm=0,
    )

    assert result.columns == 5
    assert result.rows == 5
    assert result.total_pieces == 25

    assert result.used_width_mm == 100
    assert result.used_height_mm == 100

    assert result.margin_x_mm == 0
    assert result.margin_y_mm == 0


def test_board_with_decimal_measurements():
    """Support decimal measurements."""

    result = calculate_grid(
        board_width_mm=300.5,
        board_height_mm=200.5,
        piece_size_mm=15.5,
        gap_mm=0.5,
    )

    assert result.columns > 0
    assert result.rows > 0
    assert result.total_pieces == result.columns * result.rows

    assert result.used_width_mm <= result.board_width_mm
    assert result.used_height_mm <= result.board_height_mm


def test_piece_larger_than_board():
    """Reject a piece that cannot fit on the board."""

    with pytest.raises(
        ValueError,
        match="does not fit",
    ):
        calculate_grid(
            board_width_mm=100,
            board_height_mm=100,
            piece_size_mm=150,
            gap_mm=0,
        )


def test_negative_gap():
    """Reject negative spaces between pieces."""

    with pytest.raises(
        ValueError,
        match="Gap cannot be negative",
    ):
        calculate_grid(
            board_width_mm=100,
            board_height_mm=100,
            piece_size_mm=20,
            gap_mm=-1,
        )


@pytest.mark.parametrize(
    "width,height,piece",
    [
        (0, 100, 20),
        (-100, 100, 20),
        (100, 0, 20),
        (100, -100, 20),
        (100, 100, 0),
        (100, 100, -20),
    ],
)
def test_invalid_dimensions(width, height, piece):
    """Reject zero and negative measurements."""

    with pytest.raises(ValueError):
        calculate_grid(
            board_width_mm=width,
            board_height_mm=height,
            piece_size_mm=piece,
            gap_mm=1,
        )


def test_non_numeric_value():
    """Reject non-numeric measurements."""

    with pytest.raises(TypeError):
        calculate_grid(
            board_width_mm="1000",
            board_height_mm=700,
            piece_size_mm=20,
            gap_mm=1,
        )


def test_result_can_be_converted_to_dictionary():
    """Convert the grid result to a serializable dictionary."""

    result = calculate_grid(
        board_width_mm=100,
        board_height_mm=100,
        piece_size_mm=20,
        gap_mm=0,
    )

    data = result.to_dict()

    assert isinstance(data, dict)
    assert data["columns"] == 5
    assert data["rows"] == 5
    assert data["total_pieces"] == 25
