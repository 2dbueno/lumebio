from django.db import models
from django.conf import settings


class Page(models.Model):
    THEME_CHOICES = [
        ('neon-dark', 'Neon Dark'),
        ('cyber-blue', 'Cyber Blue'),
        ('aurora', 'Aurora'),
    ]

    THEMES = {
        'neon-dark': {
            'bg': '#0F0F1A',
            'primary': '#7C3AED',
            'accent': '#A78BFA',
            'card_bg': 'rgba(255,255,255,0.05)',
            'card_border': 'rgba(124,58,237,0.3)',
            'text': '#ffffff',
            'subtext': '#a0a0b0',
        },
        'cyber-blue': {
            'bg': '#020B18',
            'primary': '#2563EB',
            'accent': '#60A5FA',
            'card_bg': 'rgba(37,99,235,0.08)',
            'card_border': 'rgba(96,165,250,0.3)',
            'text': '#ffffff',
            'subtext': '#8ab4d4',
        },
        'aurora': {
            'bg': '#0D1117',
            'primary': '#7C3AED',
            'accent': '#DB2777',
            'card_bg': 'rgba(255,255,255,0.04)',
            'card_border': 'rgba(219,39,119,0.25)',
            'text': '#ffffff',
            'subtext': '#c084fc',
        },
    }

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='page'
    )
    title = models.CharField(max_length=100, blank=True)
    bio = models.TextField(max_length=300, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='neon-dark')
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Página'
        verbose_name_plural = 'Páginas'

    def __str__(self):
        return f'Página de {self.user.email}'

    def get_theme_vars(self):
        return self.THEMES.get(self.theme, self.THEMES['neon-dark'])


class Block(models.Model):
    BLOCK_TYPES = [
        ('link', 'Link'),
        ('header', 'Cabeçalho'),
        ('divider', 'Divisor'),
        ('text', 'Texto'),
        ('social', 'Rede Social'),
    ]

    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='blocks')
    block_type = models.CharField(max_length=20, choices=BLOCK_TYPES, default='link')
    title = models.CharField(max_length=100, blank=True)
    url = models.URLField(blank=True)
    description = models.CharField(max_length=200, blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Bloco'
        verbose_name_plural = 'Blocos'

    def __str__(self):
        return f'{self.block_type}: {self.title}'


class LinkClick(models.Model):
    block = models.ForeignKey(Block, on_delete=models.CASCADE, related_name='link_clicks')
    clicked_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referer = models.URLField(blank=True)

    class Meta:
        verbose_name = 'Clique'
        verbose_name_plural = 'Cliques'
