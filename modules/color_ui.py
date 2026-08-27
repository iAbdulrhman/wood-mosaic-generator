"""Streamlit UI components for mosaic color results."""

from __future__ import annotations

import csv
from io import BytesIO, StringIO

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

from modules.color_matcher import ColorQuantizationResult


def image_to_png_bytes(image: Image.Image) -> bytes:
    """Convert a Pillow image to downloadable PNG bytes."""

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    return buffer.getvalue()


def create_color_swatch(
    rgb: tuple[int, int, int],
    width: int = 320,
    height: int = 100,
) -> Image.Image:
    """Create a solid color preview image."""

    image = Image.new(
        mode="RGB",
        size=(width, height),
        color=rgb,
    )

    draw = ImageDraw.Draw(image)

    draw.rectangle(
        (
            0,
            0,
            width - 1,
            height - 1,
        ),
        outline=(80, 80, 80),
        width=2,
    )

    return image


def palette_to_csv_bytes(
    result: ColorQuantizationResult,
) -> bytes:
    """Export the generated palette as UTF-8 CSV bytes."""

    text_buffer = StringIO()

    fieldnames = [
        "color_id",
        "red",
        "green",
        "blue",
        "hex_color",
        "piece_count",
        "percentage",
        "luminance",
    ]

    writer = csv.DictWriter(
        text_buffer,
        fieldnames=fieldnames,
    )

    writer.writeheader()

    for entry in result.palette:
        red, green, blue = entry.rgb

        writer.writerow(
            {
                "color_id": entry.color_id,
                "red": red,
                "green": green,
                "blue": blue,
                "hex_color": entry.hex_color,
                "piece_count": entry.piece_count,
                "percentage": round(
                    entry.percentage,
                    4,
                ),
                "luminance": round(
                    entry.luminance,
                    4,
                ),
            }
        )

    return text_buffer.getvalue().encode(
        "utf-8-sig"
    )


def create_palette_dataframe(
    result: ColorQuantizationResult,
) -> pd.DataFrame:
    """Create an Arabic palette table."""

    rows = []

    for entry in result.palette:
        red, green, blue = entry.rgb

        rows.append(
            {
                "كود اللون": entry.color_id,
                "HEX": entry.hex_color,
                "R": red,
                "G": green,
                "B": blue,
                "عدد القطع": entry.piece_count,
                "النسبة": entry.percentage / 100,
            }
        )

    return pd.DataFrame(rows)


def display_palette_cards(
    result: ColorQuantizationResult,
) -> None:
    """Display generated colors as separate bordered cards."""

    st.subheader("لوحة الألوان الناتجة")

    st.caption(
        "تم ترتيب الألوان من الداكن إلى الفاتح. "
        "كل كود لون سيُستخدم لاحقًا لترقيم القطع."
    )

    palette = list(result.palette)
    cards_per_row = 4

    for start_index in range(
        0,
        len(palette),
        cards_per_row,
    ):
        row_entries = palette[
            start_index:start_index + cards_per_row
        ]

        columns = st.columns(
            cards_per_row,
            gap="medium",
        )

        for column_index, entry in enumerate(
            row_entries
        ):
            with columns[column_index]:
                with st.container(border=True):
                    st.image(
                        create_color_swatch(
                            entry.rgb
                        ),
                        width="stretch",
                    )

                    st.markdown(
                        f"### {entry.color_id}"
                    )

                    st.code(
                        entry.hex_color,
                        language=None,
                    )

                    red, green, blue = entry.rgb

                    st.caption(
                        f"RGB: {red}, {green}, {blue}"
                    )

                    st.metric(
                        label="عدد القطع",
                        value=f"{entry.piece_count:,}",
                        border=True,
                    )

                    st.progress(
                        min(
                            entry.percentage / 100,
                            1.0,
                        ),
                        text=(
                            f"{entry.percentage:.2f}% "
                            "من اللوحة"
                        ),
                    )


def display_color_comparison(
    source_preview: Image.Image,
    result: ColorQuantizationResult,
) -> None:
    """Display before-and-after color previews."""

    source_column, quantized_column = st.columns(
        2,
        gap="large",
        vertical_alignment="top",
    )

    with source_column:
        with st.container(border=True):
            st.subheader("قبل تقليل الألوان")

            st.image(
                source_preview,
                caption=(
                    "شبكة الصورة بألوانها "
                    "قبل التجميع"
                ),
                width="stretch",
            )

    with quantized_column:
        with st.container(border=True):
            st.subheader("بعد تقليل الألوان")

            st.image(
                result.preview_image,
                caption=(
                    f"{result.actual_color_count} "
                    "ألوان مستخدمة"
                ),
                width="stretch",
            )


def display_palette_table(
    result: ColorQuantizationResult,
) -> None:
    """Display palette quantities and download controls."""

    table_column, download_column = st.columns(
        [1.65, 1],
        gap="large",
        vertical_alignment="top",
    )

    with table_column:
        with st.container(border=True):
            st.subheader("جدول كميات الألوان")

            palette_dataframe = (
                create_palette_dataframe(result)
            )

            st.dataframe(
                palette_dataframe,
                width="stretch",
                hide_index=True,
                column_config={
                    "كود اللون": st.column_config.TextColumn(
                        "كود اللون",
                        width="small",
                    ),
                    "HEX": st.column_config.TextColumn(
                        "HEX",
                        width="small",
                    ),
                    "R": st.column_config.NumberColumn(
                        "R",
                        format="%d",
                    ),
                    "G": st.column_config.NumberColumn(
                        "G",
                        format="%d",
                    ),
                    "B": st.column_config.NumberColumn(
                        "B",
                        format="%d",
                    ),
                    "عدد القطع": st.column_config.NumberColumn(
                        "عدد القطع",
                        format="%d",
                    ),
                    "النسبة": st.column_config.ProgressColumn(
                        "النسبة",
                        min_value=0,
                        max_value=1,
                        format="percent",
                    ),
                },
            )

    with download_column:
        with st.container(border=True):
            st.subheader("تنزيل النتائج")

            st.write(
                "يمكن تنزيل المعاينة وجدول "
                "الألوان لاستخدامهما لاحقًا."
            )

            st.download_button(
                label="تنزيل المعاينة الملونة PNG",
                data=image_to_png_bytes(
                    result.preview_image
                ),
                file_name=(
                    "wood-mosaic-quantized-preview.png"
                ),
                mime="image/png",
                width="stretch",
            )

            st.download_button(
                label="تنزيل شبكة الألوان PNG",
                data=image_to_png_bytes(
                    result.quantized_image
                ),
                file_name=(
                    "wood-mosaic-color-grid.png"
                ),
                mime="image/png",
                width="stretch",
            )

            st.download_button(
                label="تنزيل جدول الألوان CSV",
                data=palette_to_csv_bytes(
                    result
                ),
                file_name=(
                    "wood-mosaic-palette.csv"
                ),
                mime="text/csv",
                width="stretch",
            )


def display_color_quantization_result(
    source_preview: Image.Image,
    result: ColorQuantizationResult,
) -> None:
    """Display the complete color quantization section."""

    st.header("3. تقليل الألوان")

    st.caption(
        "يتم تجميع ألوان الصورة في عدد محدود من "
        "المجموعات لتسهيل الطلاء وتجهيز القطع."
    )

    metric_1, metric_2, metric_3, metric_4 = st.columns(
        4,
        gap="medium",
    )

    with metric_1:
        st.metric(
            label="الألوان المطلوبة",
            value=result.requested_color_count,
            border=True,
        )

    with metric_2:
        st.metric(
            label="الألوان الفعلية",
            value=result.actual_color_count,
            border=True,
        )

    with metric_3:
        st.metric(
            label="إجمالي القطع",
            value=f"{result.total_pieces:,}",
            border=True,
        )

    with metric_4:
        average_pieces = (
            result.total_pieces
            / result.actual_color_count
        )

        st.metric(
            label="المتوسط لكل لون",
            value=f"{average_pieces:,.1f}",
            border=True,
        )

    st.write("")

    display_color_comparison(
        source_preview=source_preview,
        result=result,
    )

    st.write("")

    display_palette_cards(result)

    st.write("")

    display_palette_table(result)

    with st.expander(
        "عرض بيانات الألوان الخام"
    ):
        st.json(
            result.metadata(),
            expanded=True,
        )
