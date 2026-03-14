from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect


class PlanRequiredMixin(LoginRequiredMixin):
    """
    Mixin para views que exigem plano Pro.
    Redireciona usuários Free para a página de pricing.

    Uso:
        class MinhaView(PlanRequiredMixin, View):
            ...
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        profile = request.user.profile
        if not profile.is_pro:
            messages.warning(
                request,
                'Este recurso está disponível apenas no plano Pro. '
                'Faça upgrade para continuar.'
            )
            return redirect('billing:pricing')

        return super().dispatch(request, *args, **kwargs)