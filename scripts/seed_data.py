#!/usr/bin/env python3
import os
import sys
import random
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db, bcrypt
from app.models import User, Tag, UserTag, Like, ProfileView

FIRST_NAMES_M = [
    "James", "John", "Robert", "Michael", "David", "William", "Richard", "Joseph",
    "Thomas", "Christopher", "Charles", "Daniel", "Matthew", "Anthony", "Mark",
    "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian",
    "George", "Timothy", "Ronald", "Edward", "Jason", "Jeffrey", "Ryan", "Jacob",
    "Gary", "Nicholas", "Eric", "Jonathan", "Stephen", "Larry", "Justin", "Scott",
    "Brandon", "Benjamin", "Samuel", "Raymond", "Gregory", "Frank", "Alexander",
    "Patrick", "Jack", "Dennis", "Jerry", "Tyler", "Aaron", "Jose", "Adam", "Nathan",
]
FIRST_NAMES_F = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
    "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra",
    "Ashley", "Kimberly", "Emily", "Donna", "Michelle", "Dorothy", "Carol", "Amanda",
    "Melissa", "Deborah", "Stephanie", "Rebecca", "Sharon", "Laura", "Cynthia",
    "Kathleen", "Amy", "Angela", "Shirley", "Anna", "Brenda", "Pamela", "Emma",
    "Nicole", "Helen", "Samantha", "Katherine", "Christine", "Debra", "Rachel",
    "Carolyn", "Janet", "Catherine", "Maria", "Heather", "Diane", "Ruth", "Julie",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Turner", "Phillips", "Evans", "Parker", "Edwards", "Collins",
]
TAGS = [
    "hiking", "photography", "music", "movies", "travel", "cooking", "reading",
    "gaming", "fitness", "yoga", "dancing", "art", "coffee", "wine", "beer",
    "cats", "dogs", "nature", "beach", "mountains", "skiing", "snowboarding",
    "surfing", "climbing", "running", "cycling", "swimming", "camping", "fishing",
    "gardening", "painting", "writing", "poetry", "theater", "concerts", "festivals",
    "foodie", "vegan", "vegetarian", "sushi", "pizza", "tacos", "brunch", "bbq",
    "meditation", "spirituality", "astrology", "science", "technology", "programming",
]
BIOS = [
    "Love exploring new places and meeting new people.",
    "Coffee addict and bookworm.",
    "Looking for someone to share adventures with.",
    "Music lover and concert enthusiast.",
    "Foodie who loves trying new restaurants.",
    "Outdoor enthusiast and nature lover.",
    "Creative soul with a passion for art.",
    "Tech geek by day, gamer by night.",
    "Fitness junkie who enjoys a good workout.",
    "Simple person looking for genuine connections.",
    "Life is short, let's make it sweet.",
    "Always up for a spontaneous road trip.",
    "Dog parent looking for a partner in crime.",
    "Cat lover seeking someone special.",
    "Traveler with a wanderlust heart.",
]
CITIES = [
    (46.5197, 6.6323),
    (46.2044, 6.1432),
    (47.3769, 8.5417),
    (46.9480, 7.4474),
    (47.5596, 7.5886),
    (46.0037, 8.9511),
    (47.0502, 8.3093),
    (46.8499, 9.5329),
    (47.4245, 9.3767),
    (46.2018, 6.1466),
]


def create_tags():
    for tag_name in TAGS:
        existing = Tag.query.filter_by(name=tag_name).first()
        if not existing:
            db.session.add(Tag(name=tag_name))
    db.session.commit()
    return Tag.query.all()


def random_date(start_year=1985, end_year=2003):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return (start + timedelta(days=random_days)).date()


def create_users(count=500):
    all_tags = create_tags()
    password_hash = bcrypt.generate_password_hash("Test1234!").decode("utf-8")
    users = []
    for i in range(count):
        gender = random.choice(["male", "female"])
        if gender == "male":
            first_name = random.choice(FIRST_NAMES_M)
        else:
            first_name = random.choice(FIRST_NAMES_F)
        last_name = random.choice(LAST_NAMES)
        username = f"{first_name.lower()}{last_name.lower()}{random.randint(1, 9999)}"
        email = f"{username}@example.com"
        if User.query.filter_by(username=username).first():
            continue
        if User.query.filter_by(email=email).first():
            continue
        city = random.choice(CITIES)
        lat = city[0] + random.uniform(-0.1, 0.1)
        lon = city[1] + random.uniform(-0.1, 0.1)
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            birth_date=random_date(),
            gender=gender,
            sexual_preference=random.choice(["heterosexual", "homosexual", "bisexual"]),
            biography=random.choice(BIOS),
            latitude=lat,
            longitude=lon,
            location_enabled=True,
            fame_rating=random.randint(0, 100),
            email_verified=True,
            is_online=random.choice([True, False]),
            last_seen=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=random.randint(0, 10080)),
        )
        db.session.add(user)
        users.append(user)
        if len(users) % 100 == 0:
            db.session.commit()
            print(f"Created {len(users)} users...")
    db.session.commit()
    print(f"Total users created: {len(users)}")
    for user in users:
        num_tags = random.randint(2, 6)
        selected_tags = random.sample(all_tags, num_tags)
        for tag in selected_tags:
            existing = UserTag.query.filter_by(user_id=user.id, tag_id=tag.id).first()
            if not existing:
                db.session.add(UserTag(user_id=user.id, tag_id=tag.id))
    db.session.commit()
    print("Tags assigned to users.")
    return users


def create_interactions(users, like_count=2000, view_count=5000):
    user_ids = [u.id for u in users]
    likes_created = 0
    for _ in range(like_count):
        liker_id = random.choice(user_ids)
        liked_id = random.choice(user_ids)
        if liker_id == liked_id:
            continue
        existing = Like.query.filter_by(liker_id=liker_id, liked_id=liked_id).first()
        if existing:
            continue
        db.session.add(Like(liker_id=liker_id, liked_id=liked_id))
        likes_created += 1
        if likes_created % 500 == 0:
            db.session.commit()
    db.session.commit()
    print(f"Created {likes_created} likes.")
    views_created = 0
    for _ in range(view_count):
        viewer_id = random.choice(user_ids)
        viewed_id = random.choice(user_ids)
        if viewer_id == viewed_id:
            continue
        db.session.add(ProfileView(
            viewer_id=viewer_id,
            viewed_id=viewed_id,
            viewed_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=random.randint(0, 43200))
        ))
        views_created += 1
        if views_created % 1000 == 0:
            db.session.commit()
    db.session.commit()
    print(f"Created {views_created} profile views.")


def main():
    app = create_app()
    with app.app_context():
        print("Starting seed data generation...")
        users = create_users(500)
        if users:
            create_interactions(users)
        print("Seed data generation complete!")


if __name__ == "__main__":
    main()
