from django.db import models
from django.conf import settings


class Plan(models.Model):
    SLUG_FREE = 'free'
    SLUG_PRO = 'pro'

    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_links = models.PositiveIntegerField(null=True, blank=True)  # None = ilimitado
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Plano'
        verbose_name_plural = 'Planos'

    def __str__(self):
        return self.name

    @property
    def price_in_cents(self):
        """Preço em centavos para a API do AbacatePay."""
        return int(self.price_monthly * 100)


class Subscription(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_PENDING = 'pending'
    STATUS_CANCELLED = 'cancelled'
    STATUS_PAST_DUE = 'past_due'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Ativa'),
        (STATUS_PENDING, 'Aguardando pagamento'),
        (STATUS_CANCELLED, 'Cancelada'),
        (STATUS_PAST_DUE, 'Pagamento atrasado'),
    ]

    profile = models.OneToOneField(
        'accounts.Profile',
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    abacate_billing_id = models.CharField(max_length=100, blank=True)  # ID da cobrança no AbacatePay
    abacate_customer_id = models.CharField(max_length=100, blank=True)
    current_period_start = models.DateField(null=True, blank=True)
    current_period_end = models.DateField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'

    def __str__(self):
        return f'{self.profile.slug} — {self.plan.name} ({self.status})'

    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE


class Invoice(models.Model):
    STATUS_PAID = 'paid'
    STATUS_PENDING = 'pending'
    STATUS_EXPIRED = 'expired'

    STATUS_CHOICES = [
        (STATUS_PAID, 'Pago'),
        (STATUS_PENDING, 'Pendente'),
        (STATUS_EXPIRED, 'Expirado'),
    ]

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    abacate_billing_id = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    billing_url = models.URLField(blank=True)  # link do Pix para o usuário pagar
    paid_at = models.DateTimeField(null=True, blank=True)
    reference_month = models.DateField()  # mês de referência da cobrança
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Fatura'
        verbose_name_plural = 'Faturas'
        ordering = ['-created_at']

    def __str__(self):
        return f'Fatura {self.reference_month} — {self.subscription.profile.slug} ({self.status})'