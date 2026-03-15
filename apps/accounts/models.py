import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from core.models import BaseModel


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser precisa ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser precisa ter is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        return self.email


class Profile(BaseModel):
    PLAN_FREE = 'free'
    PLAN_PRO = 'pro'
    PLAN_CHOICES = [
        (PLAN_FREE, 'Free'),
        (PLAN_PRO, 'Pro'),
    ]

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    slug = models.SlugField(max_length=60, unique=True, db_index=True)
    display_name = models.CharField(max_length=80, blank=True)
    bio = models.CharField(max_length=160, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default=PLAN_FREE)
    custom_domain = models.CharField(max_length=255, blank=True, null=True, unique=True)

    # Campos para billing (AbacatePay)
    cpf = models.CharField(max_length=14, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    # ── Dados LGPD coletados no cadastro ─────────────────────────────────────
    # Base legal: execução de contrato (Art. 7º V) + consentimento (Art. 7º I)

    # IP anonimizado no cadastro — segurança e prevenção de fraude
    # Base legal: interesse legítimo (Art. 7º IX)
    signup_ip = models.CharField(max_length=45, blank=True)

    # Consentimento explícito para email marketing
    # Base legal: consentimento (Art. 7º I) — opt-in no formulário de cadastro
    marketing_consent = models.BooleanField(default=False)
    marketing_consent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'

    def __str__(self):
        return f'{self.slug} ({self.plan})'

    @property
    def is_pro(self):
        """
        Verifica se o usuário tem plano Pro com assinatura ativa.
        Usa a subscription se existir, senão cai no campo plan como fallback.
        """
        try:
            return self.subscription.is_active
        except Exception:
            return self.plan == self.PLAN_PRO