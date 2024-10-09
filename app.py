from flask import Flask, render_template, send_file, url_for, request, redirect, flash
from minio import Minio
from minio.error import S3Error
import io
import zipfile
import os
import string
import random

app = Flask(__name__)
app.secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(32))

MINIO_URL = os.getenv("MINIO_URL")
SECURE = os.getenv("SECURE")
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")
REGION = os.getenv("REGION")
ENABLE_UPLOAD = os.getenv("ENABLE_UPLOAD", "False").lower() == "true"

minio_client = Minio(
    MINIO_URL,
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    secure=SECURE,
    region=REGION,
)


def human_readable_size(size, decimal_places=2):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


@app.route("/")
@app.route("/<path:prefix>")
def list_files(prefix=""):
    try:
        objects = minio_client.list_objects(BUCKET_NAME, prefix=prefix, recursive=False)
        folders = set()
        files = []
        for obj in objects:
            if obj.is_dir:
                folders.add(obj.object_name)
            else:
                file_info = minio_client.stat_object(BUCKET_NAME, obj.object_name)
                file_size = human_readable_size(file_info.size)
                created_at = file_info.last_modified.strftime("%Y-%m-%d %H:%M:%S")
                files.append((obj.object_name, file_size, created_at))

        folders = sorted(folders)
        files = sorted(files, key=lambda x: x[0])
    except S3Error as err:
        return f"Error: {err}"

    return render_template(
        "index.html",
        folders=folders,
        files=files,
        prefix=prefix,
        enable_upload=ENABLE_UPLOAD,
    )


@app.route("/download/<path:filename>")
def download_file(filename):
    try:
        response = minio_client.get_object(BUCKET_NAME, filename)
        data = io.BytesIO(response.read())
        data.seek(0)
        return send_file(data, as_attachment=True, download_name=filename)
    except S3Error as err:
        return f"Error: {err}"


@app.route("/download_dir/<path:prefix>")
def download_directory(prefix):
    try:
        objects = minio_client.list_objects(BUCKET_NAME, prefix=prefix, recursive=True)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for obj in objects:
                file_data = minio_client.get_object(BUCKET_NAME, obj.object_name)
                data = file_data.read()
                zip_file.writestr(obj.object_name[len(prefix) :], data)
        zip_buffer.seek(0)
        return send_file(
            zip_buffer, as_attachment=True, download_name=f"{prefix.strip('/')}.zip"
        )
    except S3Error as err:
        return f"Error: {err}"

@app.route("/upload", methods=["POST"])
def upload_file():
    if not ENABLE_UPLOAD:
        flash("File upload is disabled.", "danger")
        return redirect(url_for("list_files"))

    if "file" not in request.files:
        flash("No file part", "danger")
        return redirect(url_for("list_files"))

    file = request.files["file"]

    if file.filename == "":
        flash("No selected file", "danger")
        return redirect(url_for("list_files"))

    try:
        minio_client.put_object(
            BUCKET_NAME, file.filename, file.stream, length=-1, part_size=10 * 1024 * 1024
        )
        flash(f"File '{file.filename}' uploaded successfully!", "success")
    except S3Error as err:
        flash(f"Error uploading file: {err}", "danger")

    return redirect(url_for("list_files"))


if __name__ == "__main__":
    app.static_folder = "static"
    app.run(debug=True)
