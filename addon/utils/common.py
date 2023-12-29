import bpy

from .. import props


def module():
    return props.addon.name


def prefs():
    return bpy.context.preferences.addons[module()].preferences


def set_addon_preference(option, value)-> bool:
    if hasattr(prefs(), option):
        setattr(prefs(), option, value)
        return True
    return False


def sanitize(text: str):
    return ''.join('_' if c in ':*?"<>|' else c for c in text)

def addon_path():
    return props.addon.path + module() + "\\"
    # for mod in addon_utils.modules():
    #     if mod.bl_info.get("name") == "Fast Loop":
    #         print(mod.__file__)

    #         return mod.__file__

