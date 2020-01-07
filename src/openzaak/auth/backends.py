from django_auth_adfs.backend import AdfsAuthCodeBackend

from .models import ADFSConfig


class ADFSBackend(AdfsAuthCodeBackend):
    """
    Config driven ADFS Auth backend.

    Checks the 'enabled' flag of the ADFSConfig before actually running the
    auth flow, causing this backend to be skipped if it's not enabled in the
    admin.
    """

    def authenticate(self, *args, **kwargs):
        config = ADFSConfig.get_solo()
        if not config.enabled:
            return None

        return super().authenticate(*args, **kwargs)
