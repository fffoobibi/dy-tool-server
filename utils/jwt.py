import json
from flask import Flask, request
from flask_jwt_extended import JWTManager, verify_jwt_in_request, create_access_token

from loguru import logger
from utils.response import fail, success
from constants import ResponseCode
from settings import SKIP_AUTH_TOKEN
from models.account import User
from collections import namedtuple

CurrentUserHint = namedtuple(
    "CurrentUserHint", ["id",  "username", "email", "phone"]
)


def verify_auth():
    if skip_token := request.headers.get("skip-auth-token"):
        if skip_token == SKIP_AUTH_TOKEN:
            return
    verify_jwt_in_request()


def init_jwt(app: Flask):
    jwt = JWTManager()
    jwt.init_app(app)

    # 处理无效的 Token
    @jwt.invalid_token_loader
    def custom_invalid_token_callback(error):
        return (
            fail("Invalid Token. Please log in again.", ResponseCode.AUTH_FAILED),
            422,
        )

    # 处理未提供 Token 的情况
    @jwt.unauthorized_loader
    def custom_unauthorized_response(callback):
        return fail("Missing Authorization Header", ResponseCode.AUTH_FAILED), 401

    # 处理过期的 Token
    @jwt.expired_token_loader
    def custom_expired_token_callback(callback):
        return (
            fail("Token has expired. Please log in again.", ResponseCode.AUTH_FAILED),
            401,
        )

    @jwt.user_lookup_loader
    def user_lookup_callback(jwt_header, jwt_payload):
        data = jwt_payload.get("sub")  # 或根据你的实际数据结构获取用户 ID
        user_data = json.loads(data)
        user = CurrentUserHint(**user_data)
        return user

    @app.post("/auth/login")
    def login():
        """用户登录
        ---
        tags:
            - auth
        summary: 用户登录获取JWT
        description: 通过用户名密码登录
        parameters:
            - in: body
              name: body
              required: true
              schema:
                type: object
                required:
                    - user
                    - passwd
                properties:
                  user:
                    type: string
                    description: 用户名
                  passwd:
                    type: string
                    description: 密码
        responses:
            200:
                description: 登录成功
            400:
                description: 参数错误
            401:
                description: 认证失败
        """
        user = request.json.get("user")
        passwd = request.json.get("passwd")
        user: User = User.get_or_none(User.username == user)
        if user is None:
            return fail("没有该账号")
        if user.locked:
            return fail("请联系管理员解锁账号")
        if not user.verify_password(passwd):
            return fail("密码不对")
        tokens = json.dumps(
            {
                "username": user.username,
                "id": user.id,
                "email": user.email,
                "phone": user.phone,
            },
            ensure_ascii=False,
        )
        access_token = create_access_token(identity=tokens)
        return success(
            resp={
                "access_token": access_token,
                "username": user.username,
                "id": user.id,
                "email": user.email,
                "phone": user.phone,
            }
        )

    @app.post("/auth/create")
    def create_user():
        """创建用户
        ---
        tags:
            - auth
        summary: 注册新用户
        description: 注册新用户，用户名唯一
        parameters:
            - in: body
              name: body
              required: true
              schema:
                type: object
                required:
                    - username
                    - password
                properties:
                    username:
                        type: string
                    password:
                        type: string
                    email:
                        type: string
                    phone:
                        type: string
        responses:
            200:
                description: 创建成功
            400:
                description: 参数错误或已存在
        """
        verify_auth()
        js = request.json or {}
        username = js.get("username")
        password = js.get("password")
        email = js.get("email")
        phone = js.get("phone")
        if not username or not password:
            return fail("username/password 必填")
        # 长度与简单校验
        if len(username) < 3:
            return fail("用户名长度至少3")
        if len(password) < 6:
            return fail("密码长度至少6")
        exists = User.get_or_none(User.username == username, User.is_deleted == False)
        if exists:
            return fail("用户名已存在")
        try:
            user = User.create_user(username=username, password=password)
            if email:
                user.email = email
            if phone:
                user.phone = phone
            user.save()
        except Exception as e:
            return fail(f"创建失败: {e}")
        return success()

    @app.post("/auth/edit/<int:user_id>")
    def edit_user(user_id: int):
        """编辑用户
        ---
        tags:
          - auth
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
        return success()
