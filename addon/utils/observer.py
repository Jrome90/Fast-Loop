
class Subject():
    _listeners  = {}
    
    @classmethod
    def notify_listeners(cls, *args, **kwargs):
        for callback in cls._listeners.values(): 
            try:
                callback(*args, **kwargs)
            except:
                pass

    @classmethod
    def register_listener(cls, listener, callback):
        cls._listeners[listener.__class__.__name__] = callback
        return callback