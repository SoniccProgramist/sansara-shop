from django import forms
from .models import Category


class CategoryPriceUpdateForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        label='Категорія'
    )
    percent = forms.DecimalField(
        label='Відсоток зміни',
        max_digits=6,
        decimal_places=2,
        help_text='Наприклад: 10 = +10%, -15 = -15%'
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)