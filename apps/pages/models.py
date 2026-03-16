from django.db import models
from django.conf import settings


class Page(models.Model):
    THEME_CHOICES = [
        # Free
        ('neon-dark',        'Neon Dark'),
        ('cyber-blue',       'Cyber Blue'),
        ('aurora',           'Aurora'),
        # Pro
        ('midnight-purple',  'Midnight Purple'),
        ('solar-flare',      'Solar Flare'),
        ('forest-dark',      'Forest Dark'),
        ('rose-gold',        'Rose Gold'),
        ('ocean-deep',       'Ocean Deep'),
        ('volcanic',         'Volcanic'),
        ('arctic',           'Arctic'),
        ('tokyo-night',      'Tokyo Night'),
        ('golden-hour',      'Golden Hour'),
        ('matrix',           'Matrix'),
    ]

    # Temas exclusivos Pro
    PRO_THEMES = {
        'midnight-purple',
        'solar-flare',
        'forest-dark',
        'rose-gold',
        'ocean-deep',
        'volcanic',
        'arctic',
        'tokyo-night',
        'golden-hour',
        'matrix',
    }

    THEMES = {
        # ── Free
        'neon-dark': {
            'bg': '#0F0F1A', 'primary': '#7C3AED', 'accent': '#A78BFA',
            'card_bg': 'rgba(255,255,255,0.05)', 'card_border': 'rgba(124,58,237,0.3)',
            'text': '#ffffff', 'subtext': '#a0a0b0',
        },
        'cyber-blue': {
            'bg': '#020B18', 'primary': '#2563EB', 'accent': '#60A5FA',
            'card_bg': 'rgba(37,99,235,0.08)', 'card_border': 'rgba(96,165,250,0.3)',
            'text': '#ffffff', 'subtext': '#8ab4d4',
        },
        'aurora': {
            'bg': '#0D1117', 'primary': '#7C3AED', 'accent': '#DB2777',
            'card_bg': 'rgba(255,255,255,0.04)', 'card_border': 'rgba(219,39,119,0.25)',
            'text': '#ffffff', 'subtext': '#c084fc',
        },
        # ── Pro
        'midnight-purple': {
            'bg': '#0A0010', 'primary': '#6D28D9', 'accent': '#C4B5FD',
            'card_bg': 'rgba(109,40,217,0.1)', 'card_border': 'rgba(196,181,253,0.2)',
            'text': '#EDE9FE', 'subtext': '#A78BFA',
        },
        'solar-flare': {
            'bg': '#0F0800', 'primary': '#EA580C', 'accent': '#FCD34D',
            'card_bg': 'rgba(234,88,12,0.1)', 'card_border': 'rgba(252,211,77,0.25)',
            'text': '#FEF3C7', 'subtext': '#FCA5A5',
        },
        'forest-dark': {
            'bg': '#020D05', 'primary': '#16A34A', 'accent': '#86EFAC',
            'card_bg': 'rgba(22,163,74,0.08)', 'card_border': 'rgba(134,239,172,0.2)',
            'text': '#F0FDF4', 'subtext': '#6EE7B7',
        },
        'rose-gold': {
            'bg': '#120008', 'primary': '#E11D72', 'accent': '#FCA5A5',
            'card_bg': 'rgba(225,29,114,0.08)', 'card_border': 'rgba(252,165,165,0.25)',
            'text': '#FFF1F2', 'subtext': '#FDA4AF',
        },
        'ocean-deep': {
            'bg': '#00080F', 'primary': '#0891B2', 'accent': '#67E8F9',
            'card_bg': 'rgba(8,145,178,0.08)', 'card_border': 'rgba(103,232,249,0.2)',
            'text': '#ECFEFF', 'subtext': '#A5F3FC',
        },
        'volcanic': {
            'bg': '#0F0200', 'primary': '#DC2626', 'accent': '#FB923C',
            'card_bg': 'rgba(220,38,38,0.08)', 'card_border': 'rgba(251,146,60,0.25)',
            'text': '#FFF7ED', 'subtext': '#FCA5A5',
        },
        'arctic': {
            'bg': '#00050F', 'primary': '#3B82F6', 'accent': '#BAE6FD',
            'card_bg': 'rgba(59,130,246,0.06)', 'card_border': 'rgba(186,230,253,0.2)',
            'text': '#F0F9FF', 'subtext': '#BAE6FD',
        },
        'tokyo-night': {
            'bg': '#0A0014', 'primary': '#9333EA', 'accent': '#F472B6',
            'card_bg': 'rgba(147,51,234,0.08)', 'card_border': 'rgba(244,114,182,0.2)',
            'text': '#FAF5FF', 'subtext': '#E879F9',
        },
        'golden-hour': {
            'bg': '#0C0800', 'primary': '#D97706', 'accent': '#FDE68A',
            'card_bg': 'rgba(217,119,6,0.08)', 'card_border': 'rgba(253,230,138,0.25)',
            'text': '#FFFBEB', 'subtext': '#FCD34D',
        },
        'matrix': {
            'bg': '#000900', 'primary': '#16A34A', 'accent': '#4ADE80',
            'card_bg': 'rgba(22,163,74,0.06)', 'card_border': 'rgba(74,222,128,0.2)',
            'text': '#F0FFF0', 'subtext': '#86EFAC',
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
    block      = models.ForeignKey(Block, on_delete=models.CASCADE, related_name='link_clicks')
    clicked_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_type = models.CharField(
        max_length=10,
        choices=[('mobile', 'Mobile'), ('tablet', 'Tablet'), ('desktop', 'Desktop')],
        default='desktop',
    )
    referer = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Clique'
        verbose_name_plural = 'Cliques'