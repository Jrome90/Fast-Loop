from . import props
from . import ops
from . import tools
from . import ui
from . ui import gizmos 
from . import keymaps



modules = (
    props,
    ops,
    tools,
    ui,
    gizmos,
    keymaps,
)


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
