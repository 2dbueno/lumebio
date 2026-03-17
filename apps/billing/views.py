import json, re, logging
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


def _limpar_cpf(cpf: str) -> str:
    """Remove pontos e traço, retorna só dígitos."""
    return re.sub(r'[^\d]', '', cpf)

def _cpf_valido(cpf: str) -> bool:
    """Valida CPF — formato e dígitos verificadores."""
    cpf = _limpar_cpf(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[j]) * (i + 1 - j) for j in range(i))
        if int(cpf[i]) != (soma * 10 % 11) % 10:
            return False
    return True


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
        
        # em views.py, no bloco de validação do CPF
        if not profile.cpf:
            if not cpf:
                messages.error(request, 'CPF é obrigatório para pagamento via Pix.')
                return render(request, 'billing/checkout.html', {'plan': plan, 'profile': profile})
            
            # Verifica se CPF já está em uso por outro perfil
            from apps.accounts.models import Profile as ProfileModel
            import re
            cpf_limpo = re.sub(r'[^\d]', '', cpf)
            if ProfileModel.objects.filter(cpf=cpf_limpo).exclude(pk=profile.pk).exists():
                messages.error(request, 'Este CPF já está cadastrado em outra conta.')
                return render(request, 'billing/checkout.html', {'plan': plan, 'profile': profile})
            
            profile.cpf = cpf_limpo
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
    Recebe notificações do AbacatePay v2.
    Segurança: secret via query string + HMAC opcional via X-Webhook-Signature.
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

    # ── 2. Validar HMAC (camada extra — recomendação AbacatePay v2)
    signature = request.headers.get('X-Webhook-Signature', '')
    if signature:
        from apps.billing.services import verify_webhook_hmac
        if not verify_webhook_hmac(request.body, signature):
            logger.warning('Webhook com assinatura HMAC inválida.')
            return HttpResponse(status=401)

    # ── 3. Parse do payload
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event    = payload.get('event')
    dev_mode = payload.get('devMode', False)
    data     = payload.get('data', {})

    logger.info(f'Webhook AbacatePay v2: {event} | devMode={dev_mode}')

    # ── 4. Roteamento de eventos v2
    if event == 'checkout.completed':
        checkout       = data.get('checkout', {})
        customer       = data.get('customer', {})
        billing_id     = checkout.get('id', '')
        customer_id    = customer.get('id', '')
        customer_email = customer.get('email', '')

        if not billing_id or not customer_email:
            logger.error(
                f'checkout.completed com campos faltando: '
                f'billing_id={billing_id}, email={customer_email}'
            )
            return HttpResponse(status=200)

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(email=customer_email)
            services.activate_subscription(user.profile, billing_id, customer_id)
            logger.info(f'Assinatura ativada via webhook v2: {customer_email}')

        except User.DoesNotExist:
            logger.error(f'checkout.completed: usuário não encontrado — {customer_email}')
            return HttpResponse(status=200)

        except Exception as e:
            logger.error(f'Erro ao processar checkout.completed: {e}')
            return HttpResponse(status=500)

    elif event == 'checkout.refunded':
        checkout       = data.get('checkout', {})
        customer       = data.get('customer', {})
        billing_id     = checkout.get('id', '')
        customer_email = customer.get('email', '')

        if not billing_id or not customer_email:
            logger.error(f'checkout.refunded com campos faltando.')
            return HttpResponse(status=200)

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(email=customer_email)
            services.deactivate_subscription(user.profile, billing_id)
            logger.info(f'Assinatura desativada por reembolso: {customer_email}')

        except User.DoesNotExist:
            logger.error(f'checkout.refunded: usuário não encontrado — {customer_email}')
        except Exception as e:
            logger.error(f'Erro ao processar checkout.refunded: {e}')
            return HttpResponse(status=500)

    elif event == 'checkout.disputed':
        logger.info('checkout.disputed recebido — monitorar manualmente.')

    elif event in ('subscription.completed', 'subscription.renewed'):
        # AbacatePay gerencia recorrência — tratar igual ao checkout.completed
        subscription = data.get('subscription', {})
        customer     = data.get('customer', {})
        payment      = data.get('payment', {})
        billing_id   = payment.get('id', '')
        customer_id  = customer.get('id', '')
        customer_email = customer.get('email', '')

        if billing_id and customer_email:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(email=customer_email)
                services.activate_subscription(user.profile, billing_id, customer_id)
                logger.info(f'{event} processado: {customer_email}')
            except Exception as e:
                logger.error(f'Erro ao processar {event}: {e}')
                return HttpResponse(status=500)

    elif event == 'subscription.cancelled':
        customer       = data.get('customer', {})
        customer_email = customer.get('email', '')
        if customer_email:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(email=customer_email)
                services.cancel_subscription(user.profile)
                logger.info(f'Assinatura cancelada via webhook: {customer_email}')
            except Exception as e:
                logger.error(f'Erro ao processar subscription.cancelled: {e}')

    else:
        logger.info(f'Evento não tratado: {event}')

    return HttpResponse(status=200)