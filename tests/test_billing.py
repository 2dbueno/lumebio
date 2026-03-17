"""
Testes de billing — webhook AbacatePay e tasks Celery
"""
import json
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta

from apps.billing.models import Invoice, Plan, Subscription
from apps.pages.models import Page


# ─── Fixtures locais ──────────────────────────────────────────────────────────

@pytest.fixture
def plan_free(db):
    plan, _ = Plan.objects.get_or_create(
        slug='free',
        defaults={'name': 'Free', 'price_monthly': 0, 'max_links': 5, 'is_active': True},
    )
    return plan


@pytest.fixture
def plan_pro(db):
    plan, _ = Plan.objects.get_or_create(
        slug='pro',
        defaults={'name': 'Pro', 'price_monthly': 29, 'max_links': None, 'is_active': True},
    )
    return plan


@pytest.fixture
def subscription_pending(db, user, plan_pro):
    return Subscription.objects.create(
        profile=user.profile,
        plan=plan_pro,
        status=Subscription.STATUS_PENDING,
        abacate_billing_id='bill_test123',
        abacate_customer_id='cust_test123',
    )


@pytest.fixture
def subscription_active(db, user, plan_pro):
    today = date.today()
    from dateutil.relativedelta import relativedelta
    return Subscription.objects.create(
        profile=user.profile,
        plan=plan_pro,
        status=Subscription.STATUS_ACTIVE,
        abacate_billing_id='bill_active123',
        abacate_customer_id='cust_active123',
        current_period_start=today,
        current_period_end=today + relativedelta(months=1),
    )


def _webhook_payload(event='billing.paid', billing_id='bill_test123',
                     customer_id='cust_test123', email='user@test.com'):
    return json.dumps({
        'event': event,
        'devMode': True,
        'data': {
            'id': billing_id,
            'customer': {
                'id': customer_id,
                'email': email,
            },
        },
    })


def _post_webhook(client, payload, secret=None):
    from django.conf import settings
    if secret is None:
        secret = settings.ABACATEPAY_WEBHOOK_SECRET
    return client.post(
        f'/billing/webhook/?secret={secret}',
        data=payload,
        content_type='application/json',
    )

# ─── Webhook: secret ─────────────────────────────────────────────────────────

class TestWebhookSecurity:

    def test_secret_invalido_retorna_401(self, client, db):
        response = _post_webhook(client, _webhook_payload(), secret='errado')
        assert response.status_code == 401

    def test_secret_correto_retorna_200(self, client, subscription_pending, user):
        response = _post_webhook(client, _webhook_payload(email=user.email))
        assert response.status_code == 200

    def test_payload_invalido_retorna_400(self, client, db):
        response = _post_webhook(client, 'json_invalido{{{')
        assert response.status_code == 400

    def test_sem_secret_retorna_401(self, client, db):
        response = client.post(
            '/billing/webhook/',
            data=_webhook_payload(),
            content_type='application/json',
        )
        assert response.status_code == 401


# ─── Webhook: billing.paid ───────────────────────────────────────────────────

class TestWebhookBillingPaid:

    def test_pagamento_confirmado_ativa_assinatura(self, client, subscription_pending, user, plan_pro):
        assert user.profile.plan == 'free'

        response = _post_webhook(client, _webhook_payload(email=user.email))
        assert response.status_code == 200

        user.profile.refresh_from_db()
        assert user.profile.plan == 'pro'

        sub = Subscription.objects.get(profile=user.profile)
        assert sub.status == Subscription.STATUS_ACTIVE

    def test_pagamento_confirmado_cria_invoice(self, client, subscription_pending, user):
        response = _post_webhook(client, _webhook_payload(email=user.email))
        assert response.status_code == 200

        assert Invoice.objects.filter(
            subscription__profile=user.profile,
            status=Invoice.STATUS_PAID,
        ).exists()

    def test_pagamento_confirmado_preenche_periodo(self, client, subscription_pending, user):
        response = _post_webhook(client, _webhook_payload(email=user.email))
        assert response.status_code == 200

        sub = Subscription.objects.get(profile=user.profile)
        assert sub.current_period_start is not None
        assert sub.current_period_end is not None
        assert sub.current_period_end > sub.current_period_start

    def test_usuario_inexistente_retorna_200_sem_erro(self, client, db):
        """Webhook com email desconhecido deve retornar 200 (não reenviar)."""
        response = _post_webhook(client, _webhook_payload(email='naoexiste@test.com'))
        assert response.status_code == 200

    def test_billing_id_ausente_retorna_200_sem_processar(self, client, db):
        payload = json.dumps({
            'event': 'billing.paid',
            'devMode': True,
            'data': {
                'id': '',
                'customer': {'id': 'cust_x', 'email': 'user@test.com'},
            },
        })
        response = _post_webhook(client, payload)
        assert response.status_code == 200

    def test_email_ausente_retorna_200_sem_processar(self, client, db):
        payload = json.dumps({
            'event': 'billing.paid',
            'devMode': True,
            'data': {
                'id': 'bill_x',
                'customer': {'id': 'cust_x', 'email': ''},
            },
        })
        response = _post_webhook(client, payload)
        assert response.status_code == 200


# ─── Webhook: outros eventos ──────────────────────────────────────────────────

class TestWebhookOtherEvents:

    def test_billing_refunded_retorna_200(self, client, db):
        payload = json.dumps({'event': 'billing.refunded', 'devMode': True, 'data': {}})
        response = _post_webhook(client, payload)
        assert response.status_code == 200

    def test_billing_failed_retorna_200(self, client, db):
        payload = json.dumps({'event': 'billing.failed', 'devMode': True, 'data': {}})
        response = _post_webhook(client, payload)
        assert response.status_code == 200

    def test_evento_desconhecido_retorna_200(self, client, db):
        payload = json.dumps({'event': 'billing.unknown', 'devMode': True, 'data': {}})
        response = _post_webhook(client, payload)
        assert response.status_code == 200


# ─── Task: charge_monthly_subscriptions ──────────────────────────────────────

class TestChargeMonthlySubscriptions:

    def test_cria_invoice_para_assinatura_ativa(self, db, subscription_active):
        from apps.billing.tasks import charge_monthly_subscriptions

        mock_result = {
            'url': 'https://abacatepay.com/pay/bill_new',
            'billing_id': 'bill_new123',
            'customer_id': 'cust_active123',
        }

        with patch('apps.billing.tasks.create_monthly_billing', return_value=mock_result):
            charge_monthly_subscriptions()

        assert Invoice.objects.filter(
            subscription=subscription_active,
            status=Invoice.STATUS_PENDING,
        ).exists()

    def test_idempotente_nao_cobra_duas_vezes_no_mes(self, db, subscription_active):
        """Rodar duas vezes no mesmo mês não deve criar 2 invoices."""
        from apps.billing.tasks import charge_monthly_subscriptions

        mock_result = {
            'url': 'https://abacatepay.com/pay/bill_new',
            'billing_id': 'bill_new123',
            'customer_id': 'cust_active123',
        }

        with patch('apps.billing.tasks.create_monthly_billing', return_value=mock_result):
            charge_monthly_subscriptions()
            charge_monthly_subscriptions()

        assert Invoice.objects.filter(subscription=subscription_active).count() == 1

    def test_marca_subscription_como_past_due(self, db, subscription_active):
        from apps.billing.tasks import charge_monthly_subscriptions

        mock_result = {
            'url': 'https://abacatepay.com/pay/bill_new',
            'billing_id': 'bill_new123',
            'customer_id': 'cust_active123',
        }

        with patch('apps.billing.tasks.create_monthly_billing', return_value=mock_result):
            charge_monthly_subscriptions()

        subscription_active.refresh_from_db()
        assert subscription_active.status == Subscription.STATUS_PAST_DUE

    def test_sem_assinaturas_ativas_retorna_mensagem(self, db):
        from apps.billing.tasks import charge_monthly_subscriptions

        result = charge_monthly_subscriptions()
        assert result == 'Nenhuma assinatura ativa.'

    def test_ja_cobrado_pula_e_registra_mensagem(self, db, subscription_active, plan_pro):
        from apps.billing.tasks import charge_monthly_subscriptions

        # Cria invoice do mês atual
        Invoice.objects.create(
            subscription=subscription_active,
            abacate_billing_id='bill_existente',
            amount=plan_pro.price_monthly,
            status=Invoice.STATUS_PENDING,
            reference_month=date.today().replace(day=1),
        )

        with patch('apps.billing.tasks.create_monthly_billing') as mock_create:
            result = charge_monthly_subscriptions()
            mock_create.assert_not_called()

        assert 'já cobrado' in result

    def test_erro_na_api_nao_interrompe_outros(self, db, user, plan_pro):
        """Erro em uma assinatura não deve impedir processamento das demais."""
        from apps.billing.tasks import charge_monthly_subscriptions
        from django.contrib.auth import get_user_model
        from dateutil.relativedelta import relativedelta

        User = get_user_model()
        today = date.today()

        # Segunda assinatura
        user2 = User.objects.create_user(email='user2_billing@test.com', password='pass123')
        sub2 = Subscription.objects.create(
            profile=user2.profile,
            plan=plan_pro,
            status=Subscription.STATUS_ACTIVE,
            abacate_billing_id='bill_sub2',
            abacate_customer_id='cust_sub2',
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
        )

        # Primeira sub levanta exceção, segunda deve ser processada
        def side_effect(sub):
            if sub.profile == user.profile:
                raise Exception('Falha simulada')
            return {
                'url': 'https://pay.com/bill2',
                'billing_id': 'bill_ok',
                'customer_id': 'cust_sub2',
            }

        # Cria sub ativa para user também
        Subscription.objects.create(
            profile=user.profile,
            plan=plan_pro,
            status=Subscription.STATUS_ACTIVE,
            abacate_billing_id='bill_user1',
            abacate_customer_id='cust_user1',
            current_period_start=today,
            current_period_end=today + relativedelta(months=1),
        )

        with patch('apps.billing.tasks.create_monthly_billing', side_effect=side_effect):
            result = charge_monthly_subscriptions()

        assert 'ERRO' in result
        assert Invoice.objects.filter(subscription=sub2).exists()


# ─── Task: cancel_overdue_subscriptions ──────────────────────────────────────

class TestCancelOverdueSubscriptions:

    def test_cancela_assinatura_inadimplente(self, db, subscription_active):
        from apps.billing.tasks import cancel_overdue_subscriptions

        subscription_active.status = Subscription.STATUS_PAST_DUE
        subscription_active.save(update_fields=['status'])
        # Simula updated_at com mais de 7 dias
        Subscription.objects.filter(pk=subscription_active.pk).update(
            updated_at=timezone.now() - timedelta(days=8)
        )

        cancel_overdue_subscriptions()

        subscription_active.refresh_from_db()
        assert subscription_active.status == Subscription.STATUS_CANCELLED

    def test_nao_cancela_inadimplente_recente(self, db, subscription_active):
        from apps.billing.tasks import cancel_overdue_subscriptions

        subscription_active.status = Subscription.STATUS_PAST_DUE
        subscription_active.save(update_fields=['status'])
        # updated_at recente — dentro dos 7 dias

        cancel_overdue_subscriptions()

        subscription_active.refresh_from_db()
        assert subscription_active.status == Subscription.STATUS_PAST_DUE

    def test_sem_inadimplentes_retorna_mensagem(self, db):
        from apps.billing.tasks import cancel_overdue_subscriptions

        result = cancel_overdue_subscriptions()
        assert result == 'Nenhum cancelamento.'