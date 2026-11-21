import os
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image


def convert_image_to_webp(image_file, quality=90):
    """
    هر فایل تصویری ارسال‌شده یا آپلود‌شده (JPG, PNG, GIF, BMP و ...)
    را به‌صورت خودکار به فرمت بهینه و فشرده WebP تبدیل می‌کند.
    """
    if not image_file:
        return image_file

    try:
        filename = getattr(image_file, "name", "image.webp")
        base_name, _ = os.path.splitext(os.path.basename(filename))
        if not base_name:
            base_name = "image"

        if hasattr(image_file, "seek"):
            image_file.seek(0)

        img = Image.open(image_file)

        # مدیریت کانال رنگی و ترنسپرنسی
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

        buffer = BytesIO()
        img.save(buffer, format="WEBP", quality=quality, method=6)
        buffer.seek(0)

        webp_filename = f"{base_name}.webp"
        content_file = ContentFile(buffer.getvalue(), name=webp_filename)
        content_file.content_type = "image/webp"
        return content_file
    except Exception:
        if hasattr(image_file, "seek"):
            try:
                image_file.seek(0)
            except Exception:
                pass
        return image_file
