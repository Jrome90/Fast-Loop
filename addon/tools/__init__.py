import bpy
from . import fast_loop
from . import fast_loop_classic

tools = {   fast_loop_classic.FL_FastLoopClassic: ("builtin.poly_build", True, True),
            fast_loop.FL_FastLoop: ("fl.fast_loop_classic_tool", False, False),
        }

def register():
    for tool, (after, separated, grouped) in tools.items():

        bpy.utils.register_tool(tool, after=after, separator=separated, group=grouped)

def unregister():
    for tool in reversed(list(tools.keys())):
        bpy.utils.unregister_tool(tool)
