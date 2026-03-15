from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    """
    Adapter customizado do allauth para capturar dados extras no signup:
    - IP do cadastro (anonimizado no signal)
    - Consentimento de marketing (opt-in explícito)
    """

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)

        # Passa o IP real para o signal via atributo temporário
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')

        user._signup_ip = ip

        # Passa o consentimento de marketing para o signal
        user._marketing_consent = form.data.get('marketing_consent') == '1'

        if commit:
            user.save()

        return user