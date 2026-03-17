from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_profile_marketing_consent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='custom_domain_expires_at',
            field=models.DateTimeField(
                null=True, blank=True,
                help_text='Preenchido no downgrade. Domínio é removido após 15 dias.',
            ),
        ),
    ]