"""
Serviços de billing usando o SDK oficial do AbacatePay.
Toda comunicação com a API do AbacatePay fica aqui.
"""
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_abacate_client():
    from abacatepay import AbacatePay
    return AbacatePay(settings.ABACATEPAY_API_KEY)


def get_or_create_customer(profile) -> str:
    """
    Garante que o cliente existe no AbacatePay.
    - Se já tiver um customer_id válido salvo (começa com 'cust_'), usa direto.
    - Caso contrário, cria um novo cliente e retorna o ID.
    """
    # Verifica se já tem customer_id válido salvo
    try:
        sub = profile.subscription
        cid = sub.abacate_customer_id
        if cid and cid.startswith('cust_'):
            return cid
    except Exception:
        pass

    client = get_abacate_client()
    user = profile.user

    customer = client.customers.create({
        'name': profile.display_name or user.email.split('@')[0],
        'email': user.email,
        'cellphone': profile.phone,
        'tax_id': profile.cpf,
    })

    customer_id = customer.id
    logger.info(f'Cliente criado no AbacatePay: {customer_id} — {user.email}')
    return customer_id


def create_checkout(profile, plan) -> dict:
    """
    Cria uma cobrança no AbacatePay.
    Retorna dict com url, billing_id e customer_id.
    """
    client = get_abacate_client()
    today = date.today()

    # 1. Garante cliente no AbacatePay e pega ID válido
    customer_id = get_or_create_customer(profile)

    # 2. Cria a cobrança com o customerId
    billing = client.billing.create(
        products=[{
            'external_id': f'plan_{plan.slug}_{profile.slug}_{today}',
            'name': f'LumeBio {plan.name} — {today.strftime("%m/%Y")}',
            'quantity': 1,
            'price': plan.price_in_cents,
            'description': f'Assinatura mensal do plano {plan.name}',
        }],
        return_url=f'{settings.SITE_URL}/billing/',
        completion_url=f'{settings.SITE_URL}/billing/success/',
        customer_id=customer_id,
        frequency='ONE_TIME',
    )

    return {
        'url': billing.url,
        'billing_id': billing.id,
        'customer_id': customer_id,
    }


def create_monthly_billing(subscription) -> dict:
    """Cria uma cobrança mensal para uma assinatura ativa."""
    return create_checkout(subscription.profile, subscription.plan)


def activate_subscription(profile, billing_id: str, abacate_customer_id: str = ''):
    """
    Ativa a assinatura após confirmação de pagamento via webhook.
    """
    from apps.billing.models import Plan, Subscription, Invoice

    plan = Plan.objects.get(slug=Plan.SLUG_PRO)
    today = date.today()

    sub, _ = Subscription.objects.update_or_create(
        profile=profile,
        defaults={
            'plan': plan,
            'status': Subscription.STATUS_ACTIVE,
            'abacate_billing_id': billing_id,
            'abacate_customer_id': abacate_customer_id,
            'current_period_start': today,
            'current_period_end': today + relativedelta(months=1),
        }
    )

    Invoice.objects.update_or_create(
        subscription=sub,
        abacate_billing_id=billing_id,
        defaults={
            'amount': plan.price_monthly,
            'status': Invoice.STATUS_PAID,
            'paid_at': timezone.now(),
            'reference_month': today.replace(day=1),
        }
    )

    profile.plan = 'pro'
    profile.save(update_fields=['plan'])

    logger.info(f'Assinatura ativada: {profile.slug} — {billing_id}')
    return sub


def cancel_subscription(profile):
    """Cancela a assinatura e faz downgrade para Free."""
    from apps.billing.models import Subscription

    try:
        sub = Subscription.objects.get(profile=profile)
        sub.status = Subscription.STATUS_CANCELLED
        sub.cancelled_at = timezone.now()
        sub.save(update_fields=['status', 'cancelled_at'])
    except Subscription.DoesNotExist:
        pass

    profile.plan = 'free'
    profile.save(update_fields=['plan'])

    logger.info(f'Assinatura cancelada: {profile.slug}')