from django.contrib import admin

from .models import Supplier

# Invoices are deliberately not registered in Django admin: modifying invoices
# via admin bypasses stock movement logging and weighted cost recalculations.
# Invoices should only be created or edited via application views.
admin.site.register(Supplier)
