"""
Gamification Service
Handles badge checking, awarding, and progress tracking
"""

from django.utils import timezone
from datetime import date, timedelta
from .models import (
    Badge, UserBadge, UserProgress, HealthChallenge, ChallengeParticipation,
    ActivityFeed
)
from django.db.models import Q, Count


class GamificationService:
    """Service class for gamification features"""
    
    @staticmethod
    def get_or_create_progress(user):
        """Get or create user progress"""
        progress, created = UserProgress.objects.get_or_create(user=user)
        return progress
    
    @staticmethod
    def check_and_award_badges(user, activity_type, activity_data=None):
        """
        Check if user qualifies for any badges based on activity
        Returns list of newly earned badges
        """
        newly_earned = []
        
        # Get all active badges
        active_badges = Badge.objects.filter(is_active=True)
        
        # Get user's existing badges
        user_badge_ids = set(
            UserBadge.objects.filter(user=user).values_list('badge_id', flat=True)
        )
        
        # Get user progress
        progress = GamificationService.get_or_create_progress(user)
        
        for badge in active_badges:
            # Skip if user already has this badge
            if badge.id in user_badge_ids:
                continue
            
            # Check if badge criteria is met
            if GamificationService._check_badge_criteria(user, badge, activity_type, activity_data, progress):
                # Award badge
                user_badge = UserBadge.objects.create(
                    user=user,
                    badge=badge,
                    related_activity_type=activity_type,
                    related_activity_id=activity_data.get('id') if activity_data else None
                )
                
                # Add points
                if badge.points_reward > 0:
                    progress.add_points(badge.points_reward, f'badge_{badge.id}')
                
                # Update badge count
                progress.total_badges_earned += 1
                progress.save()
                
                # Create activity feed entry
                ActivityFeed.objects.create(
                    user=user,
                    activity_type='badge_earned',
                    title=f'🏆 Badge Earned: {badge.name}',
                    description=badge.description,
                    related_badge=badge,
                    points_earned=badge.points_reward,
                    visibility='public'
                )
                
                newly_earned.append({
                    'id': str(badge.id),
                    'name': badge.name,
                    'description': badge.description,
                    'category': badge.category,
                    'rarity': badge.rarity,
                    'points_reward': badge.points_reward,
                    'icon_url': badge.icon_url,
                    'icon_name': badge.icon_name,
                })
        
        return newly_earned
    
    @staticmethod
    def _check_badge_criteria(user, badge, activity_type, activity_data, progress):
        """Check if badge criteria is met"""
        criteria = badge.criteria or {}
        action = criteria.get('action')
        count = criteria.get('count', 1)
        period = criteria.get('period', 'all_time')  # days, weeks, months, all_time
        
        if not action:
            return False
        
        # Symptom logging badges
        if action == 'log_symptoms':
            if activity_type == 'symptom_logged':
                # Check total symptom logs
                from .models import PatientSymptomLog
                logs_query = PatientSymptomLog.objects.filter(patient=user)
                
                if period == 'days':
                    days = criteria.get('days', 7)
                    start_date = date.today() - timedelta(days=days)
                    logs_query = logs_query.filter(log_date__gte=start_date)
                elif period == 'weeks':
                    weeks = criteria.get('weeks', 1)
                    start_date = date.today() - timedelta(weeks=weeks)
                    logs_query = logs_query.filter(log_date__gte=start_date)
                elif period == 'months':
                    months = criteria.get('months', 1)
                    start_date = date.today() - timedelta(days=months * 30)
                    logs_query = logs_query.filter(log_date__gte=start_date)
                
                return logs_query.count() >= count
        
        # Consistency badges (streaks)
        elif action == 'maintain_streak':
            streak_days = criteria.get('days', 7)
            if period == 'current':
                return progress.current_streak >= streak_days
            elif period == 'longest':
                return progress.longest_streak >= streak_days
        
        # Points-based badges
        elif action == 'earn_points':
            if period == 'total':
                return progress.total_points >= count
            elif period == 'weekly':
                return progress.weekly_points >= count
            elif period == 'monthly':
                return progress.monthly_points >= count
        
        # Level-based badges
        elif action == 'reach_level':
            return progress.level >= count
        
        # Badge count badges
        elif action == 'earn_badges':
            return progress.total_badges_earned >= count
        
        # Challenge completion badges
        elif action == 'complete_challenges':
            completed = ChallengeParticipation.objects.filter(
                user=user,
                status='completed'
            ).count()
            return completed >= count
        
        # Activity-specific badges
        elif action == 'specific_activity':
            activity_name = criteria.get('activity_name')
            if activity_type == activity_name:
                return True
        
        return False
    
    @staticmethod
    def award_points(user, points, activity_type, description=None):
        """Award points to user for an activity"""
        progress = GamificationService.get_or_create_progress(user)
        progress.add_points(points, activity_type)
        
        # Update streak if it's a daily activity
        if activity_type in ['symptom_logged', 'daily_checkin']:
            progress.update_streak()
        
        # Create activity feed entry
        if description:
            ActivityFeed.objects.create(
                user=user,
                activity_type='custom',
                title=f'✨ {description}',
                description=f'Earned {points} points',
                points_earned=points,
                visibility='public'
            )
        
        return progress
    
    @staticmethod
    def check_level_up(user):
        """Check if user leveled up and return level info"""
        progress = GamificationService.get_or_create_progress(user)
        old_level = progress.level
        new_level = progress.calculate_level()
        
        if new_level > old_level:
            # Create level up activity feed
            ActivityFeed.objects.create(
                user=user,
                activity_type='level_up',
                title=f'🎉 Level Up!',
                description=f'Congratulations! You reached Level {new_level}!',
                points_earned=0,
                visibility='public'
            )
            return {
                'leveled_up': True,
                'old_level': old_level,
                'new_level': new_level,
                'total_points': progress.total_points
            }
        return {'leveled_up': False}
    
    @staticmethod
    def get_recent_earned_badges(user, limit=5):
        """Get recently earned badges for a user"""
        return UserBadge.objects.filter(
            user=user
        ).select_related('badge').order_by('-earned_at')[:limit]
    
    @staticmethod
    def get_user_stats(user):
        """Get comprehensive user stats"""
        progress = GamificationService.get_or_create_progress(user)
        
        return {
            'level': progress.level,
            'total_points': progress.total_points,
            'current_streak': progress.current_streak,
            'longest_streak': progress.longest_streak,
            'total_badges': progress.total_badges_earned,
            'total_challenges_completed': progress.total_challenges_completed,
            'points_to_next_level': progress.points_to_next_level,
        }

