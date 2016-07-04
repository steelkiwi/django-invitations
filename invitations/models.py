import datetime

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.adapter import get_adapter
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from . import signals
from .app_settings import app_settings
from .managers import InvitationManager


@python_2_unicode_compatible
class Invitation(models.Model):
    DEFAULT, GROUP = range(2)
    INVITATION_TYPES = (
        (DEFAULT, _('Default')),
        (GROUP, _('Group'))
    )

    email = models.EmailField(unique=False, verbose_name=_('e-mail address'))
    accepted = models.BooleanField(verbose_name=_('accepted'), default=False)
    created = models.DateTimeField(verbose_name=_('created'),
                                   default=timezone.now)
    key = models.CharField(verbose_name=_('key'), max_length=64, unique=True)
    sent = models.DateTimeField(verbose_name=_('sent'), null=True)
    inviter = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True)
    invitation_type = models.PositiveSmallIntegerField(choices=INVITATION_TYPES, default=DEFAULT)
    subject_id = models.IntegerField(blank=True, null=True)

    objects = InvitationManager()

    @classmethod
    def create(cls, email, inviter=None):
        key = get_random_string(64).lower()
        instance = cls._default_manager.create(
            email=email,
            key=key,
            inviter=inviter)
        return instance

    def key_expired(self):
        expiration_date = (
            self.sent + datetime.timedelta(
                days=app_settings.INVITATION_EXPIRY))
        return expiration_date <= timezone.now()

    def send_invitation(self, request, **kwargs):
        current_site = (kwargs['site'] if 'site' in kwargs
                        else Site.objects.get_current())
        invite_url = reverse('invitations:accept-invite',
                             args=[self.key])
        invite_url = request.build_absolute_uri(invite_url)

        ctx = {
            'invite_url': invite_url,
            'site_name': current_site.name,
            'email': self.email,
            'key': self.key,
            'inviter': self.inviter,
        }

        email_template = 'invitations/email/email_invite'

        get_adapter().send_mail(
            email_template,
            self.email,
            ctx)
        self.sent = timezone.now()
        self.save()

        signals.invite_url_sent.send(
            sender=self.__class__,
            instance=self,
            invite_url_sent=invite_url,
            inviter=request.user)

    def __str__(self):
        return "Invite: {0} by {1}".format(self.email, self.inviter)


class InvitationsAdapter(DefaultAccountAdapter):

    def is_open_for_signup(self, request):
        if hasattr(request, 'session') and request.session.get(
                'account_verified_email'):
            return True
        elif app_settings.INVITATION_ONLY is True:
            # Site is ONLY open for invites
            return False
        else:
            # Site is open to signup
            return True

    def stash_invitation(self, request, invitation_id):
        request.session['invitation'] = invitation_id

    def unstash_invitation(self, request):
        ret = request.session.get('invitation')
        request.session['invitation'] = None
        return ret
