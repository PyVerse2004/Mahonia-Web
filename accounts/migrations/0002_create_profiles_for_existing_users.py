from django.db import migrations


def create_profiles_for_existing_users(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("accounts", "UserProfile")
    for user in User.objects.all():
        role = "manager" if user.is_superuser else "seller"
        UserProfile.objects.get_or_create(user=user, defaults={"role": role})


def reverse_profiles(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_profiles_for_existing_users, reverse_profiles),
    ]

