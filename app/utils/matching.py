import math
from datetime import date
from sqlalchemy import func, and_, or_, not_
from app import db
from app.models import User, UserTag, Tag, Block, Like


def calculate_age(birth_date):
    if not birth_date:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def haversine_distance(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_user_tag_ids(user_id):
    return set(ut.tag_id for ut in UserTag.query.filter_by(user_id=user_id).all())


def get_matching_query(current_user, filters=None):
    filters = filters or {}
    blocked_by_me = db.session.query(Block.blocked_id).filter(Block.blocker_id == current_user.id)
    blocked_me = db.session.query(Block.blocker_id).filter(Block.blocked_id == current_user.id)
    query = User.query.filter(
        User.id != current_user.id,
        User.email_verified == True,
        User.id.notin_(blocked_by_me),
        User.id.notin_(blocked_me),
    )
    if current_user.gender and current_user.sexual_preference:
        if current_user.sexual_preference == "heterosexual":
            if current_user.gender == "male":
                query = query.filter(User.gender == "female")
            elif current_user.gender == "female":
                query = query.filter(User.gender == "male")
        elif current_user.sexual_preference == "homosexual":
            query = query.filter(User.gender == current_user.gender)
    query = query.filter(
        or_(
            User.sexual_preference == None,
            User.sexual_preference == "bisexual",
            and_(
                User.sexual_preference == "heterosexual",
                User.gender != current_user.gender
            ),
            and_(
                User.sexual_preference == "homosexual",
                User.gender == current_user.gender
            ),
        )
    )
    if filters.get("age_min"):
        max_birth = date.today().replace(year=date.today().year - int(filters["age_min"]))
        query = query.filter(or_(User.birth_date == None, User.birth_date <= max_birth))
    if filters.get("age_max"):
        min_birth = date.today().replace(year=date.today().year - int(filters["age_max"]) - 1)
        query = query.filter(or_(User.birth_date == None, User.birth_date >= min_birth))
    if filters.get("fame_min"):
        query = query.filter(User.fame_rating >= int(filters["fame_min"]))
    if filters.get("fame_max"):
        query = query.filter(User.fame_rating <= int(filters["fame_max"]))
    if filters.get("tags"):
        tag_names = [t.strip().lower() for t in filters["tags"].split(",") if t.strip()]
        if tag_names:
            tag_ids = db.session.query(Tag.id).filter(Tag.name.in_(tag_names)).subquery()
            users_with_tags = db.session.query(UserTag.user_id).filter(UserTag.tag_id.in_(tag_ids)).distinct()
            query = query.filter(User.id.in_(users_with_tags))
    return query


def score_user(user, current_user, my_tag_ids):
    score = 0
    if current_user.latitude and current_user.longitude and user.latitude and user.longitude:
        dist = haversine_distance(current_user.latitude, current_user.longitude, user.latitude, user.longitude)
        if dist is not None:
            if dist < 10:
                score += 1000
            elif dist < 50:
                score += 500
            elif dist < 100:
                score += 200
            else:
                score += max(0, 100 - int(dist / 10))
    user_tag_ids = get_user_tag_ids(user.id)
    common = len(my_tag_ids & user_tag_ids)
    score += common * 50
    score += user.fame_rating
    return score


def get_suggestions(current_user, sort_by=None, filters=None, limit=50):
    query = get_matching_query(current_user, filters)
    users = query.all()
    my_tag_ids = get_user_tag_ids(current_user.id)
    scored = []
    for u in users:
        dist = None
        if current_user.latitude and current_user.longitude and u.latitude and u.longitude:
            dist = haversine_distance(current_user.latitude, current_user.longitude, u.latitude, u.longitude)
        age = calculate_age(u.birth_date)
        common_tags = len(my_tag_ids & get_user_tag_ids(u.id))
        score = score_user(u, current_user, my_tag_ids)
        scored.append({
            "user": u,
            "score": score,
            "distance": dist,
            "age": age,
            "common_tags": common_tags,
        })
    if sort_by == "age":
        scored.sort(key=lambda x: (x["age"] is None, x["age"] or 0))
    elif sort_by == "location":
        scored.sort(key=lambda x: (x["distance"] is None, x["distance"] or 9999))
    elif sort_by == "fame":
        scored.sort(key=lambda x: -x["user"].fame_rating)
    elif sort_by == "tags":
        scored.sort(key=lambda x: -x["common_tags"])
    else:
        scored.sort(key=lambda x: -x["score"])
    if filters and filters.get("location_max"):
        max_dist = float(filters["location_max"])
        scored = [s for s in scored if s["distance"] is not None and s["distance"] <= max_dist]
    return scored[:limit]


def search_users(current_user, filters, sort_by=None, limit=50):
    return get_suggestions(current_user, sort_by=sort_by, filters=filters, limit=limit)
