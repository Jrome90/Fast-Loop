import traceback
import functools


def respond(self, context, event=None):
    self.report({'ERROR'}, traceback.format_exc())

    if hasattr(self, 'cancel'):
        try:
            self.cancel(context)
        except:
            self.report({'ERROR'}, traceback.format_exc())

    return {'CANCELLED'}


def decorator(method):
    wraps = functools.wraps(method)

    def wrapper(*args):
        try:
            return method(*args)
        except:
            return respond(*args)

    if method.__name__ in {'invoke', 'modal'}:
        return wraps(lambda self, context, event: wrapper(self, context, event))

    elif method.__name__ == 'execute':
        return wraps(lambda self, context: wrapper(self, context))

    raise Exception('This decorator is only for invoke, modal, and execute')
