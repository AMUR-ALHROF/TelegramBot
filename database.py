from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    func,
    case,
    literal_column,
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from enum import Enum
import logging
from datetime import datetime

Base = declarative_base()

# إعداد التسجيل (اللوق)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enums للأنواع
class FindType(str, Enum):
    COIN = "coin"
    JEWELRY = "jewelry"
    RELIC = "relic"
    ARTIFACT = "artifact"
    BUTTON = "button"
    BUCKLE = "buckle"
    TOKEN = "token"
    OTHER = "other"

class PeriodType(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"

# جداول قاعدة البيانات
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String)
    requests_count = Column(Integer, default=0)
    last_request_date = Column(DateTime)

class Find(Base):
    __tablename__ = "finds"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String)
    photo_path = Column(String)
    value = Column(Float)
    description = Column(String)
    date_found = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="finds")

class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(String)
    points = Column(Integer)

class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    achievement_id = Column(Integer, ForeignKey("achievements.id"))
    date_earned = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="user_achievements")
    achievement = relationship("Achievement")

# مدير قاعدة البيانات
class DatabaseManager:
    def __init__(self, db_url="sqlite:///treasure_bot.db"):
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.init_achievements()

    def get_session(self):
        return self.Session()

    def add_user(self, telegram_id: int, username: str):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(telegram_id=telegram_id, username=username)
                session.add(user)
                session.commit()
                logger.info(f"User {telegram_id} added.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding user {telegram_id}: {e}")
            raise
        finally:
            session.close()

    def increment_user_requests(self, telegram_id: int):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                user.requests_count += 1
                user.last_request_date = func.now()
                session.commit()
                logger.info(f"Incremented requests for user {telegram_id}. New count: {user.requests_count}")
            else:
                logger.warning(f"User {telegram_id} not found for request increment.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error incrementing requests: {e}")
            raise
        finally:
            session.close()

    def add_find(self, telegram_id: int, find_type: FindType, photo_path: str, value: float, description: str):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                raise ValueError("User not found")
            new_find = Find(
                user_id=user.id,
                type=find_type.value,
                photo_path=photo_path,
                value=value,
                description=description,
            )
            session.add(new_find)
            session.commit()
            logger.info(f"Added new find for user {telegram_id}. Type: {find_type}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding find: {e}")
            raise
        finally:
            session.close()

    def get_top_finds(self, limit=10):
        session = self.get_session()
        try:
            finds = session.query(Find).order_by(Find.value.desc()).limit(limit).all()
            return finds
        finally:
            session.close()

    def init_achievements(self):
        session = self.get_session()
        try:
            default_achievements = [
                {"name": "First Find", "description": "Congratulations on your first find!", "points": 10},
                {"name": "Treasure Hunter", "description": "Submitted 10 finds.", "points": 50},
                {"name": "High Roller", "description": "Submitted a find worth over 1000!", "points": 100},
            ]
            existing_names = {ach.name for ach in session.query(Achievement).all()}
            for ach in default_achievements:
                if ach["name"] not in existing_names:
                    session.add(Achievement(**ach))
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error initializing achievements: {e}")
            raise
        finally:
            session.close()

    def award_achievement(self, telegram_id: int, achievement_name: str):
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            achievement = session.query(Achievement).filter_by(name=achievement_name).first()
            if not user or not achievement:
                logger.warning(f"User or Achievement not found. ID: {telegram_id}, Achievement: {achievement_name}")
                return
            existing = session.query(UserAchievement).filter_by(
                user_id=user.id, achievement_id=achievement.id
            ).first()
            if not existing:
                user_ach = UserAchievement(user_id=user.id, achievement_id=achievement.id)
                session.add(user_ach)
                session.commit()
                logger.info(f"Awarded achievement '{achievement_name}' to user {telegram_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error awarding achievement: {e}")
            raise
        finally:
            session.close()

    def get_leaderboard(self, limit=10):
        session = self.get_session()
        try:
            query = session.query(
                User.telegram_id,
                User.username,
                func.coalesce(func.sum(Achievement.points), 0).label("points")
            ).outerjoin(UserAchievement).outerjoin(Achievement).group_by(User.id)
            results = query.order_by(literal_column("points").desc()).limit(limit).all()
            return results
        finally:
            session.close()