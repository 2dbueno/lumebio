from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def charge_monthly_subscriptions():
    """
    Cria cobranças mensais para todas as assinaturas ativas.
    Agendar via Celery Beat: dia 1 de cada mês às 09:00.
    """
    from apps.billing.models import Subscription, Invoice
    from apps.billing.services import create_monthly_billing
    from django.utils import timezone
    from datetime import date

    today = date.today()
    active_subs = Subscription.objects.filter(
        status=Subscription.STATUS_ACTIVE
    ).select_related('profile', 'plan')

    resultados = []
    for sub in active_subs:
        # Verifica se já foi cobrado esse mês
        already_billed = Invoice.objects.filter(
            subscription=sub,
            reference_month=today.replace(day=1),
        ).exists()

        if already_billed:
            resultados.append(f'{sub.profile.slug}: já cobrado esse mês')
            continue

        try:
            result = create_monthly_billing(sub)

            # Cria fatura pendente — será marcada como paga pelo webhook
            Invoice.objects.create(
                subscription=sub,
                abacate_billing_id=result['billing_id'],
                amount=sub.plan.price_monthly,
                status=Invoice.STATUS_PENDING,
                billing_url=result['url'],
                reference_month=today.replace(day=1),
            )

            # Marca como past_due até o pagamento ser confirmado
            sub.status = Subscription.STATUS_PAST_DUE
            sub.save(update_fields=['status'])

            resultados.append(f'{sub.profile.slug}: cobrança criada — {result["billing_id"]}')
            logger.info(f'Cobrança mensal criada: {sub.profile.slug}')

        except Exception as e:
            resultados.append(f'{sub.profile.slug}: ERRO — {str(e)}')
            logger.error(f'Erro ao cobrar {sub.profile.slug}: {e}')

    return ' | '.join(resultados) or 'Nenhuma assinatura ativa.'


@shared_task
def cancel_overdue_subscriptions():
    """
    Cancela assinaturas com pagamento em atraso há mais de 7 dias.
    Agendar via Celery Beat: todo dia às 10:00.
    """
    from apps.billing.models import Subscription, Invoice
    from apps.billing.services import cancel_subscription
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=7)

    overdue_subs = Subscription.objects.filter(
        status=Subscription.STATUS_PAST_DUE,
        updated_at__lte=cutoff,
    ).select_related('profile')

    cancelados = []
    for sub in overdue_subs:
        cancel_subscription(sub.profile)
        cancelados.append(sub.profile.slug)
        logger.warning(f'Assinatura cancelada por inadimplência: {sub.profile.slug}')

    return f'Cancelados por inadimplência: {", ".join(cancelados)}' if cancelados else 'Nenhum cancelamento.'