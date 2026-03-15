import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.contrib import messages
from django.conf import settings

from apps.billing.models import Plan, Subscription, Invoice
from apps.billing import services

logger = logging.getLogger(__name__)


@login_required
def pricing(request):
    """Página de planos — acessível por qualquer usuário logado."""
    plans = Plan.objects.filter(is_active=True).order_by('price_monthly')
    profile = request.user.profile

    try:
        subscription = profile.subscription
    except Subscription.DoesNotExist:
        subscription = None

    return render(request, 'billing/pricing.html', {
        'plans': plans,
        'profile': profile,
        'subscription': subscription,
    })


@login_required
def checkout(request):
    """
    Inicia o checkout no AbacatePay.
    GET:  exibe formulário para coletar CPF e telefone se não tiver.
    POST: cria a cobrança e redireciona para o link de pagamento.
    """
    profile = request.user.profile

    # Já é Pro e ativo — redireciona para o portal
    try:
        sub = profile.subscription
        if sub.is_active:
            messages.info(request, 'Você já tem uma assinatura ativa.')
            return redirect('billing:portal')
    except Subscription.DoesNotExist:
        pass

    plan = get_object_or_404(Plan, slug=Plan.SLUG_PRO, is_active=True)

    if request.method == 'POST':
        cpf   = request.POST.get('cpf', '').strip()
        phone = request.POST.get('phone', '').strip()

        if not profile.cpf:
            if not cpf:
                messages.error(request, 'CPF é obrigatório para pagamento via Pix.')
                return render(request, 'billing/checkout.html', {'plan': plan, 'profile': profile})
            profile.cpf = cpf
            profile.save(update_fields=['cpf'])

        if not profile.phone:
            if not phone:
                messages.error(request, 'Telefone é obrigatório para pagamento via Pix.')
                return render(request, 'billing/checkout.html', {'plan': plan, 'profile': profile})
            profile.phone = phone
            profile.save(update_fields=['phone'])

        try:
            result = services.create_checkout(profile, plan)

            # Salva billing_id e customer_id antes de redirecionar
            Subscription.objects.update_or_create(
                profile=profile,
                defaults={
                    'plan': plan,
                    'status': Subscription.STATUS_PENDING,
                    'abacate_billing_id': result['billing_id'],
                    'abacate_customer_id': result['customer_id'],
                }
            )

            logger.info(f'Checkout criado: {profile.slug} → {result["billing_id"]}')
            return redirect(result['url'])

        except Exception as e:
            logger.error(f'Erro no checkout {profile.slug}: {e}')
            messages.error(request, 'Erro ao criar cobrança. Tente novamente.')
            return render(request, 'billing/checkout.html', {'plan': plan, 'profile': profile})

    return render(request, 'billing/checkout.html', {'plan': plan, 'profile': profile})


@login_required
def success(request):
    """Página exibida após o usuário completar o pagamento."""
    return render(request, 'billing/success.html', {'profile': request.user.profile})


@login_required
def portal(request):
    """Portal de gerenciamento da assinatura."""
    profile = request.user.profile

    try:
        subscription = profile.subscription
        invoices = subscription.invoices.order_by('-created_at')[:12]
    except Subscription.DoesNotExist:
        subscription = None
        invoices = []

    return render(request, 'billing/portal.html', {
        'profile': profile,
        'subscription': subscription,
        'invoices': invoices,
    })


@login_required
@require_POST
def cancel(request):
    """Cancela a assinatura do usuário."""
    profile = request.user.profile
    services.cancel_subscription(profile)
    messages.success(request, 'Assinatura cancelada. Você voltou ao plano Free.')
    return redirect('billing:portal')


@csrf_exempt
@require_POST
def webhook(request):
    """
    Recebe notificações do AbacatePay.
    Segurança: secret validado via query string (?secret=).
    """
    # ── 1. Validar secret
    secret_recebido = request.GET.get('secret', '')
    secret_esperado = settings.ABACATEPAY_WEBHOOK_SECRET

    if not secret_esperado:
        logger.error('ABACATEPAY_WEBHOOK_SECRET não configurado.')
        return HttpResponse(status=500)

    if secret_recebido != secret_esperado:
        logger.warning('Webhook recebido com secret inválido.')
        return HttpResponse(status=401)

    # ── 2. Parse do payload
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event    = payload.get('event')
    dev_mode = payload.get('devMode', False)
    data     = payload.get('data', {})

    logger.info(f'Webhook AbacatePay: {event} | devMode={dev_mode}')

    # ── 3. Roteamento de eventos
    if event == 'billing.paid':
        billing_id     = data.get('id', '')
        customer_id    = data.get('customer', {}).get('id', '')
        customer_email = data.get('customer', {}).get('email', '')

        # Validação dos campos obrigatórios
        if not billing_id or not customer_email:
            logger.error(
                f'Webhook billing.paid com campos faltando: '
                f'billing_id={billing_id}, email={customer_email}'
            )
            return HttpResponse(status=200)  # 200 para não reenviar

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            user = User.objects.get(email=customer_email)
            services.activate_subscription(user.profile, billing_id, customer_id)
            logger.info(f'Assinatura ativada via webhook: {customer_email}')

        except User.DoesNotExist:
            logger.error(f'Webhook billing.paid: usuário não encontrado — {customer_email}')
            return HttpResponse(status=200)

        except Exception as e:
            logger.error(f'Erro ao processar billing.paid: {e}')
            return HttpResponse(status=500)

    elif event == 'billing.refunded':
        # TODO: implementar lógica de reembolso
        logger.info('billing.refunded recebido — não processado ainda.')

    elif event == 'billing.failed':
        logger.info('billing.failed recebido — não processado ainda.')

    return HttpResponse(status=200)