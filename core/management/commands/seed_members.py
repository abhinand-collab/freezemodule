import random
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models.location_models import Region, City, Club
from core.models.member_models import Member
from core.models.subscription_models import SubscriptionPlan, MemberSubscription


REGIONS = ['North', 'South', 'East', 'West', 'Central']
CITIES = {
    'North':   ['Delhi', 'Chandigarh', 'Amritsar'],
    'South':   ['Chennai', 'Bangalore', 'Hyderabad'],
    'East':    ['Kolkata', 'Bhubaneswar', 'Patna'],
    'West':    ['Mumbai', 'Pune', 'Ahmedabad'],
    'Central': ['Bhopal', 'Nagpur', 'Indore'],
}
CLUBS_PER_CITY = ['Alpha Fitness', 'Beta Gym', 'Gamma Wellness']

PLANS = [
    {'name': '1 Month',  'duration_days': 30,  'amount': 999.00},
    {'name': '3 Months', 'duration_days': 90,  'amount': 2499.00},
    {'name': '6 Months', 'duration_days': 180, 'amount': 4499.00},
    {'name': '1 Year',   'duration_days': 365, 'amount': 7999.00},
]

FIRST_NAMES = [
    'Aarav', 'Vivaan', 'Aditya', 'Vihaan', 'Arjun', 'Sai', 'Reyan', 'Arnav',
    'Ishaan', 'Krishna', 'Priya', 'Ananya', 'Diya', 'Isha', 'Kavya', 'Meera',
    'Neha', 'Pooja', 'Riya', 'Sneha', 'Raj', 'Rohan', 'Karan', 'Nikhil',
    'Rahul', 'Vikram', 'Amit', 'Deepak', 'Suresh', 'Ramesh',
]
LAST_NAMES = [
    'Sharma', 'Verma', 'Gupta', 'Singh', 'Kumar', 'Patel', 'Shah', 'Mehta',
    'Joshi', 'Nair', 'Rao', 'Iyer', 'Pillai', 'Reddy', 'Malhotra', 'Kapoor',
    'Bose', 'Das', 'Chatterjee', 'Mishra',
]


class Command(BaseCommand):
    help = 'Seed 10,000 members with active subscriptions (start_date=today, end_date=today+plan_duration)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10000,
            help='Number of members to create (default: 10000)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing members and subscriptions before seeding',
        )

    def handle(self, *args, **options):
        count = options['count']
        clear = options['clear']

        if clear:
            self.stdout.write(self.style.WARNING('Clearing existing members and subscriptions...'))
            MemberSubscription.objects.all().delete()
            Member.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared.'))

        # ── Step 1: Ensure Regions, Cities, Clubs exist ──────────────────────
        self.stdout.write('Setting up regions, cities, and clubs...')
        clubs = []
        for region_name in REGIONS:
            region, _ = Region.objects.get_or_create(name=region_name)
            for city_name in CITIES[region_name]:
                city, _ = City.objects.get_or_create(region=region, name=city_name)
                for club_name in CLUBS_PER_CITY:
                    club, _ = Club.objects.get_or_create(city=city, name=club_name)
                    clubs.append(club)

        self.stdout.write(self.style.SUCCESS(f'  {len(clubs)} clubs ready.'))

        # ── Step 2: Ensure Subscription Plans exist ───────────────────────────
        self.stdout.write('Setting up subscription plans...')
        plans = []
        for plan_data in PLANS:
            plan, _ = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults={
                    'duration_days': plan_data['duration_days'],
                    'amount': plan_data['amount'],
                    'is_active': True,
                }
            )
            plans.append(plan)

        self.stdout.write(self.style.SUCCESS(f'  {len(plans)} subscription plans ready.'))

        # ── Step 3: Bulk-create Members ───────────────────────────────────────
        self.stdout.write(f'Creating {count} members...')
        today = date.today()
        batch_size = 500

        member_objects = []
        for i in range(count):
            first = random.choice(FIRST_NAMES)
            last  = random.choice(LAST_NAMES)
            full_name = f'{first} {last}'
            mobile = f'9{random.randint(100000000, 999999999)}'
            email  = f'{first.lower()}.{last.lower()}{i}@example.com'
            club   = random.choice(clubs)
            member_objects.append(Member(
                club=club,
                full_name=full_name,
                mobile=mobile,
                email=email,
                joined_at=today,
                is_active=True,
            ))

        with transaction.atomic():
            created_members = []
            for start in range(0, len(member_objects), batch_size):
                batch = member_objects[start:start + batch_size]
                created = Member.objects.bulk_create(batch)
                created_members.extend(created)
                self.stdout.write(f'  Members: {min(start + batch_size, count)}/{count}', ending='\r')
                self.stdout.flush()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'  {len(created_members)} members created.'))

        # ── Step 4: Bulk-create Subscriptions ────────────────────────────────
        self.stdout.write('Creating subscriptions...')
        subscription_objects = []
        for member in created_members:
            plan = random.choice(plans)
            end_date = today + __import__('datetime').timedelta(days=plan.duration_days)
            subscription_objects.append(MemberSubscription(
                member=member,
                club=member.club,
                subscription_plan=plan,
                start_date=today,
                original_end_date=end_date,
                effective_end_date=end_date,
                status='active',
            ))

        with transaction.atomic():
            for start in range(0, len(subscription_objects), batch_size):
                batch = subscription_objects[start:start + batch_size]
                MemberSubscription.objects.bulk_create(batch)
                self.stdout.write(f'  Subscriptions: {min(start + batch_size, count)}/{count}', ending='\r')
                self.stdout.flush()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Done! {count} members with active subscriptions seeded successfully.'
        ))
        self.stdout.write(f'   Start date : {today}')
        self.stdout.write(f'   Plans used : {", ".join(p.name for p in plans)}')
        self.stdout.write(f'   Clubs used : {len(clubs)} clubs across {len(REGIONS)} regions')
