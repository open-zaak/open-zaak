from privates.views import PrivateMediaView as _PrivateMediaView


class PrivateMediaView(_PrivateMediaView):
    def get_sendfile_opts(self):
        return {
            "attachment": True,
            "attachment_filename": self.get_object().bestandsnaam,
        }
