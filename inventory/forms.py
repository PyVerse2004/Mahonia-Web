from django import forms
from . models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product

        fields = [
            "name",
            "stock_quantity",
            "sale_price"
        ]

        labels = {
            "name" : "نام محصول",
            "stock_quantity" : "موجودی انبار",
            "sale_price" : "قیمت"
        }

        widget = {
            "name" : forms.TextInput(attrs={"class" : "form_control" , "placeholder" : "نام محصول"}),
            "stock_quantity" : forms.NumberInput(attrs={"class" : "form_control" , "min" : 0}),
            "sale_price" : forms.NumberInput(attrs={"class" : "form_control" , "min" : 0 , "step" : 1})
        }