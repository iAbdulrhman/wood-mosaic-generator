"""Main Streamlit application for Wood Mosaic Generator."""

from __future__ import annotations

from io import BytesIO

import streamlit as st
from PIL import Image, ImageDraw

from modules.grid_calculator import GridResult, calculate_grid
from modules.image_processor import ImageProcessingResult, process_image
from modules.color_matcher import quantize_grid_image
from modules.color_ui import display_color_quantization_result


st.set_page_config(
    page_title="مولّد الفسيفساء الخشبية",
    page_icon="🪵",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_custom_styles() -> None:
    """Apply RTL direction and basic visual improvements."""

    st.markdown(
        """
        <style>
            html,
            body,
            .stApp {
                direction: rtl;
                text-align: right;
            }

            [data-testid="stAppViewContainer"] {
                direction: rtl;
            }

            [data-testid="stMainBlockContainer"] {
                max-width: 1450px;
                padding-top: 2rem;
                padding-bottom: 5rem;
            }

            [data-testid="stSidebar"] {
                direction: rtl;
                text-align: right;
                border-left: 1px solid #ded4ca;
            }

            [data-testid="stSidebar"] > div {
                direction: rtl;
            }

            [data-testid="stMetric"] {
                direction: rtl;
                text-align: center;
            }

            [data-testid="stMetricLabel"] {
                justify-content: center;
            }

            [data-testid="stMetricValue"] {
                text-align: center;
            }

            [data-testid="stVerticalBlockBorderWrapper"] {
                background-color: #ffffff;
                border-color: #ded2c7;
                box-shadow: 0 2px 8px rgba(69, 48, 32, 0.04);
            }

            h1,
            h2,
            h3,
            h4 {
                color: #69462f;
            }

            hr {
                border-color: #ebe1d8;
                margin-top: 1.2rem;
                margin-bottom: 1.2rem;
            }

            .project-subtitle {
                color: #6d6259;
                font-size: 1.05rem;
                margin-top: -0.7rem;
                margin-bottom: 1.8rem;
            }

            .section-description {
                color: #756a61;
                margin-top: -0.4rem;
                margin-bottom: 1rem;
            }

            .ltr-value {
                direction: ltr;
                display: inline-block;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_mm(value: float) -> str:
    """Format a measurement in millimeters."""

    return f"{value:,.2f} مم"


def format_file_size(size_bytes: int) -> str:
    """Format a file size for display."""

    if size_bytes < 1024:
        return f"{size_bytes} بايت"

    size_kb = size_bytes / 1024

    if size_kb < 1024:
        return f"{size_kb:,.1f} كيلوبايت"

    size_mb = size_kb / 1024

    return f"{size_mb:,.2f} ميجابايت"


def image_to_png_bytes(image: Image.Image) -> bytes:
    """Convert a Pillow image to downloadable PNG bytes."""

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    return buffer.getvalue()


def create_board_preview(
    grid: GridResult,
    canvas_width: int = 1000,
    canvas_height: int = 580,
) -> Image.Image:
    """Create a simplified board and grid preview."""

    preview = Image.new(
        mode="RGB",
        size=(canvas_width, canvas_height),
        color=(248, 245, 241),
    )

    draw = ImageDraw.Draw(preview)

    padding_x = 70
    padding_y = 55

    available_width = canvas_width - (padding_x * 2)
    available_height = canvas_height - (padding_y * 2)

    scale = min(
        available_width / grid.board_width_mm,
        available_height / grid.board_height_mm,
    )

    board_width_px = max(
        1,
        round(grid.board_width_mm * scale),
    )

    board_height_px = max(
        1,
        round(grid.board_height_mm * scale),
    )

    board_left = (canvas_width - board_width_px) // 2
    board_top = (canvas_height - board_height_px) // 2

    board_right = board_left + board_width_px
    board_bottom = board_top + board_height_px

    # Board shadow.
    draw.rounded_rectangle(
        (
            board_left + 8,
            board_top + 10,
            board_right + 8,
            board_bottom + 10,
        ),
        radius=8,
        fill=(218, 211, 204),
    )

    # Wooden board.
    draw.rounded_rectangle(
        (
            board_left,
            board_top,
            board_right,
            board_bottom,
        ),
        radius=8,
        fill=(229, 210, 188),
        outline=(104, 70, 47),
        width=4,
    )

    used_left = round(
        board_left + (grid.margin_x_mm * scale)
    )

    used_top = round(
        board_top + (grid.margin_y_mm * scale)
    )

    used_right = round(
        used_left + (grid.used_width_mm * scale)
    )

    used_bottom = round(
        used_top + (grid.used_height_mm * scale)
    )

    # Used mosaic area.
    draw.rectangle(
        (
            used_left,
            used_top,
            used_right,
            used_bottom,
        ),
        fill=(173, 199, 180),
        outline=(61, 103, 75),
        width=2,
    )

    piece_step_px = (
        grid.piece_size_mm + grid.gap_mm
    ) * scale

    # Draw grid lines only when they remain visible.
    if piece_step_px >= 2:
        for column in range(1, grid.columns):
            x = round(
                used_left + (column * piece_step_px)
            )

            if x < used_right:
                draw.line(
                    (
                        x,
                        used_top,
                        x,
                        used_bottom,
                    ),
                    fill=(240, 247, 242),
                    width=1,
                )

        for row in range(1, grid.rows):
            y = round(
                used_top + (row * piece_step_px)
            )

            if y < used_bottom:
                draw.line(
                    (
                        used_left,
                        y,
                        used_right,
                        y,
                    ),
                    fill=(240, 247, 242),
                    width=1,
                )

    return preview


def display_measurement_rows(
    rows: list[tuple[str, str]],
) -> None:
    """Display measurement labels and values in separate rows."""

    for index, (label, value) in enumerate(rows):
        label_column, value_column = st.columns(
            [1.25, 1],
            gap="small",
            vertical_alignment="center",
        )

        with label_column:
            st.write(label)

        with value_column:
            st.markdown(
                f"**{value}**"
            )

        if index < len(rows) - 1:
            st.divider()


def display_image_result(
    result: ImageProcessingResult,
    uploaded_name: str,
    uploaded_size: int,
) -> None:
    """Display source, cropped, and pixel-grid images."""

    st.header("2. معالجة الصورة")

    st.markdown(
        """
        <div class="section-description">
            تم قص الصورة تلقائيًا وفق نسبة شبكة القطع، ثم تحويلها
            إلى بكسل واحد لكل قطعة خشبية.
        </div>
        """,
        unsafe_allow_html=True,
    )

    original_column, cropped_column = st.columns(
        2,
        gap="large",
        vertical_alignment="top",
    )

    with original_column:
        with st.container(border=True):
            st.subheader("الصورة الأصلية")

            st.image(
                result.original_image,
                caption=(
                    f"{result.original_width_px} × "
                    f"{result.original_height_px} بكسل"
                ),
                width="stretch",
            )

            st.caption(
                "الصورة بعد قراءة الملف وتصحيح اتجاه EXIF."
            )

    with cropped_column:
        with st.container(border=True):
            st.subheader("الصورة بعد القص")

            st.image(
                result.cropped_image,
                caption=(
                    f"{result.cropped_width_px} × "
                    f"{result.cropped_height_px} بكسل"
                ),
                width="stretch",
            )

            st.caption(
                "تم القص من المنتصف دون تمديد الصورة أو تشويهها."
            )

    st.write("")

    with st.container(border=True):
        st.subheader("معاينة شبكة القطع")

        st.caption(
            "كل مربع ظاهر في هذه المعاينة يمثل قطعة خشبية واحدة."
        )

        preview_display, preview_details = st.columns(
            [1.7, 1],
            gap="large",
            vertical_alignment="top",
        )

        with preview_display:
            st.image(
                result.preview_image,
                caption=(
                    f"شبكة {result.columns} × {result.rows} — "
                    f"{result.total_pixels:,} قطعة"
                ),
                width="stretch",
            )

        with preview_details:
            with st.container(border=True):
                st.markdown("#### معلومات الملف")

                display_measurement_rows(
                    [
                        (
                            "اسم الملف",
                            uploaded_name,
                        ),
                        (
                            "حجم الملف",
                            format_file_size(uploaded_size),
                        ),
                        (
                            "أبعاد الصورة",
                            (
                                f"{result.original_width_px} × "
                                f"{result.original_height_px} px"
                            ),
                        ),
                        (
                            "أبعاد القص",
                            (
                                f"{result.cropped_width_px} × "
                                f"{result.cropped_height_px} px"
                            ),
                        ),
                    ]
                )

            with st.container(border=True):
                st.markdown("#### معلومات شبكة القطع")

                display_measurement_rows(
                    [
                        (
                            "الأعمدة",
                            f"{result.columns:,}",
                        ),
                        (
                            "الصفوف",
                            f"{result.rows:,}",
                        ),
                        (
                            "إجمالي القطع",
                            f"{result.total_pixels:,}",
                        ),
                        (
                            "نسبة الشبكة",
                            f"{result.grid_ratio:.4f}",
                        ),
                    ]
                )

            st.download_button(
                label="تنزيل المعاينة البكسلية PNG",
                data=image_to_png_bytes(
                    result.preview_image
                ),
                file_name="wood-mosaic-pixel-preview.png",
                mime="image/png",
                width="stretch",
            )

    with st.expander("عرض بيانات معالجة الصورة"):
        st.json(
            result.metadata(),
            expanded=True,
        )


apply_custom_styles()


# ---------------------------------------------------------
# Sidebar settings
# ---------------------------------------------------------

with st.sidebar:
    st.title("إعدادات المشروع")

    st.caption(
        "أدخل جميع القياسات بالملليمتر."
    )

    st.subheader("أبعاد اللوحة")

    board_width = st.number_input(
        "عرض اللوحة",
        min_value=50.0,
        max_value=10000.0,
        value=1000.0,
        step=10.0,
        format="%.1f",
        help="العرض الكامل للوح الخلفي.",
    )

    board_height = st.number_input(
        "ارتفاع اللوحة",
        min_value=50.0,
        max_value=10000.0,
        value=700.0,
        step=10.0,
        format="%.1f",
        help="الارتفاع الكامل للوح الخلفي.",
    )

    st.divider()

    st.subheader("القطع الخشبية")

    piece_size = st.number_input(
        "مقاس القطعة المربعة",
        min_value=2.0,
        max_value=500.0,
        value=20.0,
        step=1.0,
        format="%.1f",
        help="عرض وعمق كل قطعة خشبية.",
    )

    gap = st.number_input(
        "المسافة بين القطع",
        min_value=0.0,
        max_value=20.0,
        value=1.0,
        step=0.1,
        format="%.1f",
    )

    preview_cell_size = st.slider(
        "حجم خلية المعاينة",
        min_value=4,
        max_value=30,
        value=14,
        step=1,
        help=(
            "هذا الخيار يؤثر على حجم العرض فقط، "
            "ولا يغير مقاس القطعة الحقيقي."
        ),
    )

    st.divider()

    st.subheader("إعدادات الألوان")

    color_count = st.slider(
        "عدد الألوان المطلوب",
        min_value=2,
        max_value=64,
        value=12,
        step=1,
        help=(
            "عدد مجموعات الألوان التي سيتم استخدامها "
            "في اللوحة النهائية."
        ),
    )

    st.divider()

    st.caption(
        "المرحلة الحالية: الشبكة، معالجة الصورة، "
        "وتقليل الألوان."
    )


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.title("🪵 مولّد الفسيفساء الخشبية")

st.markdown(
    """
    <div class="project-subtitle">
        تحويل الصور إلى مخطط فسيفساء خشبية، مع حساب أبعاد
        الشبكة وعدد القطع وتجهيز المعاينة البكسلية.
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Grid calculations
# ---------------------------------------------------------

try:
    grid = calculate_grid(
        board_width_mm=board_width,
        board_height_mm=board_height,
        piece_size_mm=piece_size,
        gap_mm=gap,
    )

except (TypeError, ValueError) as error:
    st.error(
        f"تعذّر حساب شبكة اللوحة: {error}"
    )
    st.stop()


st.header("1. حساب شبكة اللوحة")

st.markdown(
    """
    <div class="section-description">
        تتحدث النتائج تلقائيًا عند تغيير أبعاد اللوحة أو القطع.
    </div>
    """,
    unsafe_allow_html=True,
)

metric_1, metric_2, metric_3, metric_4 = st.columns(
    4,
    gap="medium",
)

with metric_1:
    st.metric(
        label="عدد الأعمدة",
        value=f"{grid.columns:,}",
        border=True,
    )

with metric_2:
    st.metric(
        label="عدد الصفوف",
        value=f"{grid.rows:,}",
        border=True,
    )

with metric_3:
    st.metric(
        label="إجمالي القطع",
        value=f"{grid.total_pieces:,}",
        border=True,
    )

with metric_4:
    st.metric(
        label="مقاس الشبكة",
        value=f"{grid.columns} × {grid.rows}",
        border=True,
    )


st.write("")

board_preview_column, measurements_column = st.columns(
    [1.7, 1],
    gap="large",
    vertical_alignment="top",
)

with board_preview_column:
    with st.container(border=True):
        st.subheader("المعاينة الهندسية للوح")

        st.caption(
            "اللون الأخضر يمثل مساحة شبكة القطع، "
            "واللون الخشبي يمثل لوح الخلفية."
        )

        st.image(
            create_board_preview(grid),
            width="stretch",
        )

with measurements_column:
    with st.container(border=True):
        st.subheader("أبعاد الشبكة")

        display_measurement_rows(
            [
                (
                    "مقاس اللوح",
                    (
                        f"{grid.board_width_mm:g} × "
                        f"{grid.board_height_mm:g} مم"
                    ),
                ),
                (
                    "المساحة المستخدمة",
                    (
                        f"{grid.used_width_mm:g} × "
                        f"{grid.used_height_mm:g} مم"
                    ),
                ),
                (
                    "مقاس القطعة",
                    (
                        f"{grid.piece_size_mm:g} × "
                        f"{grid.piece_size_mm:g} مم"
                    ),
                ),
                (
                    "المسافة بين القطع",
                    format_mm(grid.gap_mm),
                ),
            ]
        )

    with st.container(border=True):
        st.subheader("هوامش التوسيط")

        display_measurement_rows(
            [
                (
                    "اليمين واليسار",
                    format_mm(grid.margin_x_mm),
                ),
                (
                    "الأعلى والأسفل",
                    format_mm(grid.margin_y_mm),
                ),
            ]
        )


with st.expander("عرض بيانات حساب الشبكة"):
    st.json(
        grid.to_dict(),
        expanded=True,
    )


st.divider()


# ---------------------------------------------------------
# Image upload and processing
# ---------------------------------------------------------

with st.container(border=True):
    st.subheader("رفع صورة التصميم")

    st.write(
        "اختر صورة واضحة ليتم قصها وتحويلها إلى شبكة القطع المحسوبة."
    )

    uploaded_file = st.file_uploader(
        "اختر صورة",
        type=[
            "jpg",
            "jpeg",
            "png",
            "webp",
            "bmp",
        ],
        accept_multiple_files=False,
        help="الحد الأقصى المحدد للمشروع هو 50 ميجابايت.",
        width="stretch",
    )

    if uploaded_file is None:
        st.info(
            "ارفع صورة لعرض نتيجة القص ومعاينة شبكة القطع."
        )


if uploaded_file is not None:
    try:
        with st.spinner(
            "جارٍ قراءة الصورة وقصها وإنشاء المعاينة..."
        ):
            image_result = process_image(
                source=uploaded_file,
                columns=grid.columns,
                rows=grid.rows,
                preview_cell_size=preview_cell_size,
            )

    except (TypeError, ValueError, OSError) as error:
        st.error(
            f"تعذّرت معالجة الصورة: {error}"
        )

    else:
        display_image_result(
            result=image_result,
            uploaded_name=uploaded_file.name,
            uploaded_size=uploaded_file.size,
        )

        st.divider()

        try:
            with st.spinner(
                "جارٍ تقليل الألوان وحساب كميات القطع..."
            ):
                color_result = quantize_grid_image(
                    grid_image=image_result.grid_image,
                    color_count=color_count,
                    preview_cell_size=preview_cell_size,
                    random_state=42,
                )

        except (TypeError, ValueError) as error:
            st.error(
                f"تعذّر تقليل ألوان الصورة: {error}"
            )

        else:
            display_color_quantization_result(
                source_preview=(
                    image_result.preview_image
                ),
                result=color_result,
            )


st.divider()


# ---------------------------------------------------------
# Project status
# ---------------------------------------------------------

st.header("تقدم المشروع")

status_1, status_2, status_3, status_4 = st.columns(
    4,
    gap="medium",
)

with status_1:
    st.success(
        "✅ حساب الشبكة"
    )

with status_2:
    st.success(
        "✅ معالجة الصورة"
    )

with status_3:
    st.success(
        "✅ تقليل الألوان"
    )

with status_4:
    st.info(
        "⏳ ترقيم القطع"
    )
