from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0005_remove_linkclick_user_agent_linkclick_device_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='Theme',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug',        models.SlugField(unique=True)),
                ('name',        models.CharField(max_length=50)),
                ('is_pro',      models.BooleanField(default=False)),
                ('is_active',   models.BooleanField(default=True)),
                ('bg',          models.CharField(max_length=50)),
                ('primary',     models.CharField(max_length=50)),
                ('accent',      models.CharField(max_length=50)),
                ('card_bg',     models.CharField(max_length=100)),
                ('card_border', models.CharField(max_length=100)),
                ('text',        models.CharField(max_length=50)),
                ('subtext',     models.CharField(max_length=50)),
            ],
            options={
                'verbose_name': 'Tema',
                'verbose_name_plural': 'Temas',
                'ordering': ['is_pro', 'name'],
            },
        ),
    ]