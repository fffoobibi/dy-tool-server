from models import BaseModel
from peewee import IntegerField, CharField, SmallIntegerField


class ChatMessage(BaseModel):
    
    content = CharField(null=True)
    translate_content = CharField(null=True)  # Translated content
    platform = SmallIntegerField(index=True, default=0)  # 0 douyin

    send_user = CharField(max_length=50, null=False, index=True)  # 发送者
    recv_user = CharField(max_length=50, null=False, index=True)  # 接收者

