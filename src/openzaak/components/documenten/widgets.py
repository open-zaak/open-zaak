from privates.widgets import PrivateFileWidget as _PrivateFileWidget


class PrivateFileWidget(_PrivateFileWidget):
    def get_display_value(self, value):
        instance = value.instance
        return instance.bestandsnaam or super().get_display_value(value)
