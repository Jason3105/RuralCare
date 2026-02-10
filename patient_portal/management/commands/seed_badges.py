"""
Management command to seed initial badges for gamification
"""

from django.core.management.base import BaseCommand
from patient_portal.models import Badge


class Command(BaseCommand):
    help = 'Seed initial badges for gamification system'

    def handle(self, *args, **options):
        badges_data = [
            {
                'name': 'First Steps',
                'description': 'Logged your first symptom entry',
                'category': 'symptom_tracking',
                'rarity': 'common',
                'points_reward': 50,
                'criteria': {
                    'action': 'log_symptoms',
                    'count': 1,
                    'period': 'all_time'
                },
                'icon_name': 'fa-heartbeat'
            },
            {
                'name': 'Week Warrior',
                'description': 'Logged symptoms for 7 consecutive days',
                'category': 'consistency',
                'rarity': 'uncommon',
                'points_reward': 100,
                'criteria': {
                    'action': 'maintain_streak',
                    'days': 7,
                    'period': 'current'
                },
                'icon_name': 'fa-calendar-check'
            },
            {
                'name': 'Monthly Champion',
                'description': 'Logged symptoms for 30 consecutive days',
                'category': 'consistency',
                'rarity': 'rare',
                'points_reward': 500,
                'criteria': {
                    'action': 'maintain_streak',
                    'days': 30,
                    'period': 'current'
                },
                'icon_name': 'fa-trophy'
            },
            {
                'name': 'Dedicated Logger',
                'description': 'Logged symptoms 10 times',
                'category': 'symptom_tracking',
                'rarity': 'uncommon',
                'points_reward': 150,
                'criteria': {
                    'action': 'log_symptoms',
                    'count': 10,
                    'period': 'all_time'
                },
                'icon_name': 'fa-clipboard-list'
            },
            {
                'name': 'Century Club',
                'description': 'Earned 100 points',
                'category': 'milestone',
                'rarity': 'common',
                'points_reward': 0,
                'criteria': {
                    'action': 'earn_points',
                    'count': 100,
                    'period': 'total'
                },
                'icon_name': 'fa-star'
            },
            {
                'name': 'Point Master',
                'description': 'Earned 500 points',
                'category': 'milestone',
                'rarity': 'uncommon',
                'points_reward': 0,
                'criteria': {
                    'action': 'earn_points',
                    'count': 500,
                    'period': 'total'
                },
                'icon_name': 'fa-medal'
            },
            {
                'name': 'Rising Star',
                'description': 'Reached Level 5',
                'category': 'milestone',
                'rarity': 'rare',
                'points_reward': 0,
                'criteria': {
                    'action': 'reach_level',
                    'count': 5
                },
                'icon_name': 'fa-star'
            },
            {
                'name': 'Badge Collector',
                'description': 'Earned 5 badges',
                'category': 'milestone',
                'rarity': 'uncommon',
                'points_reward': 200,
                'criteria': {
                    'action': 'earn_badges',
                    'count': 5
                },
                'icon_name': 'fa-award'
            },
            {
                'name': 'Daily Dedication',
                'description': 'Logged symptoms for 7 days in a week',
                'category': 'consistency',
                'rarity': 'uncommon',
                'points_reward': 150,
                'criteria': {
                    'action': 'log_symptoms',
                    'count': 7,
                    'period': 'days',
                    'days': 7
                },
                'icon_name': 'fa-calendar-day'
            },
            {
                'name': 'Wellness Warrior',
                'description': 'Logged symptoms for 30 days',
                'category': 'wellness',
                'rarity': 'rare',
                'points_reward': 300,
                'criteria': {
                    'action': 'log_symptoms',
                    'count': 30,
                    'period': 'all_time'
                },
                'icon_name': 'fa-heart'
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for badge_data in badges_data:
            badge, created = Badge.objects.update_or_create(
                name=badge_data['name'],
                defaults={
                    'description': badge_data['description'],
                    'category': badge_data['category'],
                    'rarity': badge_data['rarity'],
                    'points_reward': badge_data['points_reward'],
                    'criteria': badge_data['criteria'],
                    'icon_name': badge_data.get('icon_name', 'fa-trophy'),
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created badge: {badge.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Updated badge: {badge.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully seeded badges! Created: {created_count}, Updated: {updated_count}'
            )
        )

