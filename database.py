"""
Database models and operations for the Treasure Hunter Bot
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

Base = declarative_base()

class User(Base):
    """User model for tracking treasure hunters"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    total_points = Column(Integer, default=0)
    finds_count = Column(Integer, default=0)
    join_date = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    finds = relationship("Find", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")

class Find(Base):
    """Model for tracking individual treasure finds"""
    __tablename__ = 'finds'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    find_type = Column(String(100))  # coin, jewelry, relic, etc.
    description = Column(Text)
    points_awarded = Column(Integer, default=0)
    location = Column(String(255))  # General location (no exact coordinates for privacy)
    depth = Column(Float)  # Depth in inches/cm
    detector_used = Column(String(255))
    image_analysis = Column(Text)  # AI analysis results
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="finds")

class Achievement(Base):
    """Achievement definitions"""
    __tablename__ = 'achievements'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    icon = Column(String(50))  # Emoji or icon identifier
    points_required = Column(Integer)
    finds_required = Column(Integer)
    achievement_type = Column(String(50))  # points, finds, special
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_achievements = relationship("UserAchievement", back_populates="achievement")

class UserAchievement(Base):
    """User achievements junction table"""
    __tablename__ = 'user_achievements'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    achievement_id = Column(Integer, ForeignKey('achievements.id'), nullable=False)
    earned_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")

class LeaderboardEntry(Base):
    """Weekly/Monthly leaderboard snapshots"""
    __tablename__ = 'leaderboard_entries'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    period_type = Column(String(20))  # weekly, monthly, all_time
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    points = Column(Integer, default=0)
    finds_count = Column(Integer, default=0)
    rank = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabaseManager:
    """Database manager for treasure hunter operations"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("Database URL is required")
        
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        self.create_tables()
        self.init_achievements()
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def init_achievements(self):
        """Initialize default achievements"""
        session = self.get_session()
        try:
            # Check if achievements already exist
            if session.query(Achievement).count() > 0:
                return
            
            default_achievements = [
                {
                    'name': 'First Find',
                    'description': 'Record your very first treasure find!',
                    'icon': '🎯',
                    'finds_required': 1,
                    'points_required': 0,
                    'achievement_type': 'finds'
                },
                {
                    'name': 'Rookie Hunter',
                    'description': 'Find 5 treasures',
                    'icon': '🔍',
                    'finds_required': 5,
                    'points_required': 0,
                    'achievement_type': 'finds'
                },
                {
                    'name': 'Experienced Hunter',
                    'description': 'Find 25 treasures',
                    'icon': '⛏️',
                    'finds_required': 25,
                    'points_required': 0,
                    'achievement_type': 'finds'
                },
                {
                    'name': 'Master Hunter',
                    'description': 'Find 100 treasures',
                    'icon': '🏆',
                    'finds_required': 100,
                    'points_required': 0,
                    'achievement_type': 'finds'
                },
                {
                    'name': 'Point Collector',
                    'description': 'Earn 100 points',
                    'icon': '💯',
                    'finds_required': 0,
                    'points_required': 100,
                    'achievement_type': 'points'
                },
                {
                    'name': 'High Scorer',
                    'description': 'Earn 500 points',
                    'icon': '⭐',
                    'finds_required': 0,
                    'points_required': 500,
                    'achievement_type': 'points'
                },
                {
                    'name': 'Legend',
                    'description': 'Earn 1000 points',
                    'icon': '👑',
                    'finds_required': 0,
                    'points_required': 1000,
                    'achievement_type': 'points'
                },
                {
                    'name': 'Coin Specialist',
                    'description': 'Find 10 coins',
                    'icon': '🪙',
                    'finds_required': 10,
                    'points_required': 0,
                    'achievement_type': 'special'
                },
                {
                    'name': 'Jewelry Expert',
                    'description': 'Find 5 pieces of jewelry',
                    'icon': '💍',
                    'finds_required': 5,
                    'points_required': 0,
                    'achievement_type': 'special'
                },
                {
                    'name': 'History Buff',
                    'description': 'Find 5 historical relics',
                    'icon': '🏺',
                    'finds_required': 5,
                    'points_required': 0,
                    'achievement_type': 'special'
                }
            ]
            
            for ach_data in default_achievements:
                achievement = Achievement(**ach_data)
                session.add(achievement)
            
            session.commit()
            logger.info("Default achievements initialized")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error initializing achievements: {e}")
        finally:
            session.close()
    
    def get_or_create_user(self, telegram_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> User:
        """Get existing user or create new one"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
                session.commit()
                logger.info(f"Created new user: {telegram_id}")
            else:
                # Update user info if changed
                user.username = username or user.username
                user.first_name = first_name or user.first_name
                user.last_name = last_name or user.last_name
                user.last_activity = datetime.utcnow()
                session.commit()
            
            return user
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error getting/creating user: {e}")
            raise
        finally:
            session.close()
    
    def add_find(self, user_id: int, find_type: str, description: str, 
                 location: str = None, depth: float = None, 
                 detector_used: str = None, image_analysis: str = None) -> Find:
        """Add a new find and calculate points"""
        session = self.get_session()
        try:
            # Calculate points based on find type
            points = self._calculate_points(find_type, depth)
            
            find = Find(
                user_id=user_id,
                find_type=find_type,
                description=description,
                points_awarded=points,
                location=location,
                depth=depth,
                detector_used=detector_used,
                image_analysis=image_analysis
            )
            
            session.add(find)
            
            # Update user stats
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.total_points += points
                user.finds_count += 1
                user.last_activity = datetime.utcnow()
            
            session.commit()
            
            # Check for new achievements
            self._check_achievements(user_id, session)
            
            logger.info(f"Added find for user {user_id}: {find_type} ({points} points)")
            return find
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding find: {e}")
            raise
        finally:
            session.close()
    
    def _calculate_points(self, find_type: str, depth: float = None) -> int:
        """Calculate points for a find based on type and depth"""
        base_points = {
            'coin': 10,
            'jewelry': 25,
            'relic': 20,
            'artifact': 30,
            'button': 15,
            'buckle': 15,
            'token': 20,
            'other': 5
        }
        
        points = base_points.get(find_type.lower(), 5)
        
        # Bonus points for depth
        if depth:
            if depth > 12:  # Deep finds get bonus
                points += 10
            elif depth > 8:
                points += 5
        
        return points
    
    def _check_achievements(self, user_id: int, session: Session):
        """Check and award new achievements"""
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return
            
            # Get user's current achievements
            current_achievements = session.query(UserAchievement.achievement_id).filter(
                UserAchievement.user_id == user_id
            ).all()
            current_achievement_ids = [ach[0] for ach in current_achievements]
            
            # Check all achievements
            achievements = session.query(Achievement).filter(Achievement.is_active == True).all()
            
            for achievement in achievements:
                if achievement.id in current_achievement_ids:
                    continue
                
                earned = False
                
                if achievement.achievement_type == 'finds':
                    if user.finds_count >= achievement.finds_required:
                        earned = True
                elif achievement.achievement_type == 'points':
                    if user.total_points >= achievement.points_required:
                        earned = True
                elif achievement.achievement_type == 'special':
                    # Special achievements need custom logic
                    earned = self._check_special_achievement(user_id, achievement, session)
                
                if earned:
                    user_achievement = UserAchievement(
                        user_id=user_id,
                        achievement_id=achievement.id
                    )
                    session.add(user_achievement)
                    logger.info(f"User {user_id} earned achievement: {achievement.name}")
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error checking achievements: {e}")
    
    def _check_special_achievement(self, user_id: int, achievement: Achievement, session: Session) -> bool:
        """Check special achievements based on find types"""
        try:
            if achievement.name == 'Coin Specialist':
                coin_count = session.query(Find).filter(
                    Find.user_id == user_id,
                    Find.find_type.ilike('%coin%')
                ).count()
                return coin_count >= 10
            
            elif achievement.name == 'Jewelry Expert':
                jewelry_count = session.query(Find).filter(
                    Find.user_id == user_id,
                    Find.find_type.ilike('%jewelry%')
                ).count()
                return jewelry_count >= 5
            
            elif achievement.name == 'History Buff':
                relic_count = session.query(Find).filter(
                    Find.user_id == user_id,
                    Find.find_type.in_(['relic', 'artifact', 'button', 'buckle'])
                ).count()
                return relic_count >= 5
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking special achievement: {e}")
            return False
    
    def get_leaderboard(self, period: str = 'all_time', limit: int = 10) -> List[Dict[str, Any]]:
        """Get leaderboard for specified period"""
        session = self.get_session()
        try:
            if period == 'weekly':
                start_date = datetime.utcnow() - timedelta(days=7)
                query = session.query(
                    User.telegram_id,
                    User.username,
                    User.first_name,
                    func.sum(Find.points_awarded).label('points'),
                    func.count(Find.id).label('finds')
                ).join(Find).filter(
                    Find.created_at >= start_date
                ).group_by(User.id, User.telegram_id, User.username, User.first_name)
            
            elif period == 'monthly':
                start_date = datetime.utcnow() - timedelta(days=30)
                query = session.query(
                    User.telegram_id,
                    User.username,
                    User.first_name,
                    func.sum(Find.points_awarded).label('points'),
                    func.count(Find.id).label('finds')
                ).join(Find).filter(
                    Find.created_at >= start_date
                ).group_by(User.id, User.telegram_id, User.username, User.first_name)
            
            else:  # all_time
                query = session.query(
                    User.telegram_id,
                    User.username,
                    User.first_name,
                    User.total_points.label('points'),
                    User.finds_count.label('finds')
                ).filter(User.total_points > 0)
            
            results = query.order_by(func.coalesce('points', 0).desc()).limit(limit).all()
            
            leaderboard = []
            for i, result in enumerate(results, 1):
                leaderboard.append({
                    'rank': i,
                    'telegram_id': result.telegram_id,
                    'username': result.username,
                    'first_name': result.first_name,
                    'points': result.points or 0,
                    'finds': result.finds or 0
                })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
        finally:
            session.close()
    
    def get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return {}
            
            # Get recent finds
            recent_finds = session.query(Find).filter(
                Find.user_id == user.id
            ).order_by(Find.created_at.desc()).limit(5).all()
            
            # Get achievements
            user_achievements = session.query(Achievement).join(UserAchievement).filter(
                UserAchievement.user_id == user.id
            ).all()
            
            # Get user rank
            rank_query = session.query(User).filter(
                User.total_points > user.total_points
            ).count()
            user_rank = rank_query + 1
            
            return {
                'user': user,
                'rank': user_rank,
                'recent_finds': recent_finds,
                'achievements': user_achievements,
                'total_users': session.query(User).filter(User.total_points > 0).count()
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
        finally:
            session.close()
    
    def get_recent_community_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent community finds and achievements"""
        session = self.get_session()
        try:
            # Recent finds
            recent_finds = session.query(Find, User).join(User).filter(
                Find.points_awarded > 0
            ).order_by(Find.created_at.desc()).limit(limit).all()
            
            activity = []
            for find, user in recent_finds:
                activity.append({
                    'type': 'find',
                    'username': user.username or user.first_name,
                    'find_type': find.find_type,
                    'points': find.points_awarded,
                    'created_at': find.created_at
                })
            
            return activity
            
        except Exception as e:
            logger.error(f"Error getting community activity: {e}")
            return []
        finally:
            session.close()