from decimal import Decimal
from django import forms
from .models import Category


class CategoryPriceUpdateForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        label='Категорія'
    )

    percent = forms.DecimalField(
        label='Відсоток зміни',
        max_digits=6,
        decimal_places=2,
        required=False,
        help_text='Наприклад: 10 = +10%, -15 = -15%'
    )

    fixed_amount = forms.DecimalField(
        label='Фіксована сума зміни',
        max_digits=10,
        decimal_places=2,
        required=False,
        help_text='Наприклад: 50 = +50 грн, -25 = -25 грн'
    )

    update_products = forms.BooleanField(
        required=False,
        initial=True,
        label='Оновити базову ціну товарів без варіантів'
    )

    update_variants = forms.BooleanField(
        required=False,
        initial=True,
        label='Оновити ціни варіантів товарів'
    )

    def clean(self):
        cleaned_data = super().clean()
        percent = cleaned_data.get("percent")
        fixed_amount = cleaned_data.get("fixed_amount")

        if percent in (None, Decimal("0")) and fixed_amount in (None, Decimal("0")):
            raise forms.ValidationError("Вкажіть або відсоток зміни, або фіксовану суму.")

        if percent not in (None, Decimal("0")) and fixed_amount not in (None, Decimal("0")):
            raise forms.ValidationError("Заповніть тільки одне поле: або відсоток, або фіксовану суму.")

        return cleaned_data