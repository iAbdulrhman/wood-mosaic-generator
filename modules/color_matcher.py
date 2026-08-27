"""Color quantization utilities for wooden mosaic designs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

from modules.image_processor import create_pixel_preview


@dataclass(frozen=True)
class PaletteEntry:
    """A single generated mosaic color."""

    color_id: str
    rgb: tuple[int, int, int]
    hex_color: str
    piece_count: int
    percentage: float
    luminance: float

    def to_dict(self) -> dict:
        """Return a serializable representation."""

        return {
            "color_id": self.color_id,
            "rgb": list(self.rgb),
            "hex_color": self.hex_color,
            "piece_count": self.piece_count,
            "percentage": round(self.percentage, 4),
            "luminance": round(self.luminance, 4),
        }


@dataclass(frozen=True)
class ColorQuantizationResult:
    """Result of reducing a grid image to a limited palette."""

    quantized_image: Image.Image
    preview_image: Image.Image
    palette: tuple[PaletteEntry, ...]
    color_index_grid: np.ndarray
    requested_color_count: int
    actual_color_count: int
    columns: int
    rows: int
    total_pieces: int

    def palette_rows(self) -> list[dict]:
        """Return palette entries as serializable rows."""

        return [
            entry.to_dict()
            for entry in self.palette
        ]

    def metadata(self) -> dict:
        """Return summary information."""

        return {
            "requested_color_count": self.requested_color_count,
            "actual_color_count": self.actual_color_count,
            "columns": self.columns,
            "rows": self.rows,
            "total_pieces": self.total_pieces,
            "palette": self.palette_rows(),
        }


def validate_color_count(color_count: int) -> None:
    """Validate the requested number of colors."""

    if isinstance(color_count, bool) or not isinstance(
        color_count,
        int,
    ):
        raise TypeError(
            "Color count must be an integer."
        )

    if color_count < 2:
        raise ValueError(
            "Color count must be at least 2."
        )

    if color_count > 256:
        raise ValueError(
            "Color count cannot exceed 256."
        )


def rgb_to_hex(
    rgb: tuple[int, int, int],
) -> str:
    """Convert an RGB color to a hexadecimal color string."""

    red, green, blue = rgb

    for channel in rgb:
        if not 0 <= channel <= 255:
            raise ValueError(
                "RGB channel values must be between 0 and 255."
            )

    return f"#{red:02X}{green:02X}{blue:02X}"


def calculate_luminance(
    rgb: tuple[int, int, int],
) -> float:
    """
    Calculate relative display luminance for palette ordering.

    This value is used only to order generated colors from dark to light.
    """

    red, green, blue = rgb

    return (
        0.2126 * red
        + 0.7152 * green
        + 0.0722 * blue
    )


def _sort_palette_and_remap_labels(
    centers: np.ndarray,
    labels: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Sort colors from dark to light and remap their labels."""

    luminance_values = np.array(
        [
            calculate_luminance(
                (
                    int(center[0]),
                    int(center[1]),
                    int(center[2]),
                )
            )
            for center in centers
        ],
        dtype=np.float64,
    )

    sort_order = np.argsort(
        luminance_values,
        kind="stable",
    )

    sorted_centers = centers[sort_order]

    old_to_new = np.empty(
        len(sort_order),
        dtype=np.int32,
    )

    old_to_new[sort_order] = np.arange(
        len(sort_order),
        dtype=np.int32,
    )

    remapped_labels = old_to_new[labels]

    return sorted_centers, remapped_labels


def quantize_grid_image(
    grid_image: Image.Image,
    color_count: int,
    preview_cell_size: int = 16,
    random_state: int = 42,
) -> ColorQuantizationResult:
    """
    Reduce a grid image to a limited number of colors.

    Every source pixel represents one wooden piece. KMeans assigns every
    piece to exactly one generated palette color.
    """

    validate_color_count(color_count)

    if grid_image.width <= 0 or grid_image.height <= 0:
        raise ValueError(
            "Grid image dimensions must be greater than zero."
        )

    rgb_image = grid_image.convert("RGB")

    pixels = np.asarray(
        rgb_image,
        dtype=np.uint8,
    )

    flat_pixels = pixels.reshape(-1, 3)

    unique_colors = np.unique(
        flat_pixels,
        axis=0,
    )

    actual_color_count = min(
        color_count,
        len(unique_colors),
    )

    if actual_color_count < 1:
        raise ValueError(
            "The image does not contain any usable colors."
        )

    if actual_color_count == 1:
        centers = unique_colors.astype(
            np.uint8
        )

        labels = np.zeros(
            len(flat_pixels),
            dtype=np.int32,
        )

    else:
        model = KMeans(
            n_clusters=actual_color_count,
            random_state=random_state,
            n_init=10,
        )

        labels = model.fit_predict(
            flat_pixels.astype(np.float32)
        )

        centers = np.clip(
            np.rint(model.cluster_centers_),
            0,
            255,
        ).astype(np.uint8)

    centers, labels = _sort_palette_and_remap_labels(
        centers=centers,
        labels=labels,
    )

    quantized_pixels = centers[labels].reshape(
        pixels.shape
    )

    quantized_image = Image.fromarray(
        quantized_pixels,
        mode="RGB",
    )

    preview_image = create_pixel_preview(
        grid_image=quantized_image,
        cell_display_size=preview_cell_size,
    )

    counts = np.bincount(
        labels,
        minlength=actual_color_count,
    )

    total_pieces = len(labels)

    palette_entries: list[PaletteEntry] = []

    for index, center in enumerate(centers):
        rgb = (
            int(center[0]),
            int(center[1]),
            int(center[2]),
        )

        piece_count = int(counts[index])

        percentage = (
            piece_count / total_pieces
        ) * 100

        palette_entries.append(
            PaletteEntry(
                color_id=f"C{index + 1:02d}",
                rgb=rgb,
                hex_color=rgb_to_hex(rgb),
                piece_count=piece_count,
                percentage=percentage,
                luminance=calculate_luminance(rgb),
            )
        )

    color_index_grid = labels.reshape(
        rgb_image.height,
        rgb_image.width,
    )

    return ColorQuantizationResult(
        quantized_image=quantized_image,
        preview_image=preview_image,
        palette=tuple(palette_entries),
        color_index_grid=color_index_grid,
        requested_color_count=color_count,
        actual_color_count=actual_color_count,
        columns=rgb_image.width,
        rows=rgb_image.height,
        total_pieces=total_pieces,
    )
