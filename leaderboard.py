"""
Leaderboard functionality for the Treasure Hunter Bot
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from database import DatabaseManager, User, Find
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

class LeaderboardManager:
    """Manages leaderboard operations and formatting"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def format_leaderboard(self, period: str = 'all_time', limit: int = 10) -> str:
        """Format leaderboard for display"""
        try:
            leaderboard = self.db.get_leaderboard(period, limit)
            
            if not leaderboard:
                return f"📊 **{period.replace('_', ' ').title()} Leaderboard**\n\nNo treasure hunters found yet. Be the first to record a find!"
            
            period_name = {
                'weekly': 'Weekly',
                'monthly': 'Monthly', 
                'all_time': 'All-Time'
            }.get(period, 'All-Time')
            
            message = f"🏆 **{period_name} Leaderboard**\n\n"
            
            for entry in leaderboard:
                rank = entry['rank']
                name = entry['username'] or entry['first_name'] or 'Anonymous Hunter'
                points = entry['points']
                finds = entry['finds']
                
                # Add rank emoji
                rank_emoji = self._get_rank_emoji(rank)
                
                message += f"{rank_emoji} **{rank}.** {name}\n"
                message += f"   💎 {points} points • 🎯 {finds} finds\n\n"
            
            # Add period info
            if period == 'weekly':
                message += "\n📅 *Last 7 days*"
            elif period == 'monthly':
                message += "\n📅 *Last 30 days*"
            else:
                message += "\n📅 *All time records*"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting leaderboard: {e}")
            return "❌ Unable to load leaderboard. Please try again later."
    
    def _get_rank_emoji(self, rank: int) -> str:
        """Get emoji for rank position"""
        if rank == 1:
            return "👑"
        elif rank == 2:
            return "🥈"
        elif rank == 3:
            return "🥉"
        elif rank <= 5:
            return "⭐"
        elif rank <= 10:
            return "🔸"
        else:
            return "▫️"
    
    def get_leaderboard_keyboard(self) -> InlineKeyboardMarkup:
        """Get inline keyboard for leaderboard navigation"""
        keyboard = [
            [
                InlineKeyboardButton("🏆 All Time", callback_data="leaderboard_all_time"),
                InlineKeyboardButton("📅 Monthly", callback_data="leaderboard_monthly")
            ],
            [
                InlineKeyboardButton("📊 Weekly", callback_data="leaderboard_weekly"),
                InlineKeyboardButton("📈 My Stats", callback_data="leaderboard_mystats")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def format_user_stats(self, telegram_id: int) -> str:
        """Format user statistics for display"""
        try:
            stats = self.db.get_user_stats(telegram_id)
            
            if not stats or not stats.get('user'):
                return "🔍 No treasure hunting activity found. Start by recording your first find!"
            
            user = stats['user']
            rank = stats.get('rank', 'Unknown')
            total_users = stats.get('total_users', 0)
            recent_finds = stats.get('recent_finds', [])
            achievements = stats.get('achievements', [])
            
            name = user.username or user.first_name or 'Anonymous Hunter'
            
            message = f"📊 **{name}'s Treasure Stats**\n\n"
            message += f"🏆 **Rank:** #{rank} of {total_users}\n"
            message += f"💎 **Total Points:** {user.total_points}\n"
            message += f"🎯 **Total Finds:** {user.finds_count}\n"
            message += f"📅 **Member Since:** {user.join_date.strftime('%B %Y')}\n\n"
            
            # Achievements section
            if achievements:
                message += "🏅 **Achievements:**\n"
                for achievement in achievements[:5]:  # Show top 5
                    message += f"{achievement.icon} {achievement.name}\n"
                if len(achievements) > 5:
                    message += f"... and {len(achievements) - 5} more!\n"
                message += "\n"
            
            # Recent finds
            if recent_finds:
                message += "🔍 **Recent Finds:**\n"
                for find in recent_finds[:3]:  # Show last 3
                    days_ago = (datetime.utcnow() - find.created_at).days
                    time_str = f"{days_ago}d ago" if days_ago > 0 else "Today"
                    message += f"• {find.find_type.title()} (+{find.points_awarded} pts) - {time_str}\n"
                message += "\n"
            
            # Calculate average points per find
            if user.finds_count > 0:
                avg_points = user.total_points / user.finds_count
                message += f"📈 **Average:** {avg_points:.1f} points per find\n"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting user stats: {e}")
            return "❌ Unable to load your statistics. Please try again later."
    
    def record_find_from_analysis(self, telegram_id: int, username: str, first_name: str, 
                                find_type: str, description: str, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Record a find based on AI analysis results"""
        try:
            # Get or create user
            user = self.db.get_or_create_user(telegram_id, username, first_name)
            
            # Extract information from analysis if available
            location = None
            depth = None
            
            # Try to extract depth from analysis or description
            if 'depth' in description.lower():
                import re
                depth_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:inch|cm|")', description.lower())
                if depth_match:
                    depth = float(depth_match.group(1))
            
            # Determine find type from analysis if not provided
            if not find_type or find_type.lower() == 'unknown':
                find_type = self._extract_find_type_from_analysis(analysis_result.get('analysis', ''))
            
            # Record the find
            find = self.db.add_find(
                user_id=user.id,
                find_type=find_type,
                description=description,
                location=location,
                depth=depth,
                image_analysis=analysis_result.get('analysis', '')
            )
            
            # Check for new achievements
            new_achievements = self._check_new_achievements(user.id)
            
            return {
                'success': True,
                'find': find,
                'points_awarded': find.points_awarded,
                'new_achievements': new_achievements,
                'total_points': user.total_points,
                'total_finds': user.finds_count
            }
            
        except Exception as e:
            logger.error(f"Error recording find: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_find_type_from_analysis(self, analysis: str) -> str:
        """Extract likely find type from AI analysis"""
        analysis_lower = analysis.lower()
        
        # Define keywords for different find types
        find_types = {
            'coin': ['coin', 'penny', 'nickel', 'dime', 'quarter', 'cent', 'currency'],
            'jewelry': ['ring', 'necklace', 'bracelet', 'earring', 'jewelry', 'gold', 'silver'],
            'relic': ['relic', 'artifact', 'historical', 'antique', 'old'],
            'button': ['button', 'fastener'],
            'buckle': ['buckle', 'belt'],
            'token': ['token', 'medallion', 'badge']
        }
        
        # Score each type based on keyword matches
        scores = {}
        for find_type, keywords in find_types.items():
            score = sum(1 for keyword in keywords if keyword in analysis_lower)
            if score > 0:
                scores[find_type] = score
        
        # Return the highest scoring type, or 'other' if none found
        if scores:
            return max(scores, key=scores.get)
        return 'other'
    
    def _check_new_achievements(self, user_id: int) -> List[Dict[str, Any]]:
        """Check for newly earned achievements"""
        try:
            # This would be called after the find is added
            # For now, return empty list as achievements are checked in database.py
            return []
        except Exception as e:
            logger.error(f"Error checking new achievements: {e}")
            return []
    
    def format_community_activity(self, limit: int = 10) -> str:
        """Format recent community activity"""
        try:
            activity = self.db.get_recent_community_activity(limit)
            
            if not activity:
                return "🌟 **Community Activity**\n\nNo recent activity. Be the first to share a find!"
            
            message = "🌟 **Recent Community Activity**\n\n"
            
            for item in activity:
                if item['type'] == 'find':
                    name = item['username'] or 'Anonymous Hunter'
                    find_type = item['find_type'].title()
                    points = item['points']
                    time_ago = self._format_time_ago(item['created_at'])
                    
                    message += f"🎯 **{name}** found a {find_type}\n"
                    message += f"   💎 +{points} points • {time_ago}\n\n"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting community activity: {e}")
            return "❌ Unable to load community activity."
    
    def _format_time_ago(self, timestamp: datetime) -> str:
        """Format time difference as human readable string"""
        try:
            now = datetime.utcnow()
            diff = now - timestamp
            
            if diff.days > 0:
                return f"{diff.days}d ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours}h ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
            else:
                return "Just now"
                
        except Exception as e:
            logger.error(f"Error formatting time: {e}")
            return "Unknown"
    
    def get_find_recording_keyboard(self) -> InlineKeyboardMarkup:
        """Get keyboard for find recording options"""
        keyboard = [
            [
                InlineKeyboardButton("🪙 Coin", callback_data="record_coin"),
                InlineKeyboardButton("💍 Jewelry", callback_data="record_jewelry")
            ],
            [
                InlineKeyboardButton("🏺 Relic", callback_data="record_relic"),
                InlineKeyboardButton("🔘 Button", callback_data="record_button")
            ],
            [
                InlineKeyboardButton("🔗 Buckle", callback_data="record_buckle"),
                InlineKeyboardButton("🎖️ Token", callback_data="record_token")
            ],
            [
                InlineKeyboardButton("❓ Other", callback_data="record_other")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def format_find_confirmation(self, result: Dict[str, Any]) -> str:
        """Format find recording confirmation message"""
        try:
            if not result.get('success'):
                return f"❌ Failed to record find: {result.get('error', 'Unknown error')}"
            
            find = result['find']
            points = result['points_awarded']
            total_points = result['total_points']
            total_finds = result['total_finds']
            new_achievements = result.get('new_achievements', [])
            
            message = f"✅ **Find Recorded Successfully!**\n\n"
            message += f"🎯 **Type:** {find.find_type.title()}\n"
            message += f"💎 **Points Earned:** +{points}\n"
            message += f"📊 **Total Points:** {total_points}\n"
            message += f"🔍 **Total Finds:** {total_finds}\n"
            
            if new_achievements:
                message += f"\n🏅 **New Achievements:**\n"
                for achievement in new_achievements:
                    message += f"{achievement.get('icon', '🏆')} {achievement.get('name', 'Achievement')}\n"
            
            message += f"\nKeep hunting for more treasures!"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting find confirmation: {e}")
            return "✅ Find recorded successfully!"