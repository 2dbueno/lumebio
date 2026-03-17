from django import forms
from django.core.validators import URLValidator

from apps.pages.models import Block, Page


class PageEditForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = ['title', 'bio', 'theme', 'is_published']

    def __init__(self, *args, profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = profile

    def clean_theme(self):
        theme = self.cleaned_data.get('theme')
        if theme in Page.PRO_THEMES and self.profile and not self.profile.is_pro:
            raise forms.ValidationError(
                'Este tema é exclusivo do plano Pro. Faça upgrade para utilizá-lo.'
            )
        return theme


class BlockForm(forms.ModelForm):
    TYPES_WITH_URL = ('link', 'social')

    url = forms.URLField(
        required=False,
        assume_scheme='https',
    )

    class Meta:
        model = Block
        fields = ['block_type', 'title', 'url', 'description', 'icon', 'is_active']

    def clean_url(self):
        url        = self.cleaned_data.get('url', '').strip()
        block_type = self.cleaned_data.get('block_type', '')

        if block_type in self.TYPES_WITH_URL and url:
            validator = URLValidator()
            try:
                validator(url)
            except forms.ValidationError:
                raise forms.ValidationError(
                    'Insira uma URL válida (ex: https://exemplo.com).'
                )

        return url