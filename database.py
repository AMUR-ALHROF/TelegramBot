from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    balance = Column(Integer, default=0)
    last_daily = Column(DateTime, default=None)
    invite_code = Column(String, unique=True)
    inviter_id = Column(Integer, default=None)
    invited_friends = Column(Integer, default=0)
    username = Column(String)  # ✅ تمت الإضافة
    first_name = Column(String)  # ✅ تمت الإضافة

class Achievement(Base):
    __tablename__ = 'achievements'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    name = Column(String)
    achieved_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    def __init__(self, db_url="sqlite:///treasure_bot.db"):
        if db_url.startswith("sqlite"):
            self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        else:
            self.engine = create_engine(db_url)

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.init_achievements()

    def init_achievements(self):
        self.achievement_list = [
            {"name": "أول تجميع", "condition": lambda user: user.balance >= 100},
            {"name": "محترف التجميع", "condition": lambda user: user.balance >= 1000},
            {"name": "دعوة أول صديق", "condition": lambda user: user.invited_friends >= 1},
            {"name": "دعوة 5 أصدقاء", "condition": lambda user: user.invited_friends >= 5},
        ]

    def get_or_create_user(self, user_id, username=None, first_name=None):
        session = self.Session()
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name
            )
            session.add(user)
            session.commit()
        session.close()
        return user

    def get_user(self, user_id):
        session = self.Session()
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            user = User(user_id=user_id)
            session.add(user)
            session.commit()
        session.close()
        return user

    def update_balance(self, user_id, amount):
        session = self.Session()
        user = session.query(User).filter_by(user_id=user_id).first()
        if user:
            user.balance += amount
            session.commit()
        session.close()

    def set_last_daily(self, user_id):
        session = self.Session()
        user = session.query(User).filter_by(user_id=user_id).first()
        if user:
            user.last_daily = datetime.utcnow()
            session.commit()
        session.close()

    def check_achievements(self, user_id):
        session = self.Session()
        user = session.query(User).filter_by(user_id=user_id).first()
        earned = []
        if user:
            for ach in self.achievement_list:
                exists = session.query(Achievement).filter_by(user_id=user_id, name=ach["name"]).first()
                if not exists and ach["condition"](user):
                    achievement = Achievement(user_id=user_id, name=ach["name"])
                    session.add(achievement)
                    earned.append(ach["name"])
            session.commit()
        session.close()
        return earned

    def get_user_achievements(self, user_id):
        session = self.Session()
        achievements = session.query(Achievement).filter_by(user_id=user_id).all()
        session.close()
        return achievements

    def set_invite_code(self, user_id, code):
        session = self.Session()
        user = session.query(User).filter_by(user_id=user_id).first()
        if user:
            user.invite_code = code
            session.commit()
        session.close()

    def use_invite_code(self, user_id, code):
        session = self.Session()
        inviter = session.query(User).filter_by(invite_code=code).first()
        user = session.query(User).filter_by(user_id=user_id).first()
        success = False
        if inviter and user and user.inviter_id is None and inviter.user_id != user_id:
            user.inviter_id = inviter.user_id
            inviter.invited_friends += 1
            session.commit()
            success = True
        session.close()
        return success