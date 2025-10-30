from peewee import (
    CharField,
    IntegerField,
    TextField,
    FloatField,
    ForeignKeyField,
    DateTimeField,
    BooleanField,
)
from datetime import datetime
from models import BaseModel
from models.account import User

__all__ = ("UserSpeaker", "TTSUsageRecord")


class UserSpeaker(BaseModel):
    """用户音色模型"""

    user_id = IntegerField(null=False, index=True)
    speaker_id = CharField(max_length=100, null=False, unique=True, index=True)
    speaker_name = CharField(max_length=100, null=False)
    audio_file_path = CharField(max_length=500, null=True)  # 原始音频文件路径
    status = CharField(
        max_length=20, default="created", null=False
    )  # created, training, ready, failed
    api_url = CharField(max_length=500, null=False)  # fish-speech API地址
    description = TextField(null=True)  # 音色描述
    is_active = BooleanField(default=True, index=True)  # 是否可用

    class Meta:
        table_name = "user_speakers"
        indexes = ((("user_id", "speaker_name"), False),)  # 用户下音色名称不重复

    @classmethod
    def get_user_speakers(cls, user_id: int, base_url: str, is_active: bool = True):
        """获取用户的音色列表"""
        query = cls.select().where(
            (cls.user_id == user_id)
            & (cls.is_deleted == False)
            & (cls.api_url == base_url)
        )
        if is_active is not None:
            query = query.where(cls.is_active == is_active)
        return query

    @classmethod
    def create_speaker(
        cls,
        user_id: int,
        speaker_id: str,
        speaker_name: str,
        api_url: str,
        audio_file_path: str = None,
        description: str = None,
    ):
        """创建音色记录"""
        return cls.create(
            user_id=user_id,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            api_url=api_url,
            audio_file_path=audio_file_path,
            description=description,
            status="created",
            create_time=datetime.now(),
        )


class TTSUsageRecord(BaseModel):
    """TTS使用记录"""

    user_id = IntegerField(null=False, index=True)
    speaker_id = CharField(max_length=100, null=False, index=True)
    text = TextField(null=False)  # 合成的文本
    text_length = IntegerField(null=False, default=0)  # 文本长度
    audio_duration = FloatField(null=True)  # 音频时长(秒)
    audio_file_path = CharField(max_length=500, null=True)  # 生成的音频文件路径
    audio_url = CharField(max_length=500, null=True)  # 音频下载地址
    api_url = CharField(max_length=500, null=False)  # 使用的API地址
    status = CharField(
        max_length=20, default="pending", null=False
    )  # pending, success, failed
    error_message = TextField(null=True)  # 错误信息
    cost_time = FloatField(null=True)  # 合成耗时(秒)

    class Meta:
        table_name = "tts_usage_records"
        indexes = (
            (("user_id", "create_time"), False),
            (("speaker_id", "create_time"), False),
        )

    @classmethod
    def create_record(cls, user_id: int, speaker_id: str, text: str, api_url: str):
        """创建TTS使用记录"""
        return cls.create(
            user_id=user_id,
            speaker_id=speaker_id,
            text=text,
            text_length=len(text),
            api_url=api_url,
            status="pending",
            create_time=datetime.now(),
        )

    def update_success(
        self,
        audio_url: str = None,
        audio_file_path: str = None,
        audio_duration: float = None,
        cost_time: float = None,
    ):
        """更新为成功状态"""
        self.status = "success"
        if audio_url:
            self.audio_url = audio_url
        if audio_file_path:
            self.audio_file_path = audio_file_path
        if audio_duration:
            self.audio_duration = audio_duration
        if cost_time:
            self.cost_time = cost_time
        self.save()

    def update_failed(self, error_message: str, cost_time: float = None):
        """更新为失败状态"""
        self.status = "failed"
        self.error_message = error_message
        if cost_time:
            self.cost_time = cost_time
        self.save()

    @classmethod
    def get_user_usage_stats(cls, user_id: int, days: int = 30):
        """获取用户使用统计"""
        from datetime import timedelta

        start_date = datetime.now() - timedelta(days=days)

        return cls.select().where(
            (cls.user_id == user_id)
            & (cls.create_time >= start_date)
            & (cls.is_deleted == False)
        )
