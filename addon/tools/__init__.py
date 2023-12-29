import bpy
from . import fast_loop

tools = {
            fast_loop.FL_FastLoop: ("builtin.poly_build", False, False),
        }

def register():
    for tool, (after, separated, grouped) in tools.items():

        bpy.utils.register_tool(tool, after=after, separator=separated, group=grouped)

def unregister():
    for tool in reversed(list(tools.keys())):
        bpy.utils.unregister_tool(tool)
