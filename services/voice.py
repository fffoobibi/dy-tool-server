import time
import requests
import typing as t
from typing import Dict, Any
from loguru import logger
from models.voice import UserSpeaker, TTSUsageRecord
from utils.response import success, fail
from utils.upload import get_upload_file_path


class FishSpeechAPI:
    @classmethod
    def clone_voice(
        cls,
        base_url: str,
        token: str,
        title: str,
        upload_file_path: str,
        texts: str | None = None,
        description: str | None = None,
        is_online: bool = True,
    ):
        """
        调用 fish-speech 克隆音色接口
        返回值示例:
        ```json
            {
            "_id": "<string>",
            "type": "svc",
            "title": "<string>",
            "description": "<string>",
            "cover_image": "<string>",
            "train_mode": "full",
            "state": "created",
            "tags": [
                "<string>"
            ],
            "samples": [],
            "created_at": "2023-11-07T05:31:56Z",
            "updated_at": "2023-11-07T05:31:56Z",
            "languages": [],
            "visibility": "public",
            "lock_visibility": false,
            "like_count": 123,
            "mark_count": 123,
            "shared_count": 123,
            "task_count": 123,
            "unliked": false,
            "liked": false,
            "marked": false,
            "author": {
                "_id": "<string>",
                "nickname": "<string>",
                "avatar": "<string>"
            }
            }
        ```
        """
        url = f"{base_url.rstrip('/')}/model"
        payload = {
            "visibility": "private",
            "type": "tts",
            "title": title,
            "description": description or "<string>",
            "train_mode": "fast",
            "texts": texts or "<string>",
            "tags": "<string>",
            "enhance_audio_quality": "false",
        }
        headers = {
            "Authorization": "Bearer " + token,
        }
        files = {"voices": open(get_upload_file_path(upload_file_path), "rb")}
        response = requests.post(url, data=payload, files=files, headers=headers)
        return response.json()

    @classmethod
    def tts(
        cls,
        base_url,
        model: t.Literal["s1", "speech-1.6", "speech-1.5"],
        text: str,
        speaker_id: str,
        token: str,
        is_online: bool = True,
    ) -> bytes:
        """
        调用 fish-speech TTS 接口进行语音合成
        返回值: 音频二进制数据
        """
        url = f"{base_url.rstrip('/')}/v1/tts"
        payload = {
            "text": text,
            "temperature": 0.9,
            "top_p": 0.9,
            "reference_id": speaker_id,
            "prosody": {"speed": 1, "volume": 0},
            "chunk_length": 200,
            "normalize": True,
            "format": "mp3",
            "sample_rate": None,
            "mp3_bitrate": 128,
            "opus_bitrate": 32,
            "latency": "normal",
        }
        headers = {
            "Authorization": "Bearer " + token,
            "model": model,
            "Content-Type": "application/json",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        return resp.content


class VoiceService:
    """语音服务类"""

    @staticmethod
    def create_speaker(
        user_id: int,
        speaker_id: str,
        speaker_name: str,
        api_url: str,
        audio_file_path: str = None,
        description: str = None,
    ) -> Dict[str, Any]:
        """创建用户音色"""
        try:
            # 检查音色名称是否重复
            existing = UserSpeaker.get_or_none(
                (UserSpeaker.user_id == user_id)
                & (UserSpeaker.speaker_name == speaker_name)
                & (UserSpeaker.is_deleted == False)
            )
            if existing:
                return fail(f"音色名称'{speaker_name}'已存在")

            # 检查speaker_id是否重复
            existing_id = UserSpeaker.get_or_none(
                (UserSpeaker.speaker_id == speaker_id)
                & (UserSpeaker.is_deleted == False)
            )
            if existing_id:
                return fail(f"speaker_id'{speaker_id}'已存在")

            # 创建音色记录
            speaker = UserSpeaker.create_speaker(
                user_id=user_id,
                speaker_id=speaker_id,
                speaker_name=speaker_name,
                api_url=api_url,
                audio_file_path=audio_file_path,
                description=description,
            )

            return success(
                {
                    "id": speaker.id,
                    "speaker_id": speaker.speaker_id,
                    "speaker_name": speaker.speaker_name,
                    "status": speaker.status,
                }
            )

        except Exception as e:
            logger.error(f"创建音色失败: {e}")
            return fail(f"创建音色失败: {str(e)}")

    @staticmethod
    def get_user_speakers(user_id: int, base_url:str, is_active: bool = True, ) -> Dict[str, Any]:
        """获取用户音色列表"""
        try:
            speakers = UserSpeaker.get_user_speakers(user_id, base_url, is_active)
            speaker_list = []

            for speaker in speakers:
                speaker_list.append(
                    {
                        "id": speaker.id,
                        "speaker_id": speaker.speaker_id,
                        "speaker_name": speaker.speaker_name,
                        "status": speaker.status,
                        "description": speaker.description,
                        "is_active": speaker.is_active,
                        "create_time": (
                            speaker.create_time.isoformat()
                            if speaker.create_time
                            else None
                        ),
                    }
                )

            return success({"speakers": speaker_list})

        except Exception as e:
            logger.error(f"获取用户音色列表失败: {e}")
            return fail(f"获取用户音色列表失败: {str(e)}")

    @staticmethod
    def update_speaker_status(
        speaker_id: str, status: str, is_active: bool = None
    ) -> Dict[str, Any]:
        """更新音色状态"""
        try:
            speaker = UserSpeaker.get_or_none(
                (UserSpeaker.speaker_id == speaker_id)
                & (UserSpeaker.is_deleted == False)
            )
            if not speaker:
                return fail("音色不存在")

            speaker.status = status
            if is_active is not None:
                speaker.is_active = is_active
            speaker.save()

            return success(
                {
                    "speaker_id": speaker.speaker_id,
                    "status": speaker.status,
                    "is_active": speaker.is_active,
                }
            )

        except Exception as e:
            logger.error(f"更新音色状态失败: {e}")
            return fail(f"更新音色状态失败: {str(e)}")

    @staticmethod
    def create_tts_record(
        user_id: int, speaker_id: str, text: str, api_url: str
    ) -> TTSUsageRecord:
        """创建TTS使用记录"""
        return TTSUsageRecord.create_record(
            user_id=user_id, speaker_id=speaker_id, text=text, api_url=api_url
        )

    @staticmethod
    def update_tts_success(
        record: TTSUsageRecord,
        audio_url: str = None,
        audio_file_path: str = None,
        audio_duration: float = None,
        cost_time: float = None,
    ) -> None:
        """更新TTS记录为成功"""
        record.update_success(
            audio_url=audio_url,
            audio_file_path=audio_file_path,
            audio_duration=audio_duration,
            cost_time=cost_time,
        )

    @staticmethod
    def update_tts_failed(
        record: TTSUsageRecord, error_message: str, cost_time: float = None
    ) -> None:
        """更新TTS记录为失败"""
        record.update_failed(error_message, cost_time)

    @staticmethod
    def get_user_tts_records(
        user_id: int, page: int = 1, page_size: int = 20, speaker_id: str = None
    ) -> Dict[str, Any]:
        """获取用户TTS使用记录"""
        try:
            query = TTSUsageRecord.select().where(
                (TTSUsageRecord.user_id == user_id)
                & (TTSUsageRecord.is_deleted == False)
            )

            if speaker_id:
                query = query.where(TTSUsageRecord.speaker_id == speaker_id)

            # 分页
            total = query.count()
            records = query.order_by(TTSUsageRecord.create_time.desc()).paginate(
                page, page_size
            )

            record_list = []
            for record in records:
                record_list.append(
                    {
                        "id": record.id,
                        "speaker_id": record.speaker_id,
                        "text": (
                            record.text[:100] + "..."
                            if len(record.text) > 100
                            else record.text
                        ),  # 截取前100字符
                        "text_length": record.text_length,
                        "audio_duration": record.audio_duration,
                        "audio_url": record.audio_url,
                        "status": record.status,
                        "error_message": record.error_message,
                        "cost_time": record.cost_time,
                        "create_time": (
                            record.create_time.isoformat()
                            if record.create_time
                            else None
                        ),
                    }
                )

            return success(
                {
                    "records": record_list,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                }
            )

        except Exception as e:
            logger.error(f"获取TTS记录失败: {e}")
            return fail(f"获取TTS记录失败: {str(e)}")

    @staticmethod
    def get_user_usage_stats(user_id: int, days: int = 30) -> Dict[str, Any]:
        """获取用户使用统计"""
        try:
            records = TTSUsageRecord.get_user_usage_stats(user_id, days)

            total_count = records.count()
            success_count = records.where(TTSUsageRecord.status == "success").count()
            failed_count = records.where(TTSUsageRecord.status == "failed").count()

            # 计算总文本长度和音频时长
            success_records = records.where(TTSUsageRecord.status == "success")
            total_text_length = sum(r.text_length for r in success_records)
            total_audio_duration = sum(r.audio_duration or 0 for r in success_records)
            avg_cost_time = (
                sum(r.cost_time or 0 for r in success_records) / success_count
                if success_count > 0
                else 0
            )

            return success(
                {
                    "days": days,
                    "total_count": total_count,
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "success_rate": (
                        round(success_count / total_count * 100, 2)
                        if total_count > 0
                        else 0
                    ),
                    "total_text_length": total_text_length,
                    "total_audio_duration": total_audio_duration,
                    "avg_cost_time": round(avg_cost_time, 3),
                }
            )

        except Exception as e:
            logger.error(f"获取使用统计失败: {e}")
            return fail(f"获取使用统计失败: {str(e)}")

    @staticmethod
    def verify_speaker_ownership(user_id: int, speaker_id: str) -> bool:
        """验证音色是否属于用户"""
        speaker = UserSpeaker.get_or_none(
            (UserSpeaker.user_id == user_id)
            & (UserSpeaker.speaker_id == speaker_id)
            & (UserSpeaker.is_deleted == False)
        )
        return speaker is not None

    @staticmethod
    def tts_synthesis(
        user_id: int,
        text: str,
        speaker_id: str,
        base_url: str,
        token: str,
        model: str = "speech-1.6",
    ) -> Dict[str, Any]:
        """TTS语音合成"""
        start_time = time.time()
        record = None

        try:
            # 验证音色是否属于当前用户
            if not VoiceService.verify_speaker_ownership(user_id, speaker_id):
                return fail("无权使用该音色", 403)

            # 创建TTS使用记录
            record = VoiceService.create_tts_record(user_id, speaker_id, text, base_url)

            # 调用FishSpeechAPI进行TTS合成
            audio_content = FishSpeechAPI.tts(
                base_url=base_url,
                model=model,
                text=text,
                speaker_id=speaker_id,
                token=token,
            )

            cost_time = time.time() - start_time

            if audio_content:
                # 这里可以将音频内容保存到文件或上传到存储服务
                # 暂时返回成功状态
                audio_url = None  # 实际应用中应该保存音频文件并返回URL
                audio_base64 = None  # 可以将audio_content转换为base64

                # 更新记录为成功
                VoiceService.update_tts_success(
                    record,
                    audio_url=audio_url,
                    audio_duration=None,  # 可以通过分析音频文件获取时长
                    cost_time=cost_time,
                )

                return success(
                    {
                        "audio_url": audio_url,
                        "audio_base64": audio_base64,
                        "audio_content": audio_content,  # 返回原始音频数据
                        "record_id": record.id,
                    }
                )
            else:
                # 更新记录为失败
                VoiceService.update_tts_failed(record, "TTS合成返回空数据", cost_time)
                logger.error("fish-speech TTS返回空数据")
                return fail("语音合成失败: 返回空数据", 500)

        except Exception as e:
            # 如果有记录，更新为失败
            if record:
                cost_time = time.time() - start_time
                VoiceService.update_tts_failed(record, str(e), cost_time)

            logger.error(f"语音合成异常: {e}")
            return fail(f"语音合成异常: {str(e)}", 500)

    @staticmethod
    def create_speaker_with_api(
        user_id: int,
        audio_file,
        speaker_name: str,
        base_url: str,
        token: str,
        description: str = None,
        texts: str = None,
    ) -> Dict[str, Any]:
        """创建音色 - 包含API调用的完整业务逻辑"""
        try:
            # 先保存上传的音频文件
            from utils.upload import save_upload_file

            audio_file_path = save_upload_file(audio_file)

            # 调用FishSpeechAPI创建音色
            result = FishSpeechAPI.clone_voice(
                base_url=base_url,
                token=token,
                title=speaker_name,
                upload_file_path=audio_file_path,
                texts=texts,
                description=description,
                is_online=True,
            )

            if result and result.get("_id"):
                speaker_id = result.get("_id")

                # 保存到数据库
                return VoiceService.create_speaker(
                    user_id=user_id,
                    speaker_id=speaker_id,
                    speaker_name=speaker_name,
                    api_url=base_url,
                    audio_file_path=audio_file_path,
                    description=description,
                )
            else:
                logger.error(f"fish-speech创建音色失败: {result}")
                return fail(f"创建音色失败: {result.get('message', '未知错误')}", 500)

        except Exception as e:
            logger.error(f"创建音色异常: {e}")
            return fail(f"创建音色异常: {str(e)}", 500)
