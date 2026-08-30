"""Generate manufacturing records for wooden mosaic pieces."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from modules.color_matcher import ColorQuantizationResult
from modules.grid_calculator import GridResult


@dataclass(frozen=True)
class PieceRecord:
    """Manufacturing information for one mosaic piece."""

    piece_id: str
    sequence: int

    row: int
    column: int

    color_id: str
    color_index: int
    hex_color: str

    red: int
    green: int
    blue: int

    x_mm: float
    y_mm: float

    center_x_mm: float
    center_y_mm: float

    width_mm: float
    height_mm: float

    def to_dict(self) -> dict:
        """Return a serializable piece record."""

        return asdict(self)


def validate_piece_inputs(
    grid: GridResult,
    colors: ColorQuantizationResult,
) -> None:
    """Validate compatibility between grid and color results."""

    if grid.columns != colors.columns:
        raise ValueError(
            "Grid columns do not match the color grid."
        )

    if grid.rows != colors.rows:
        raise ValueError(
            "Grid rows do not match the color grid."
        )

    expected_shape = (
        grid.rows,
        grid.columns,
    )

    if colors.color_index_grid.shape != expected_shape:
        raise ValueError(
            "Color index grid has an invalid shape."
        )

    if len(colors.palette) != colors.actual_color_count:
        raise ValueError(
            "Palette size does not match the actual color count."
        )


def generate_piece_records(
    grid: GridResult,
    colors: ColorQuantizationResult,
) -> tuple[PieceRecord, ...]:
    """
    Generate one manufacturing record for every mosaic cell.

    Coordinates are measured from the top-left corner of the full
    background board. Row and column numbering starts at 1.
    """

    validate_piece_inputs(
        grid=grid,
        colors=colors,
    )

    records: list[PieceRecord] = []
    sequence = 1

    for row_index in range(grid.rows):
        for column_index in range(grid.columns):
            color_index = int(
                colors.color_index_grid[
                    row_index,
                    column_index,
                ]
            )

            if not 0 <= color_index < len(colors.palette):
                raise ValueError(
                    "A piece references an invalid palette color."
                )

            palette_entry = colors.palette[color_index]

            x_mm = (
                grid.margin_x_mm
                + column_index
                * (
                    grid.piece_size_mm
                    + grid.gap_mm
                )
            )

            y_mm = (
                grid.margin_y_mm
                + row_index
                * (
                    grid.piece_size_mm
                    + grid.gap_mm
                )
            )

            center_x_mm = (
                x_mm
                + grid.piece_size_mm / 2
            )

            center_y_mm = (
                y_mm
                + grid.piece_size_mm / 2
            )

            red, green, blue = palette_entry.rgb

            records.append(
                PieceRecord(
                    piece_id=(
                        f"R{row_index + 1:03d}-"
                        f"C{column_index + 1:03d}"
                    ),
                    sequence=sequence,
                    row=row_index + 1,
                    column=column_index + 1,
                    color_id=palette_entry.color_id,
                    color_index=color_index,
                    hex_color=palette_entry.hex_color,
                    red=red,
                    green=green,
                    blue=blue,
                    x_mm=round(x_mm, 3),
                    y_mm=round(y_mm, 3),
                    center_x_mm=round(center_x_mm, 3),
                    center_y_mm=round(center_y_mm, 3),
                    width_mm=grid.piece_size_mm,
                    height_mm=grid.piece_size_mm,
                )
            )

            sequence += 1

    return tuple(records)


def piece_records_to_rows(
    records: tuple[PieceRecord, ...],
) -> list[dict]:
    """Convert piece records to tabular rows."""

    return [
        record.to_dict()
        for record in records
    ]


def summarize_pieces_by_color(
    records: tuple[PieceRecord, ...],
) -> list[dict]:
    """Count generated piece records by color."""

    summary: dict[str, dict] = {}

    for record in records:
        if record.color_id not in summary:
            summary[record.color_id] = {
                "color_id": record.color_id,
                "hex_color": record.hex_color,
                "red": record.red,
                "green": record.green,
                "blue": record.blue,
                "piece_count": 0,
            }

        summary[record.color_id]["piece_count"] += 1

    return sorted(
        summary.values(),
        key=lambda item: item["color_id"],
    )


def create_piece_id_grid(
    records: tuple[PieceRecord, ...],
    rows: int,
    columns: int,
) -> np.ndarray:
    """Create a two-dimensional array of piece identifiers."""

    if rows <= 0 or columns <= 0:
        raise ValueError(
            "Rows and columns must be greater than zero."
        )

    if len(records) != rows * columns:
        raise ValueError(
            "Record count does not match the grid dimensions."
        )

    identifiers = np.array(
        [
            record.piece_id
            for record in records
        ],
        dtype=object,
    )

    return identifiers.reshape(
        rows,
        columns,
    )
