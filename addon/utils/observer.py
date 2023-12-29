
class Subject():
    _listeners  = {}
    
    @classmethod
    def notify_listeners(cls, *args, **kwargs):
        for callback in list(cls._listeners.values()): 
            try:
                callback(*args, **kwargs)
            except:
                pass

    @classmethod
    def register_listener(cls, listener, callback):
        cls._listeners[listener.__class__.__name__] = callback
        return callback
    

    @classmethod
    def unregister_listener(cls, listener):
        if listener.__class__.__name__ in cls._listeners:
            del cls._listeners[listener.__class__.__name__]
