from django.core.management.base import BaseCommand
from authentication.models import User

class Command(BaseCommand):
    help = 'Create test users for Patient, Doctor, and Admin roles'

    def handle(self, *args, **options):
        # Test users data
        test_users = [
            {
                'email': 'patientpatient@CureShieldSynapse.com',
                'name': 'John Patient',
                'role': 'PATIENT',
                'password': 'patient123',
                'age': 35,
                'gender': 'M',
                'blood_group': 'A+'
            },
            {
                'email': 'doctorpatient@CureShieldSynapse.com',
                'name': 'Dr. Sarah Smith',
                'role': 'DOCTOR',
                'password': 'doctor123',
                'age': 42,
                'gender': 'F',
                'blood_group': 'O+'
            },
            {
                'email': 'adminpatient@CureShieldSynapse.com',
                'name': 'Admin Manager',
                'role': 'HOSPITAL_ADMIN',
                'password': 'admin123',
                'age': 45,
                'gender': 'M',
                'blood_group': 'B+'
            }
        ]

        created_count = 0
        updated_count = 0

        for user_data in test_users:
            email = user_data['email']
            password = user_data.pop('password')
            
            # Check if user already exists
            user, created = User.objects.get_or_create(
                email=email,
                defaults=user_data
            )
            
            if created:
                # Set password for new user
                user.set_password(password)
                user.save()
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created {user_data["role"]} user: {email}')
                )
            else:
                # Update existing user's password
                user.set_password(password)
                user.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated {user_data["role"]} user: {email}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed test users. Created: {created_count}, Updated: {updated_count}'
            )
        ) 