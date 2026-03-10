from types import SimpleNamespace
from flask_login import UserMixin
from app import login_manager


class User(UserMixin):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        if "profile_picture" not in kwargs:
            self.profile_picture = None

    def get_id(self):
        return str(self.id)


def make_user(row):
    if not row:
        return None
    data = dict(row)
    pp_filename = data.pop("pp_filename", None)
    pp_id = data.pop("pp_id", None)
    user = User(**data)
    if pp_filename:
        user.profile_picture = SimpleNamespace(id=pp_id, filename=pp_filename)
    elif data.get("profile_picture_id"):
        from app.database import query_one as _q
        pp = _q("SELECT id, filename FROM user_images WHERE id = %s", (data["profile_picture_id"],))
        if pp:
            user.profile_picture = SimpleNamespace(**pp)
    return user


@login_manager.user_loader
def load_user(user_id):
    from app.database import query_one
    row = query_one(
        "SELECT u.*, ui.filename AS pp_filename, ui.id AS pp_id "
        "FROM users u LEFT JOIN user_images ui ON u.profile_picture_id = ui.id "
        "WHERE u.id = %s",
        (int(user_id),),
    )
    return make_user(row)
