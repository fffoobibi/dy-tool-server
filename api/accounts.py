from flask import Blueprint, request
from utils.jwt import verify_auth
from utils.response import success, fail
from models.account import User
from peewee import IntegrityError
from flask_jwt_extended import create_access_token

bp = Blueprint("accounts", __name__)


@bp.before_request
def verify():
    verify_auth()


def _serialize(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "locked": user.locked,
        "create_time": user.create_time,
    }



@bp.post("/edit/<int:user_id>")
def edit_user(user_id: int):
    """编辑用户
    ---
    tags:
      - accounts
    summary: 编辑用户信息
    description: 可更新邮箱/手机号/密码，密码重新哈希
    parameters:
      - in: path
        name: user_id
        required: true
        type: integer
        description: 用户ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            email:
              type: string
            phone:
              type: string
            password:
              type: string
            locked:
              type: boolean
    responses:
      200:
        description: 更新成功
      404:
        description: 用户不存在
    """
    user: User = User.get_or_none(User.id == user_id, User.is_deleted == False)
    if not user:
        return fail("用户不存在")
    js = request.json or {}
    email = js.get("email")
    phone = js.get("phone")
    password = js.get("password")
    locked = js.get("locked")
    if email is not None:
        user.email = email
    if phone is not None:
        user.phone = phone
    if locked is not None:
        user.locked = bool(locked)
    if password:
        if len(password) < 6:
            return fail("密码长度至少6")
        from passlib.hash import pbkdf2_sha256

        user.passwd = pbkdf2_sha256.hash(password)
    try:
        user.save()
    except Exception as e:
        return fail(f"更新失败: {e}")
    return success(resp=_serialize(user))
