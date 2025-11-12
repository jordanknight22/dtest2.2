from django import forms
from base import static_data  # your module that loads RE_RATED_CACHE

class UserForms(forms.Form):
    copay_choices = [
        ('yes', 'Yes'),
        ('no', 'No'),
        ('*', '*'),
    ]

    copay = forms.ChoiceField(
        choices=copay_choices,
        label='Co-Pay',
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='*'
    )

    asat_date = forms.ChoiceField(
        label='As At Date',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Load dataframe from your cache
        static_data.load_re_rated_cache()
        df_merged = static_data.RE_RATED_CACHE

        # Get unique inception months (as strings, like '2025.07')
        months = (
            df_merged['inception_month']
            .dropna()
            .astype(float)
            .unique()
        )

        # Sort chronologically (works with YYYY.MM format)
        months = sorted(months)

        # Assign dropdown choices (value, label)
        self.fields['asat_date'].choices = [(m, m) for m in months]

        # Default to the latest available inception_month
        if months:
            self.fields['asat_date'].initial = months[-1]