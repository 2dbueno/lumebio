"""
Serviços de billing usando o SDK do AbacatePay.

Versão atual: SDK v1 (v1.0.9)
Migração para v2: quando o SDK v2 for público, descomentar os blocos
marcados com "# v2:" e remover os blocos marcados com "# v1:".
Referência: https://docs.abacatepay.com/pages/sdks/python
"""
import hashlib
import hmac
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
    Se já tiver customer_id válido salvo, usa direto.
    """
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

    # v1: retorna customer.id diretamente
    customer_id = customer.id
    # v2: customer_id = customer.data.id

    logger.info(f'Cliente criado no AbacatePay: {customer_id} — {user.email}')
    return customer_id


def create_checkout(profile, plan) -> dict:
    """
    Cria checkout no AbacatePay.

    v1 (atual): produtos inline com name/price/description.
    v2 (futuro): produto pré-cadastrado na loja referenciado por ID.
    """
    client = get_abacate_client()
    today = date.today()
    customer_id = get_or_create_customer(profile)

    # ── v1 ────────────────────────────────────────────────────────────────────
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
    billing_url = billing.url
    billing_id  = billing.id
    # ── fim v1 ────────────────────────────────────────────────────────────────

    # ── v2 (descomentar quando SDK v2 for público) ────────────────────────────
    # billing = client.billing.create(
    #     items=[{
    #         'id': settings.ABACATEPAY_PRODUCT_PRO_ID,
    #         'quantity': 1,
    #     }],
    #     return_url=f'{settings.SITE_URL}/billing/',
    #     completion_url=f'{settings.SITE_URL}/billing/success/',
    #     customer_id=customer_id,
    # )
    # billing_url = billing.data.url
    # billing_id  = billing.data.id
    # ── fim v2 ────────────────────────────────────────────────────────────────

    logger.info(f'Checkout criado: {profile.slug} → {billing_id}')
    return {
        'url':         billing_url,
        'billing_id':  billing_id,
        'customer_id': customer_id,
    }


def create_monthly_billing(subscription) -> dict:
    """Cria uma cobrança mensal para uma assinatura ativa."""
    return create_checkout(subscription.profile, subscription.plan)


def verify_webhook_hmac(raw_body: bytes, signature_header: str) -> bool:
    """
    Valida assinatura HMAC-SHA256 do webhook AbacatePay v2.
    Header: X-Webhook-Signature
    Chave pública fornecida pela AbacatePay (fixa por ambiente).
    Referência: https://docs.abacatepay.com/pages/webhooks
    """
    ABACATEPAY_PUBLIC_KEY = (
        "t9dXRhHHo3yDEj5pVDYz0frf7q6bMKyMRmxxCPIPp3RCplBfXRxqlC6ZpiWmOqj4"
        "L63qEaeUOtrCI8P0VMUgo6iIga2ri9ogaHFs0WIIywSMg0q7RmBfybe1E5XJcfC4"
        "IW3alNqym0tXoAKkzvfEjZxV6bE0oG2zJrNNYmUCKZyV0KZ3JS8Votf9EAWWYdi"
        "DkMkpbMdPggfh1EqHlVkMiTady6jOR3hyzGEHrIz2Ret0xHKMbiqkr9HS1JhNHDX9"
    )

    if not signature_header:
        return False

    import base64
    expected = hmac.new(
        ABACATEPAY_PUBLIC_KEY.encode('utf-8'),
        raw_body,
        hashlib.sha256,
    ).digest()
    expected_b64 = base64.b64encode(expected).decode('utf-8')

    try:
        return hmac.compare_digest(expected_b64, signature_header)
    except Exception:
        return False


def activate_subscription(profile, billing_id: str, abacate_customer_id: str = ''):
    """Ativa a assinatura após confirmação de pagamento via webhook."""
    from apps.billing.models import Plan, Subscription, Invoice

    plan = Plan.objects.get(slug=Plan.SLUG_PRO)
    today = date.today()

    sub, _ = Subscription.objects.update_or_create(
        profile=profile,
        defaults={
            'plan':                 plan,
            'status':               Subscription.STATUS_ACTIVE,
            'abacate_billing_id':   billing_id,
            'abacate_customer_id':  abacate_customer_id,
            'current_period_start': today,
            'current_period_end':   today + relativedelta(months=1),
        }
    )

    Invoice.objects.update_or_create(
        subscription=sub,
        abacate_billing_id=billing_id,
        defaults={
            'amount':          plan.price_monthly,
            'status':          Invoice.STATUS_PAID,
            'paid_at':         timezone.now(),
            'reference_month': today.replace(day=1),
        }
    )

    profile.plan = 'pro'
    profile.save(update_fields=['plan'])

    logger.info(f'Assinatura ativada: {profile.slug} — {billing_id}')
    return sub


def deactivate_subscription(profile, billing_id: str):
    """Desativa a assinatura após reembolso via webhook."""
    from apps.billing.models import Subscription, Invoice
    from datetime import timedelta

    try:
        sub = Subscription.objects.get(profile=profile)
        sub.status = Subscription.STATUS_CANCELLED
        sub.cancelled_at = timezone.now()
        sub.save(update_fields=['status', 'cancelled_at'])

        Invoice.objects.filter(
            subscription=sub,
            abacate_billing_id=billing_id,
        ).update(status=Invoice.STATUS_PENDING)

    except Subscription.DoesNotExist:
        pass

    profile.plan = 'free'
    if profile.custom_domain:
        profile.custom_domain_expires_at = timezone.now() + timedelta(days=15)
        profile.save(update_fields=['plan', 'custom_domain_expires_at'])
    else:
        profile.save(update_fields=['plan'])

    logger.info(f'Assinatura desativada por reembolso: {profile.slug} — {billing_id}')


def cancel_subscription(profile):
    """Cancela a assinatura e faz downgrade para Free."""
    from apps.billing.models import Subscription
    from datetime import timedelta

    try:
        sub = Subscription.objects.get(profile=profile)
        sub.status = Subscription.STATUS_CANCELLED
        sub.cancelled_at = timezone.now()
        sub.save(update_fields=['status', 'cancelled_at'])
    except Subscription.DoesNotExist:
        pass

    profile.plan = 'free'
    if profile.custom_domain:
        profile.custom_domain_expires_at = timezone.now() + timedelta(days=15)
        profile.save(update_fields=['plan', 'custom_domain_expires_at'])
    else:
        profile.save(update_fields=['plan'])

    logger.info(f'Assinatura cancelada: {profile.slug}')