from rest_framework import serializers

from workflow.models import Space, User


class CurrentSpaceDefault:
    requires_context = True

    def set_context(self, serializer_field):
        # Only one MasterUser per Space (scheme)
        self._space = Space.objects.all().first()

    def __call__(self, serializer_field):
        self.set_context(serializer_field)

        return self._space


class SpaceField(serializers.HiddenField):
    def __init__(self, **kwargs):
        kwargs["default"] = CurrentSpaceDefault()
        super().__init__(**kwargs)


class CurrentOwnerDefault:
    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context["request"]
        self._owner = request.user

    def __call__(self, serializer_field):
        self.set_context(serializer_field)

        return self._owner


class OwnerField(serializers.HiddenField):
    def __init__(self, **kwargs):
        kwargs["default"] = CurrentOwnerDefault()
        super().__init__(**kwargs)
