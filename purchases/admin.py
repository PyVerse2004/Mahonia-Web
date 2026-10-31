from django.contrib import admin

from .models import Supplier

# فاکتورها عمداً در admin ثبت نشده‌اند: تغییر فاکتور از admin موجودی انبار و
# میانگین قیمت خرید را به‌روز نمی‌کند. ثبت و ویرایش فاکتور فقط از صفحه‌های خود برنامه.
admin.site.register(Supplier)
