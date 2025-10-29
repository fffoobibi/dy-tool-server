from flask import Blueprint, request
from utils import current_user
from utils.jwt import verify_auth
from utils.response import success, fail
from utils.response import paginate

from models.channels import Channel
from peewee import IntegrityError


bp = Blueprint("channel", __name__)


@bp.before_request
def verify():
    verify_auth()


def _serialize(ch: Channel) -> dict:
    d = ch.to_dict()
    # 移除不希望暴露的字段
    return {
        "id": d.get("id"),
        "platform": d.get("platform"),
        "room_id": d.get("room_id"),
        "user_id": d.get("user_id"),
        "is_active": d.get("is_active"),
        "name": d.get("name"),
        "description": d.get("description"),
        "proxy_url": d.get("proxy_url"),
        "create_time": d.get("create_time"),
    }


@bp.get("/list")
def list_channels():
    """频道列表查询
    ---
    tags:
      - channel
    summary: 获取频道列表
    description: 根据过滤条件获取当前用户频道列表
    security:
      - Bearer: []
      - SkipAuth: []
    parameters:
      - in: query
        name: platform
        type: integer
        required: false
        description: 平台ID
      - in: query
        name: room_id
        type: string
        required: false
        description: 房间号模糊匹配
      - in: query
        name: is_active
        type: string
        required: false
        description: 激活状态(0/1)
      - in: query
        name: page
        type: integer
        required: false
        description: 页码
      - in: query
        name: page_size
        type: integer
        required: false
        description: 每页数量
    responses:
      200:
        description: 成功
    """
    try:
        js = request.json or {}
    except Exception:
        js = {}
    args = request.args
    def _get(name: str):
        return args.get(name) if args.get(name) is not None else js.get(name)
    q = Channel.select().where(Channel.is_deleted == False)
    platform = _get("platform")
    if platform not in (None, ""):
        try:
            platform = int(platform)
            q = q.where(Channel.platform == platform)
        except Exception:
            return fail("platform 参数非法，应为整数")
    user_id = current_user.id
    q = q.where(Channel.user_id == user_id)
    room_id = _get("room_id")
    if room_id not in (None, ""):
        q = q.where(Channel.room_id.contains(str(room_id)))
    is_active = _get("is_active")
    if is_active not in (None, ""):
        if str(is_active) in {"1", "true", "True"}:
            q = q.where(Channel.is_active == True)
        elif str(is_active) in {"0", "false", "False"}:
            q = q.where(Channel.is_active == False)
        else:
            return fail("is_active 参数非法，需为 0/1 或 true/false")
    q = q.order_by(Channel.id.asc())
    total = q.count()
    return paginate(q, total_count=total)


@bp.post("/create")
def create_channel():
    """创建频道
    ---
    tags:
      - channel
    summary: 创建频道
    description: 创建频道 (platform, room_id 唯一)
    security:
      - Bearer: []
      - SkipAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [platform, room_id, user_id]
          properties:
            platform: { type: integer }
            room_id: { type: string }
            user_id: { type: integer }
            name: { type: string }
            description: { type: string }
            proxy_url: { type: string }
            is_active: { type: boolean }
    responses:
      200:
        description: 成功
      400:
        description: 参数错误
    """
    js = request.json or {}
    platform = js.get("platform")
    room_id = js.get("room_id")
    user_id = current_user.id
    if platform is None or room_id is None or user_id is None:
        return fail("platform, room_id, user_id 为必填")
    try:
        platform = int(platform)
        user_id = int(user_id)
    except Exception:
        return fail("platform/user_id 必须是整数")
    exists = Channel.get_or_none(Channel.platform == platform, Channel.room_id == room_id, Channel.is_deleted == False)
    if exists:
        return fail("频道已存在")
    data = dict(platform=platform, room_id=str(room_id), user_id=user_id, name=js.get("name"), description=js.get("description"), proxy_url=js.get("proxy_url"), is_active=js.get("is_active", True))
    try:
        ch = Channel.create(**data)
    except IntegrityError:
        return fail("唯一约束冲突，创建失败")
    except Exception as e:
        return fail(f"创建失败: {e}")
    return success(resp=_serialize(ch))


@bp.post("/edit")
def update_channel():
    """更新频道
    ---
    tags:
      - channel
    summary: 更新频道
    description: 根据频道ID更新字段
    security:
      - Bearer: []
      - SkipAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            id: { type: integer }
            platform: { type: integer }
            room_id: { type: string }
            name: { type: string }
            description: { type: string }
            proxy_url: { type: string }
            is_active: { type: boolean }
    responses:
      200:
        description: 成功
      404:
        description: 未找到
    """
    channel_id = request.json.get("id")
    ch = Channel.get_or_none(Channel.id == channel_id, Channel.is_deleted == False)
    if not ch:
        return fail("频道不存在")
    js = request.json or {}
    updated = js.copy()
    updated.pop("id", None)
    try:
        Channel.update(**updated).where(Channel.id == channel_id).execute()
    except Exception as e:
        return fail(f"保存失败: {e}")
    return success(resp=_serialize(ch))


@bp.post("/delete")
def delete_channel():
    """删除频道
    ---
    tags:
      - channel
    summary: 软删除频道
    description: 标记 is_deleted=true 并停用
    security:
      - Bearer: []
      - SkipAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            channel_id:
              type: integer
        type: integer
        required: true
        description: 频道ID
    responses:
      200:
        description: 成功
      404:
        description: 未找到
    """
    channel_id = request.json.get("channel_id")
    ch: Channel = Channel.get_or_none(Channel.id == channel_id, Channel.is_deleted == False)
    if not ch:
        return fail("频道不存在")
    # ch.is_deleted = True
    # ch.is_active = False
    try:
        ch.delete_instance()
    except Exception as e:
        return fail(f"删除失败: {e}")
    return success(resp={"id": channel_id})
