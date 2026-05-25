from datetime import date, timedelta
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from core.models.location_models import Region, City, Club
from core.models.member_models import Member
from core.models.subscription_models import SubscriptionPlan, MemberSubscription
from core.models.freeze_models import Freeze, FreezeLog, SubscriptionFreezePeriod
from core.tasks import process_bulk_freeze

User = get_user_model()

@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
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

    def test_get_freeze_details_view(self):
        # Create a region freeze
        freeze = Freeze.objects.create(
            target_type="region",
            region=self.region,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 10),
            reason="Renovation",
            created_by=self.user
        )
        # Process the freeze
        process_bulk_freeze(freeze.id)
        
        # Log in the user and call the view
        self.client.login(username="testadmin", password="password123")
        response = self.client.get(f'/freezes/{freeze.id}/details/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['id'], freeze.id)
        self.assertEqual(data['target_type'], 'region')
        self.assertEqual(data['target_name'], 'Region A')
        self.assertEqual(len(data['logs']), 1)
        self.assertEqual(data['logs'][0]['member_name'], 'John Doe')
        self.assertEqual(data['logs'][0]['status'], 'success')

    def test_get_freeze_details_view_with_pending_members(self):
        # 1. Create another member and active subscription in the same region
        member2 = Member.objects.create(
            club=self.club,
            full_name="Jane Smith",
            mobile="0987654321",
            joined_at=date(2026, 1, 1)
        )
        sub2 = MemberSubscription.objects.create(
            member=member2,
            club=self.club,
            subscription_plan=self.plan,
            start_date=date(2026, 1, 1),
            original_end_date=date(2026, 1, 31),
            status="active"
        )

        # 2. Create a region freeze
        freeze = Freeze.objects.create(
            target_type="region",
            region=self.region,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 10),
            reason="Partial success test",
            created_by=self.user
        )

        # 3. Simulate a partial run where ONLY self.subscription has a FreezeLog
        # We manually create a successful FreezeLog for self.subscription
        FreezeLog.objects.create(
            freeze=freeze,
            member_subscription=self.subscription,
            status="success",
            old_end_date=self.subscription.original_end_date,
            new_end_date=date(2026, 2, 10),
            freeze_days=10
        )

        # 4. Log in the user and call the view
        self.client.login(username="testadmin", password="password123")
        response = self.client.get(f'/freezes/{freeze.id}/details/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['id'], freeze.id)
        
        # We expect 2 logs in total: one processed ('success') and one pending ('pending')
        self.assertEqual(len(data['logs']), 2)
        
        # Sort logs by member name to ensure deterministic assertions
        sorted_logs = sorted(data['logs'], key=lambda x: x['member_name'])
        
        self.assertEqual(sorted_logs[0]['member_name'], 'Jane Smith')
        self.assertEqual(sorted_logs[0]['status'], 'pending')
        
        self.assertEqual(sorted_logs[1]['member_name'], 'John Doe')
        self.assertEqual(sorted_logs[1]['status'], 'success')


