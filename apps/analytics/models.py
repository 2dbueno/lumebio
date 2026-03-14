from django.db import models
from apps.pages.models import Page


class PageView(models.Model):
    DEVICE_CHOICES = [
        ('mobile', 'Mobile'),
        ('tablet', 'Tablet'),
        ('desktop', 'Desktop'),
    ]

    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='page_views')
    viewed_at = models.DateTimeField(auto_now_add=True)
    ip_anon = models.CharField(max_length=45, blank=True)   # IP já anonimizado
    device_type = models.CharField(max_length=10, choices=DEVICE_CHOICES, default='desktop')
    referer_domain = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'Visualização'
        verbose_name_plural = 'Visualizações'
        ordering = ['-viewed_at']

    def __str__(self):
        return f'View {self.page} — {self.viewed_at}'


class DailyAggregate(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='daily_aggregates')
    date = models.DateField()
    total_views = models.PositiveIntegerField(default=0)
    total_clicks = models.PositiveIntegerField(default=0)
    mobile_count = models.PositiveIntegerField(default=0)
    desktop_count = models.PositiveIntegerField(default=0)
    tablet_count = models.PositiveIntegerField(default=0)
    top_referer = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ['page', 'date']
        verbose_name = 'Agregado Diário'
        verbose_name_plural = 'Agregados Diários'
        ordering = ['-date']

    def __str__(self):
        return f'{self.page} — {self.date}'