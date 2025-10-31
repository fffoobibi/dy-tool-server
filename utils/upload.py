import settings
import os
import tempfile
import hashlib
from loguru import logger
from utils.response import success, fail
from constants import ResponseCode
from pathlib import Path
from os.path import join
from mutagen import File

from flask import Flask, request, send_from_directory


__all__ = (
    "init_upload",
    "get_upload_file_path",
    "save_upload_file",
    "save_file_by_bytes",
    "get_audio_duration",
)


def get_upload_file_path(file_path: str) -> str:
    logger.info(" {}", settings.UPLOAD_FOLDER)
    dst = file_path.replace(settings.UPLOAD_DOMAIN, "").replace("/files/", "./", 1)
    return join(settings.UPLOAD_FOLDER, dst)


def upload_path_to_url(file_path: str) -> str:
    return (
        settings.UPLOAD_DOMAIN
        + "files/"
        + file_path.replace(settings.UPLOAD_FOLDER, settings.UPLOAD_DOMAIN)
        .replace("./", "/files/", 1)
        .replace("\\", "/")
    )


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


def save_file_by_bytes(
    content: bytes, upload_dir: str = "files", file_extension: str = "bin"
) -> tuple[str, str]:
    """
    保存二进制内容到文件并返回文件的url地址，本地地址

    Args:
        content: 要保存的二进制内容
        upload_dir: 上传目录，默认为 "files"
        file_extension: 文件扩展名，默认为 "bin"

    Returns:
        str: 文件的访问地址

    Raises:
        ValueError: 当内容为空时抛出
        Exception: 保存文件时的其他异常
    """
    if not content:
        raise ValueError("No content provided")

    target_dir = os.path.join(settings.UPLOAD_FOLDER, upload_dir)
    if not Path(target_dir).exists():
        Path(target_dir).mkdir(parents=True, exist_ok=True)

    temp_file_path = None
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            dir=target_dir, delete=False, suffix=".tmp"
        ) as temp_f:
            temp_file_path = temp_f.name
            # 计算文件hash
            hasher = hashlib.sha256()
            hasher.update(content)
            # 写入内容
            temp_f.write(content)

        file_hash = hasher.hexdigest()
        # 确保扩展名前有点
        if file_extension and not file_extension.startswith("."):
            file_extension = "." + file_extension
        unique_filename = (
            f"{file_hash}{file_extension}" if file_extension else file_hash
        )
        final_filepath = os.path.join(target_dir, unique_filename)

        if os.path.exists(final_filepath):
            # 文件已存在，删除临时文件
            os.remove(temp_file_path)
            logger.info("File already exists, using existing: {}", final_filepath)
        else:
            # 移动临时文件到最终位置
            os.rename(temp_file_path, final_filepath)
            logger.info("File saved to: {}", final_filepath)

        # 返回相对路径
        relative_path = os.path.join(upload_dir, unique_filename)
        # logger.info("relative_path {}", relative_path)
        rs = upload_path_to_url(relative_path)
        # logger.info("process file url: {}", rs)
        return rs, final_filepath

    except Exception as e:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        logger.error(f"Error saving file by bytes: {e}")
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
            return fail(
                f"An error occurred during file upload: {str(e)}",
                ResponseCode.UPLOAD_FAILED,
            )

    @app.get("/files/<path:filename>")
    def download_files(filename):
        logger.info("filename {} {}", upload_dir, filename)
        return send_from_directory(upload_dir, filename, as_attachment=True)


def get_audio_duration(file_path: str) -> float | None:
    """
    获取音频文件的时长（秒）

    Args:
        file_path: 音频文件的本地路径

    Returns:
        float: 音频时长（秒），如果无法获取则返回None
    """
    try:
        # 先尝试使用 mutagen 库
        try:
            audio_file = File(file_path)
            if audio_file and audio_file.info:
                duration = audio_file.info.length
                logger.info(f"使用mutagen获取音频时长: {duration}秒")
                return duration
        except ImportError:
            logger.warning("mutagen库未安装，尝试使用其他方法获取音频时长")
        except Exception as e:
            logger.warning(f"mutagen获取音频时长失败: {e}")

        # 如果mutagen不可用，尝试使用wave库（仅限wav格式）
        if file_path.lower().endswith(".wav"):
            try:
                import wave

                with wave.open(file_path, "rb") as wav_file:
                    frames = wav_file.getnframes()
                    rate = wav_file.getframerate()
                    duration = frames / float(rate)
                    logger.info(f"使用wave库获取音频时长: {duration}秒")
                    return duration
            except Exception as e:
                logger.warning(f"wave库获取音频时长失败: {e}")

        # 如果以上方法都不可用，返回None
        logger.warning(f"无法获取音频文件时长: {file_path}")
        return None

    except Exception as e:
        logger.error(f"获取音频时长时发生异常: {e}")
        return None
