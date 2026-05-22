from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from core.models.location_models import Region, City, Club
from core.models.member_models import Member
from core.models.subscription_models import SubscriptionPlan, MemberSubscription
from core.models.freeze_models import Freeze, FreezeLog, SubscriptionFreezePeriod
from core.tasks import process_bulk_freeze

User = get_user_model()

class CeleryFreezeTaskTestCase(TestCase):
    def setUp(self):
        # 1. Create a User
        self.user = User.objects.create_user(username="testadmin", password="password123")
        
        # 2. Setup locations
        self.region = Region.objects.create(name="Region A")
        self.city = City.objects.create(region=self.region, name="City A")
        self.club = Club.objects.create(city=self.city, name="Club A")
        
        # 3. Create a member
        self.member = Member.objects.create(
            club=self.club,
            full_name="John Doe",
            mobile="1234567890",
            joined_at=date(2026, 1, 1)
        )
        
        # 4. Create a plan
        self.plan = SubscriptionPlan.objects.create(
            name="Plan 30 Days",
            duration_days=30,
            amount=99.99
        )
        
        # 5. Create a subscription
        self.subscription = MemberSubscription.objects.create(
            member=self.member,
            club=self.club,
            subscription_plan=self.plan,
            start_date=date(2026, 1, 1),
            original_end_date=date(2026, 1, 31),
            status="active"
        )

    def test_region_freeze_celery_task_success(self):
        # Create a region freeze
        freeze = Freeze.objects.create(
            target_type="region",
            region=self.region,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 10), # 10 days
            reason="Renovation",
            created_by=self.user
        )
        
        # Execute Celery task
        result = process_bulk_freeze(freeze.id)
        
        # Refresh from database
        freeze.refresh_from_db()
        self.subscription.refresh_from_db()
        
        # Assertions
        self.assertEqual(freeze.status, "completed")
        self.assertEqual(freeze.total_members, 1)
        self.assertEqual(freeze.processed_members, 1)
        self.assertEqual(freeze.error_logs, "")
        
        # End date should be extended by 10 days (31 + 10 = Feb 10)
        expected_end_date = date(2026, 2, 10)
        self.assertEqual(self.subscription.effective_end_date, expected_end_date)
        
        # Assert log entries are created
        self.assertTrue(FreezeLog.objects.filter(freeze=freeze, status="success").exists())
        self.assertTrue(SubscriptionFreezePeriod.objects.filter(freeze=freeze, member_subscription=self.subscription).exists())

    def test_member_freeze_celery_task_success(self):
        # Create a member freeze
        freeze = Freeze.objects.create(
            target_type="member",
            member=self.member,
            start_date=date(2026, 2, 15),
            end_date=date(2026, 2, 24), # 10 days
            reason="Medical",
            created_by=self.user
        )
        
        # Execute Celery task via delay / async call (which is eager under test)
        res = process_bulk_freeze.delay(freeze.id)
        
        # Refresh
        freeze.refresh_from_db()
        self.subscription.refresh_from_db()
        
        # Assertions
        self.assertEqual(freeze.status, "completed")
        self.assertEqual(freeze.total_members, 1)
        self.assertEqual(freeze.processed_members, 1)
        self.assertEqual(freeze.error_logs, "")
        
        # Since this is the first freeze on this subscription, it extends the original_end_date by 10 days
        self.assertEqual(self.subscription.effective_end_date, date(2026, 2, 10))
