from django.db import models
from django.conf import settings

class Theme(models.Model):
    """
    Representa um tema visual disponível para páginas bio.
    Migrado do dict hardcoded Page.THEMES para permitir gestão via admin e banco.
    """
    slug       = models.SlugField(unique=True)
    name       = models.CharField(max_length=50)
    is_pro     = models.BooleanField(default=False)
    is_active  = models.BooleanField(default=True)
    # CSS vars
    bg         = models.CharField(max_length=50)
    primary    = models.CharField(max_length=50)
    accent     = models.CharField(max_length=50)
    card_bg    = models.CharField(max_length=100)
    card_border = models.CharField(max_length=100)
    text       = models.CharField(max_length=50)
    subtext    = models.CharField(max_length=50)

    class Meta:
        verbose_name = 'Tema'
        verbose_name_plural = 'Temas'
        ordering = ['is_pro', 'name']

    def __str__(self):
        return f'{self.name} {"(Pro)" if self.is_pro else "(Free)"}'

    def as_vars(self) -> dict:
        """Retorna dict compatível com o template público."""
        return {
            'bg':          self.bg,
            'primary':     self.primary,
            'accent':      self.accent,
            'card_bg':     self.card_bg,
            'card_border': self.card_border,
            'text':        self.text,
            'subtext':     self.subtext,
        }


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

    def get_theme_vars(self) -> dict:
            """
            Lê as variáveis CSS do banco via model Theme.
            Fallback para neon-dark se o tema não existir.
            """
            try:
                return Theme.objects.get(slug=self.theme, is_active=True).as_vars()
            except Theme.DoesNotExist:
                fallback = Theme.objects.filter(slug='neon-dark').first()
                if fallback:
                    return fallback.as_vars()
                # Último recurso — nunca deve chegar aqui após a seed
                return {
                    'bg': '#0F0F1A', 'primary': '#7C3AED', 'accent': '#A78BFA',
                    'card_bg': 'rgba(255,255,255,0.05)', 'card_border': 'rgba(124,58,237,0.3)',
                    'text': '#ffffff', 'subtext': '#a0a0b0',
                }

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