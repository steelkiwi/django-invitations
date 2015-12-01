class AppSettings(object):

    def __init__(self, prefix):
        self.prefix = prefix

    def _setting(self, name, dflt):
        from django.conf import settings
        return getattr(settings, self.prefix + name, dflt)

    @property
    def INVITATION_EXPIRY(self):
        """ How long before the invitation expires """
        return self._setting('INVITATION_EXPIRY', 3)

    @property
    def INVITATION_ONLY(self):
        """ Signup is invite only """
        return self._setting('INVITATION_ONLY', False)

    @property
    def CONFIRM_INVITE_ON_GET(self):
        """ Simple get request confirms invite """
        return self._setting('CONFIRM_INVITE_ON_GET', True)

    @property
    def ALLOW_JSON_INVITES(self):
        """ Exposes json endpoint for mass invite creation """
        return self._setting('ALLOW_JSON_INVITES', False)

    @property
    def SIGNUP_REDIRECT(self):
        """ Where to redirect on email confirm of invite """
        return self._setting('SIGNUP_REDIRECT', 'account_signup')

    @property
    def ADAPTER(self):
        """ The adapter, setting ACCOUNT_ADAPTER overrides this default """
        return self._setting(
            'ADAPTER', 'invitations.adapters.BaseInvitationsAdapter')

app_settings = AppSettings('INVITATIONS_')
