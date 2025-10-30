import settings
import os
import tempfile
import hashlib
from loguru import logger
from utils.response import success, fail
from constants import ResponseCode
from pathlib import Path
from os.path import join

from flask import Flask, request, send_from_directory


__all__ = ("init_upload", "get_upload_file_path", "save_upload_file")


def get_upload_file_path(file_path: str) -> str:
    logger.info(" {}", settings.UPLOAD_FOLDER)
    dst = file_path.replace(settings.UPLOAD_DOMAIN, "").replace("/files/", "./", 1)
    return join(settings.UPLOAD_FOLDER, dst)


def save_upload_file(file, upload_dir: str = "voice") -> str:
    """
    保存上传的文件并返回相对路径
    """
    if not file or file.filename == "":
        raise ValueError("No file provided")

    original_filename = file.filename.strip()
    if not original_filename:
        raise ValueError("Invalid filename")

    file_extension = ""
    if "." in original_filename:
        file_extension = original_filename.rsplit(".", 1)[1].lower()

    target_dir = os.path.join(settings.UPLOAD_FOLDER, upload_dir)
    if not Path(target_dir).exists():
        Path(target_dir).mkdir(parents=True, exist_ok=True)

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=target_dir, delete=False, suffix=".tmp"
        ) as temp_f:
            temp_file_path = temp_f.name
            hasher = hashlib.sha256()
            while chunk := file.stream.read(8192):
                hasher.update(chunk)
                temp_f.write(chunk)

        file_hash = hasher.hexdigest()
        unique_filename = (
            f"{file_hash}.{file_extension}" if file_extension else file_hash
        )
        final_filepath = os.path.join(target_dir, unique_filename)

        if os.path.exists(final_filepath):
            os.remove(temp_file_path)
            logger.info("File already exists, using existing: {}", final_filepath)
        else:
            os.rename(temp_file_path, final_filepath)
            logger.info("File saved to: {}", final_filepath)

        # 返回相对路径
        relative_path = os.path.join(upload_dir, unique_filename)
        return relative_path

    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        logger.error(f"Error saving upload file: {e}")
        raise e


def init_upload(app: Flask):
    """
    初始化上传功能，设置上传目录和相关配置。
    """

    upload_dir = settings.UPLOAD_FOLDER

    @app.post("/upload")
    def upload():
        upload_dir = request.form.get("dir")
        if not upload_dir:
            return fail("Directory is required.", ResponseCode.UPLOAD_FAILED)

        file = request.files.get("file")
        if not file or file.filename == "":
            return fail("No file part in the request.", ResponseCode.UPLOAD_FAILED)

        original_filename = file.filename.strip()
        if not original_filename:
            return fail("Invalid filename.", ResponseCode.UPLOAD_FAILED)

        file_extension = ""
        if "." in original_filename:
            file_extension = original_filename.rsplit(".", 1)[1].lower()

        target_dir = os.path.join(app.config["UPLOAD_FOLDER"], upload_dir)
        if not Path(target_dir).exists():
            Path(target_dir).mkdir(parents=True, exist_ok=True)

        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=target_dir, delete=False, suffix=".tmp"
            ) as temp_f:
                temp_file_path = temp_f.name
                hasher = hashlib.sha256()
                while chunk := file.stream.read(8192):
                    hasher.update(chunk)
                    temp_f.write(chunk)

            file_hash = hasher.hexdigest()
            unique_filename = (
                f"{file_hash}.{file_extension}" if file_extension else file_hash
            )
            final_filepath = os.path.join(target_dir, unique_filename)

            if os.path.exists(final_filepath):
                os.remove(temp_file_path)
                logger.info("File already exists, skipping save: {}", final_filepath)
            else:
                os.rename(temp_file_path, final_filepath)
                logger.info("File saved to: {}", final_filepath)

            file_url = f"{settings.UPLOAD_DOMAIN}/files/{upload_dir}/{unique_filename}"
            logger.info("File uploaded successfully: {}", file_url)
            return success(resp={"path": file_url})

        except Exception as e:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            logger.error(f"Error during file upload: {e}")
            return fail(f"An error occurred during file upload: {str(e)}", ResponseCode.UPLOAD_FAILED)

    @app.get("/files/<path:filename>")
    def download_files(filename):
        logger.info("filename {} {}", upload_dir, filename)
        return send_from_directory(upload_dir, filename, as_attachment=True)
