from django.db import migrations

THEMES = [
    # ── Free
    {
        'slug': 'neon-dark', 'name': 'Neon Dark', 'is_pro': False,
        'bg': '#0F0F1A', 'primary': '#7C3AED', 'accent': '#A78BFA',
        'card_bg': 'rgba(255,255,255,0.05)', 'card_border': 'rgba(124,58,237,0.3)',
        'text': '#ffffff', 'subtext': '#a0a0b0',
    },
    {
        'slug': 'cyber-blue', 'name': 'Cyber Blue', 'is_pro': False,
        'bg': '#020B18', 'primary': '#2563EB', 'accent': '#60A5FA',
        'card_bg': 'rgba(37,99,235,0.08)', 'card_border': 'rgba(96,165,250,0.3)',
        'text': '#ffffff', 'subtext': '#8ab4d4',
    },
    {
        'slug': 'aurora', 'name': 'Aurora', 'is_pro': False,
        'bg': '#0D1117', 'primary': '#7C3AED', 'accent': '#DB2777',
        'card_bg': 'rgba(255,255,255,0.04)', 'card_border': 'rgba(219,39,119,0.25)',
        'text': '#ffffff', 'subtext': '#c084fc',
    },
    # ── Pro
    {
        'slug': 'midnight-purple', 'name': 'Midnight Purple', 'is_pro': True,
        'bg': '#0A0010', 'primary': '#6D28D9', 'accent': '#C4B5FD',
        'card_bg': 'rgba(109,40,217,0.1)', 'card_border': 'rgba(196,181,253,0.2)',
        'text': '#EDE9FE', 'subtext': '#A78BFA',
    },
    {
        'slug': 'solar-flare', 'name': 'Solar Flare', 'is_pro': True,
        'bg': '#0F0800', 'primary': '#EA580C', 'accent': '#FCD34D',
        'card_bg': 'rgba(234,88,12,0.1)', 'card_border': 'rgba(252,211,77,0.25)',
        'text': '#FEF3C7', 'subtext': '#FCA5A5',
    },
    {
        'slug': 'forest-dark', 'name': 'Forest Dark', 'is_pro': True,
        'bg': '#020D05', 'primary': '#16A34A', 'accent': '#86EFAC',
        'card_bg': 'rgba(22,163,74,0.08)', 'card_border': 'rgba(134,239,172,0.2)',
        'text': '#F0FDF4', 'subtext': '#6EE7B7',
    },
    {
        'slug': 'rose-gold', 'name': 'Rose Gold', 'is_pro': True,
        'bg': '#120008', 'primary': '#E11D72', 'accent': '#FCA5A5',
        'card_bg': 'rgba(225,29,114,0.08)', 'card_border': 'rgba(252,165,165,0.25)',
        'text': '#FFF1F2', 'subtext': '#FDA4AF',
    },
    {
        'slug': 'ocean-deep', 'name': 'Ocean Deep', 'is_pro': True,
        'bg': '#00080F', 'primary': '#0891B2', 'accent': '#67E8F9',
        'card_bg': 'rgba(8,145,178,0.08)', 'card_border': 'rgba(103,232,249,0.2)',
        'text': '#ECFEFF', 'subtext': '#A5F3FC',
    },
    {
        'slug': 'volcanic', 'name': 'Volcanic', 'is_pro': True,
        'bg': '#0F0200', 'primary': '#DC2626', 'accent': '#FB923C',
        'card_bg': 'rgba(220,38,38,0.08)', 'card_border': 'rgba(251,146,60,0.25)',
        'text': '#FFF7ED', 'subtext': '#FCA5A5',
    },
    {
        'slug': 'arctic', 'name': 'Arctic', 'is_pro': True,
        'bg': '#00050F', 'primary': '#3B82F6', 'accent': '#BAE6FD',
        'card_bg': 'rgba(59,130,246,0.06)', 'card_border': 'rgba(186,230,253,0.2)',
        'text': '#F0F9FF', 'subtext': '#BAE6FD',
    },
    {
        'slug': 'tokyo-night', 'name': 'Tokyo Night', 'is_pro': True,
        'bg': '#0A0014', 'primary': '#9333EA', 'accent': '#F472B6',
        'card_bg': 'rgba(147,51,234,0.08)', 'card_border': 'rgba(244,114,182,0.2)',
        'text': '#FAF5FF', 'subtext': '#E879F9',
    },
    {
        'slug': 'golden-hour', 'name': 'Golden Hour', 'is_pro': True,
        'bg': '#0C0800', 'primary': '#D97706', 'accent': '#FDE68A',
        'card_bg': 'rgba(217,119,6,0.08)', 'card_border': 'rgba(253,230,138,0.25)',
        'text': '#FFFBEB', 'subtext': '#FCD34D',
    },
    {
        'slug': 'matrix', 'name': 'Matrix', 'is_pro': True,
        'bg': '#000900', 'primary': '#16A34A', 'accent': '#4ADE80',
        'card_bg': 'rgba(22,163,74,0.06)', 'card_border': 'rgba(74,222,128,0.2)',
        'text': '#F0FFF0', 'subtext': '#86EFAC',
    },
]


def seed_themes(apps, schema_editor):
    Theme = apps.get_model('pages', 'Theme')
    for data in THEMES:
        Theme.objects.get_or_create(slug=data['slug'], defaults={**data, 'is_active': True})


def unseed_themes(apps, schema_editor):
    Theme = apps.get_model('pages', 'Theme')
    Theme.objects.filter(slug__in=[t['slug'] for t in THEMES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0006_theme'),
    ]

    operations = [
        migrations.RunPython(seed_themes, reverse_code=unseed_themes),
    ]