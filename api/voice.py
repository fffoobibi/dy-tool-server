from flask import Blueprint, request
from utils.jwt import verify_auth
from utils.response import fail, success
from utils import current_user
from utils.redis import get_redis
from services.voice import VoiceService, FishSpeechAPI
from loguru import logger
import json

bp = Blueprint("voice", __name__)

redis_client = get_redis()


@bp.before_request
def verify():
    verify_auth()


@bp.post("/credit")
def credit():
    """获取fish-speech账号credit"""
    token = request.json.get("token", "").strip()
    if not token:
        return fail("token不能为空", 400)
    try:
        credit_info = FishSpeechAPI.get_credit(token)
        return success(resp=credit_info)
    except Exception as e:
        logger.error(f"获取fish-speech credit失败: {str(e)}")
        return fail(f"获取credit失败: {str(e)}", 500)


@bp.post("/check_play_available")
def check_available():
    channels = request.json.get("channels") or []
    res = redis_client.execute_command("PUBSUB", "NUMSUB", *channels)
    val = dict(zip(res[::2], res[1::2]))
    logger.debug(f"频道 {channels} 订阅数: {val}")
    return success(resp=val)


@bp.post("/play")
def play():
    """语音播放接口"""
    type = request.json.get("type").strip()
    channel = request.json.get("channel", "").strip()
    audio_url = request.json.get("audio_url", "").strip()
    if not channel or not audio_url:
        return fail("channel和play_url不能为空", 400)
    redis_client.publish(
        channel, json.dumps({"type": type, "data": audio_url}, ensure_ascii=False)
    )
    return success(msg="语音播放指令已发送")


@bp.post("/tts")
def tts():
    """语音克隆接口
    ---
    tags:
      - voice
    summary: 使用fish-speech克隆语音，文本转语音
    description: 输入文本和目标音色，返回语音音频URL或base64
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - text
            - speaker_id
            - base_url
            - token
          properties:
            text:
              type: string
              description: 需要合成的文本
              example: "你好，欢迎来到直播间！"
            speaker_id:
              type: string
              description: 目标音色ID（fish-speech模型）
              example: "fish-001"
            base_url:
              type: string
              description: fish-speech API基础地址
              example: "https://api.fish.audio"
            token:
              type: string
              description: fish-speech API认证token
              example: "your_api_token"
            model:
              type: string
              description: 使用的模型版本
              example: "speech-1.6"
              enum: ["s1", "speech-1.6", "speech-1.5"]
    responses:
      200:
        description: 合成成功
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            msg:
              type: string
              example: "success"
            resp:
              type: object
              properties:
                audio_url:
                  type: string
                  description: 语音音频下载地址
                audio_base64:
                  type: string
                  description: 语音音频base64（可选）
                record_id:
                  type: integer
                  description: TTS使用记录ID
      400:
        description: 参数错误
      403:
        description: 无权使用该音色
      500:
        description: 合成失败
    """

    # 参数验证
    data = request.get_json()
    if not data:
        return fail("请求数据不能为空", 400)

    text = data.get("text", "").strip()
    speaker_id = data.get("speaker_id", "").strip()
    base_url = data.get("base_url", "").strip()
    token = data.get("token", "").strip()
    model = data.get("model", "speech-1.6").strip()

    if not text or not speaker_id or not base_url or not token:
        return fail("text、speaker_id、base_url和token不能为空", 400)

    # 调用服务层
    return VoiceService.tts_synthesis(
        current_user.id, text, speaker_id, base_url, token, model
    )


@bp.post("/create_speaker")
def create_speaker():
    """创建音色模型
    ---
    tags:
      - voice
    summary: 上传音频文件创建fish-speech音色模型
    description: 上传音频文件训练生成speaker_id，用于后续语音克隆
    consumes:
      - multipart/form-data
    produces:
      - application/json
    parameters:
      - name: audio_file
        in: formData
        type: file
        required: true
        description: 音频文件 (支持wav, mp3等格式)
      - name: speaker_name
        in: formData
        type: string
        required: true
        description: 音色名称
        example: "张三的声音"
      - name: base_url
        in: formData
        type: string
        required: true
        description: fish-speech API基础地址
        example: "https://api.fish.audio"
      - name: token
        in: formData
        type: string
        required: true
        description: fish-speech API认证token
        example: "your_api_token"
      - name: description
        in: formData
        type: string
        required: false
        description: 音色描述
        example: "清晰的男性声音"
      - name: texts
        in: formData
        type: string
        required: false
        description: 训练文本（可选）
        example: "用于训练的示例文本"
    responses:
      200:
        description: 创建成功
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            msg:
              type: string
              example: "success"
            resp:
              type: object
              properties:
                id:
                  type: integer
                  description: 数据库记录ID
                speaker_id:
                  type: string
                  description: 生成的音色ID
                speaker_name:
                  type: string
                  description: 音色名称
                status:
                  type: string
                  description: 创建状态
      400:
        description: 参数错误
      500:
        description: 创建失败
    """

    # 参数验证
    if "audio_file" not in request.files:
        return fail("缺少音频文件", 400)

    audio_file = request.files["audio_file"]
    speaker_name = request.form.get("speaker_name", "").strip()
    base_url = request.form.get("base_url", "").strip()
    token = request.form.get("token", "").strip()
    description = request.form.get("description", "").strip()
    texts = request.form.get("texts", "").strip()

    if not audio_file.filename or not speaker_name or not base_url or not token:
        return fail("音频文件、speaker_name、base_url和token不能为空", 400)

    # 调用服务层
    resp = VoiceService.create_speaker_with_api(
        current_user.id, audio_file, speaker_name, base_url, token, description, texts
    )
    return resp


@bp.get("/speakers")
def speakers():
    """获取用户音色列表
    ---
    tags:
      - voice
    summary: 获取当前用户的音色列表
    description: 返回用户创建的所有音色模型
    produces:
      - application/json
    parameters:
      - name: is_active
        in: query
        type: boolean
        required: false
        description: 是否只显示可用音色
        default: true
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            msg:
              type: string
              example: "success"
            resp:
              type: object
              properties:
                speakers:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: integer
                      speaker_id:
                        type: string
                      speaker_name:
                        type: string
                      status:
                        type: string
                      description:
                        type: string
                      is_active:
                        type: boolean
                      create_time:
                        type: string
      500:
        description: 获取失败
    """
    base_url = request.args.get("base_url", "").strip()
    is_active = request.args.get("is_active", "true").lower() in ("true", "1", "t")
    resp = VoiceService.get_user_speakers(current_user.id, base_url, is_active)
    logger.info(f"获取音色列表响应: {resp}")
    return resp


@bp.get("/records")
def get_tts_records():
    """获取TTS使用记录
    ---
    tags:
      - voice
    summary: 获取用户TTS使用记录
    description: 分页返回用户的TTS使用历史
    produces:
      - application/json
    parameters:
      - name: page
        in: query
        type: integer
        required: false
        description: 页码
        default: 1
      - name: page_size
        in: query
        type: integer
        required: false
        description: 每页数量
        default: 20
      - name: speaker_id
        in: query
        type: string
        required: false
        description: 按音色ID筛选
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            msg:
              type: string
              example: "success"
            resp:
              type: object
              properties:
                records:
                  type: array
                  items:
                    type: object
                    properties:
                      id:
                        type: integer
                      speaker_id:
                        type: string
                      text:
                        type: string
                      text_length:
                        type: integer
                      audio_duration:
                        type: number
                      audio_url:
                        type: string
                      status:
                        type: string
                      error_message:
                        type: string
                      cost_time:
                        type: number
                      create_time:
                        type: string
                total:
                  type: integer
                page:
                  type: integer
                page_size:
                  type: integer
      500:
        description: 获取失败
    """
    user = current_user()
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    speaker_id = request.args.get("speaker_id")

    return VoiceService.get_user_tts_records(user["id"], page, page_size, speaker_id)


@bp.get("/stats")
def get_usage_stats():
    """获取使用统计
    ---
    tags:
      - voice
    summary: 获取用户TTS使用统计
    description: 返回用户在指定天数内的使用统计数据
    produces:
      - application/json
    parameters:
      - name: days
        in: query
        type: integer
        required: false
        description: 统计天数
        default: 30
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            msg:
              type: string
              example: "success"
            resp:
              type: object
              properties:
                days:
                  type: integer
                total_count:
                  type: integer
                  description: 总次数
                success_count:
                  type: integer
                  description: 成功次数
                failed_count:
                  type: integer
                  description: 失败次数
                success_rate:
                  type: number
                  description: 成功率(%)
                total_text_length:
                  type: integer
                  description: 总文本长度
                total_audio_duration:
                  type: number
                  description: 总音频时长(秒)
                avg_cost_time:
                  type: number
                  description: 平均耗时(秒)
      500:
        description: 获取失败
    """
    user = current_user()
    days = int(request.args.get("days", 30))

    return VoiceService.get_user_usage_stats(user["id"], days)


@bp.delete("/delete_speaker")
def delete_speaker():
    """删除音色模型
    ---
    tags:
      - voice
    summary: 删除用户的音色模型
    description: 删除指定的音色模型，可选择同时删除相关使用记录
    produces:
      - application/json
    parameters:
      - name: speaker_id
        in: query
        type: string
        required: true
        description: 要删除的音色ID
        example: "fish-001"
      - name: base_url
        in: query
        type: string
        required: true
        description: fish-speech API基础地址
        example: "https://api.fish.audio"
      - name: token
        in: query
        type: string
        required: true
        description: fish-speech API认证token
        example: "your_api_token"
      - name: force_delete
        in: query
        type: boolean
        required: false
        description: 是否强制删除（包括使用记录）
        default: false
    responses:
      200:
        description: 删除成功
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 200
            msg:
              type: string
              example: "音色删除成功"
            resp:
              type: object
              properties:
                speaker_id:
                  type: string
                  description: 删除的音色ID
                speaker_name:
                  type: string
                  description: 音色名称
                deleted_records:
                  type: integer
                  description: 删除的使用记录数
      400:
        description: 参数错误或有使用记录
      404:
        description: 音色不存在
      500:
        description: 删除失败
    """
    # 参数验证
    speaker_id = request.json.get("speaker_id", "").strip()
    base_url = request.json.get("base_url", "").strip()
    token = request.json.get("token", "").strip()
    force_delete = request.json.get("force_delete")
    if not speaker_id or not base_url or not token:
        return fail("speaker_id、base_url和token不能为空", 400)

    # 调用服务层
    return VoiceService.delete_speaker(
        current_user.id, speaker_id, base_url, token, force_delete
    )
