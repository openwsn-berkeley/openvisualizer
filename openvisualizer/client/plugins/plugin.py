from __future__ import print_function

from openvisualizer.client.view import View


class Plugin(object):
    views = {}

    @classmethod
    def record_view(cls, view_id):
        """Decorator to record all the supported views dynamically"""

        def decorator(the_class):
            if not issubclass(the_class, View):
                raise ValueError("Can only decorate subclass of View")
            cls.views[view_id] = the_class
            return the_class

        return decorator
