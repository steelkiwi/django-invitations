import json

from allauth.account.adapter import get_adapter
from braces.views import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.views.generic import FormView, View
from django.views.generic.detail import SingleObjectMixin

from .app_settings import app_settings
from .exceptions import AlreadyInvited, AlreadyAccepted
from .forms import InviteForm, CleanEmailMixin
from .models import Invitation


class SendInvite(LoginRequiredMixin, FormView):
    template_name = 'invitations/forms/_invite.html'
    form_class = InviteForm

    def form_valid(self, form):
        email = form.cleaned_data["email"]

        try:
            invite = form.save(email)
            invite.send_invitation(self.request)
        except Exception:
            return self.form_invalid(form)

        return self.render_to_response(
            self.get_context_data(
                success_message='%s has been invited' % email))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class SendJSONInvite(LoginRequiredMixin, View):
    http_method_names = [u'post']

    def dispatch(self, request, *args, **kwargs):
        if app_settings.ALLOW_JSON_INVITES:
            return super(SendJSONInvite, self).dispatch(
                request, *args, **kwargs)
        else:
            raise Http404

    def post(self, request, *args, **kwargs):
        status_code = 400
        invitees = json.loads(request.body.decode())
        response = {'valid': [], 'invalid': []}
        if isinstance(invitees, list):
            for invitee in invitees:
                try:
                    validate_email(invitee)
                    CleanEmailMixin().validate_invitation(invitee)
                    invite = Invitation.create(invitee)
                except(ValueError, KeyError):
                    pass
                except(ValidationError):
                    response['invalid'].append({
                        invitee: 'invalid email'})
                except(AlreadyAccepted):
                    response['invalid'].append({
                        invitee: 'already accepted'})
                except(AlreadyInvited):
                    response['invalid'].append(
                        {invitee: 'pending invite'})
                else:
                    invite.send_invitation(request)
                    response['valid'].append({invitee: 'invited'})

        if response['valid']:
            status_code = 201

        return HttpResponse(
            json.dumps(response),
            status=status_code, content_type='application/json')


class AcceptInvite(SingleObjectMixin, View):
    form_class = InviteForm

    def get(self, *args, **kwargs):
        if app_settings.CONFIRM_INVITE_ON_GET:
            return self.post(*args, **kwargs)
        else:
            raise Http404()

    def post(self, *args, **kwargs):
        self.object = invitation = self.get_object()

        get_adapter().stash_verified_email(self.request, invitation.email)
        get_adapter().stash_invitation(self.request, invitation.id)

        return redirect(app_settings.SIGNUP_REDIRECT)

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        try:
            return queryset.get(key=self.kwargs["key"].lower())
        except Invitation.DoesNotExist:
            raise Http404()

    def get_queryset(self):
        return Invitation.objects.all_valid()
