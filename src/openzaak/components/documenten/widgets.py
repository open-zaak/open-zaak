from privates.widgets import PrivateFileWidget as _PrivateFileWidget


class PrivateFileWidget(_PrivateFileWidget):
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        context["widget"]["value"] = self.attrs.get("display_value")
        return context
