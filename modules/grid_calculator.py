"""Calculate the dimensions of a wooden mosaic grid."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class GridResult:
    """Result of calculating a wooden mosaic grid."""

    board_width_mm: float
    board_height_mm: float
    piece_size_mm: float
    gap_mm: float

    columns: int
    rows: int
    total_pieces: int

    used_width_mm: float
    used_height_mm: float

    margin_x_mm: float
    margin_y_mm: float

    def to_dict(self) -> dict:
        """Convert the result to a dictionary."""

        return asdict(self)


def calculate_grid(
    board_width_mm: float,
    board_height_mm: float,
    piece_size_mm: float,
    gap_mm: float = 0.0,
) -> GridResult:
    """
    Calculate how many square pieces fit on a wooden board.

    The unused space is divided equally between the opposite edges,
    producing centered horizontal and vertical margins.
    """

    values = {
        "board_width_mm": board_width_mm,
        "board_height_mm": board_height_mm,
        "piece_size_mm": piece_size_mm,
        "gap_mm": gap_mm,
    }

    for name, value in values.items():
        if not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a number.")

    if board_width_mm <= 0:
        raise ValueError("Board width must be greater than zero.")

    if board_height_mm <= 0:
        raise ValueError("Board height must be greater than zero.")

    if piece_size_mm <= 0:
        raise ValueError("Piece size must be greater than zero.")

    if gap_mm < 0:
        raise ValueError("Gap cannot be negative.")

    columns = math.floor(
        (board_width_mm + gap_mm)
        / (piece_size_mm + gap_mm)
    )

    rows = math.floor(
        (board_height_mm + gap_mm)
        / (piece_size_mm + gap_mm)
    )

    if columns < 1 or rows < 1:
        raise ValueError(
            "The selected piece size does not fit on the board."
        )

    used_width_mm = (
        columns * piece_size_mm
        + max(columns - 1, 0) * gap_mm
    )

    used_height_mm = (
        rows * piece_size_mm
        + max(rows - 1, 0) * gap_mm
    )

    margin_x_mm = (
        board_width_mm - used_width_mm
    ) / 2

    margin_y_mm = (
        board_height_mm - used_height_mm
    ) / 2

    return GridResult(
        board_width_mm=float(board_width_mm),
        board_height_mm=float(board_height_mm),
        piece_size_mm=float(piece_size_mm),
        gap_mm=float(gap_mm),
        columns=columns,
        rows=rows,
        total_pieces=columns * rows,
        used_width_mm=round(used_width_mm, 3),
        used_height_mm=round(used_height_mm, 3),
        margin_x_mm=round(margin_x_mm, 3),
        margin_y_mm=round(margin_y_mm, 3),
    )
