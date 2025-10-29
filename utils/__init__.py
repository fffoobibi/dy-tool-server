import typing_extensions as t
from utils.jwt import verify_auth, init_jwt
# from utils.response import success, fail, paginate
from utils.cache import cache
from utils.redis import get_redis
from utils.upload import init_upload, get_upload_file_path
from utils.routes import init_blueprints
from utils.database import init_database, context_db, db

from flask_jwt_extended import current_user, jwt_required

if t.TYPE_CHECKING:

    class CurrentUserHint:
        id: int
        access_token: str
        username: str
        email: str | None
        phone: str | None
        # roles: t.List[str]
        # fp: str

    current_user: CurrentUserHint

__all__ = (
    "verify_auth",
    "current_user",
    "jwt_required",
    "init_jwt",
    # "success",
    # "fail",
    # "paginate",
    "init_cache",
    "get_redis",
    "init_upload",
    "get_upload_file_path",
    "init_blueprints",
    "init_database",
    "context_db",
    "db",
)
