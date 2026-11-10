from django.contrib.auth.models import Group, Permission, User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROLE_SELLER = "seller"
    ROLE_MANAGER = "manager"
    ROLE_CHOICES = [
        (ROLE_SELLER, "فروشنده"),
        (ROLE_MANAGER, "مدیر"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="کاربر",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_SELLER,
        verbose_name="نقش",
    )

    class Meta:
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "پروفایل‌های کاربری"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_manager(self):
        return self.role == self.ROLE_MANAGER or self.user.is_superuser

    @property
    def is_seller(self):
        return self.role == self.ROLE_SELLER and not self.user.is_superuser


def sync_user_role_permissions(user, role):
    """
    همگام‌سازی دسترسی‌ها و گروه‌ها بر اساس نقش:
    - نقش فروشنده: فاکتور فروش، اشخاص، مشاهده انبار و کالا. بدون دسترسی به فاکتور خرید، تامین‌کنندگان و سود و زیان.
    - نقش مدیر: دسترسی کامل به تمامی بخش‌های سامانه.
    """
    try:
        manager_group, _ = Group.objects.get_or_create(name="مدیران")
        seller_group, _ = Group.objects.get_or_create(name="فروشندگان")

        seller_permission_codenames = [
            # sales_invoice
            "view_sale",
            "add_sale",
            "change_sale",
            "delete_sale",
            # persons
            "view_person",
            "add_person",
            "change_person",
            "delete_person",
            # inventory
            "view_product",
            "view_stockmovement",
        ]
        seller_perms = Permission.objects.filter(codename__in=seller_permission_codenames)
        seller_group.permissions.set(seller_perms)

        manager_perms = Permission.objects.filter(
            content_type__app_label__in=["inventory", "purchases", "sales_invoice", "persons"]
        )
        manager_group.permissions.set(manager_perms)

        if role == UserProfile.ROLE_MANAGER:
            user.groups.remove(seller_group)
            user.groups.add(manager_group)
            is_staff_val = True
        else:
            user.groups.remove(manager_group)
            user.groups.add(seller_group)
            is_staff_val = False

        if not user.is_superuser and user.is_staff != is_staff_val:
            User.objects.filter(pk=user.pk).update(is_staff=is_staff_val)
    except Exception:
        # در زمان اجرای اولیه‌ی مایگریشن‌ها یا شرایطی که جداول پر نشده‌اند
        pass


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        default_role = (
            UserProfile.ROLE_MANAGER if instance.is_superuser else UserProfile.ROLE_SELLER
        )
        UserProfile.objects.get_or_create(
            user=instance, defaults={"role": default_role}
        )
