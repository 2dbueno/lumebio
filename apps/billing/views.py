import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.contrib import messages

from apps.billing.models import Plan, Subscription, Invoice
from apps.billing import services

logger = logging.getLogger(__name__)


@login_required
def pricing(request):
    """Página pública de planos — acessível por qualquer usuário logado."""
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
    GET: exibe formulário para coletar CPF e telefone se não tiver.
    POST: cria a cobrança e redireciona para o link de pagamento.
    """
    profile = request.user.profile

    # Já é Pro e ativo
    try:
        sub = profile.subscription
        if sub.is_active:
            messages.info(request, 'Você já tem uma assinatura ativa.')
            return redirect('billing:portal')
    except Subscription.DoesNotExist:
        pass

    plan = get_object_or_404(Plan, slug=Plan.SLUG_PRO, is_active=True)

    if request.method == 'POST':
        # Coleta CPF e telefone se não tiver
        cpf = request.POST.get('cpf', '').strip()
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

            # Cria ou atualiza assinatura como pendente
            sub, _ = Subscription.objects.update_or_create(
                profile=profile,
                defaults={
                    'plan': plan,
                    'status': Subscription.STATUS_PENDING,
                    'abacate_billing_id': result['billing_id'],
                }
            )

            # Redireciona para a página de pagamento do AbacatePay
            return redirect(result['url'])

        except Exception as e:
            logger.error(f'Erro no checkout: {e}')
            messages.error(request, 'Erro ao criar cobrança. Tente novamente.')
            return render(request, 'billing/checkout.html', {'plan': plan, 'profile': profile})

    return render(request, 'billing/checkout.html', {'plan': plan, 'profile': profile})


@login_required
def success(request):
    """Página exibida após o usuário completar o pagamento."""
    profile = request.user.profile
    return render(request, 'billing/success.html', {'profile': profile})


@login_required
def portal(request):
    """Portal de gerenciamento da assinatura no dashboard."""
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
    Evento principal: billing.paid → ativa a assinatura.
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event = payload.get('event')
    data = payload.get('data', {})

    logger.info(f'Webhook AbacatePay recebido: {event}')

    if event == 'billing.paid':
        billing_id = data.get('id', '')
        customer_id = data.get('customer', {}).get('id', '')
        customer_email = data.get('customer', {}).get('email', '')

        try:
            from django.contrib.auth import get_user_model
            from apps.accounts.models import Profile
            User = get_user_model()

            user = User.objects.get(email=customer_email)
            profile = user.profile
            services.activate_subscription(profile, billing_id, customer_id)

            logger.info(f'Assinatura ativada via webhook: {customer_email}')

        except Exception as e:
            logger.error(f'Erro ao processar webhook billing.paid: {e}')
            return HttpResponse(status=500)

    return HttpResponse(status=200)