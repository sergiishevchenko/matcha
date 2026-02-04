import os
import uuid
from PIL import Image
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_IMAGE_SIZE = (1200, 1200)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file, upload_folder):
    if not file or not file.filename:
        return None, "No file selected."
    if not allowed_file(file.filename):
        return None, "Invalid file type. Allowed: png, jpg, jpeg, gif, webp."
    try:
        img = Image.open(file)
        img.verify()
        file.seek(0)
        img = Image.open(file)
    except Exception:
        return None, "Invalid image file."
    ext = file.filename.rsplit(".", 1)[1].lower()
    if ext == "jpeg":
        ext = "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_folder, filename)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
    img.save(filepath, quality=85, optimize=True)
    return filename, None


def delete_image_file(filename, upload_folder):
    if not filename:
        return
    filepath = os.path.join(upload_folder, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
