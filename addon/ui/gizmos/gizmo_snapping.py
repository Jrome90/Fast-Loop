from functools import partial
from ....signalslot.signalslot import Signal

import bpy
from bpy.types import GizmoGroup

from ... import utils

def get_props():
    return utils.ops.fl_props()


class RP_GGT_SnapGizmoGroup(GizmoGroup):
    
    bl_idname = "fl.snap_gizmo_group"
    bl_label = "Edit pivot GG"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}

    on_snap_update = Signal(args=['[snap_location]'])

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.snap_gizmo = None


    @classmethod
    def poll(cls, context):
        return True
  

    def setup(self, context):
        self.snap_gizmo = self.gizmos.new("GIZMO_GT_snap_3d")
        


    def draw_prepare(self, context):
        if self.snap_gizmo is not None:
            index, elem_type = get_element_type_and_index(self.snap_gizmo.snap_elem_index)
            snap_location = self.snap_gizmo.location
            if snap_location is not None and elem_type is not None:
                self.on_snap_update.emit(snap_location=snap_location)


def is_snap_data_changed(context, element_type, element_index)-> bool:
    window_manager = context.window_manager
    shared_snap_data = window_manager.Shared_Snap_Data

    if shared_snap_data.element_type != "NONE" or element_type != "NONE":
        return True
    return False


def get_element_type_and_index(elem_type):
    if all(e == 0 for e in elem_type):
        return -1, "NONE"

    if elem_type[0] != -1:
        return elem_type[0], "VERTEX"
    elif elem_type[1] != -1:
        return elem_type[1], "EDGE"
    elif elem_type[2] != -1:
        return elem_type[2], "FACE"
    
    return -1, "NONE"
        

# def get_active_snap_elements(context):
#     snap_elements: set = context.tool_settings.snap_elements
#     invalid: set = {"INCREMENT", "EDGE", "VOLUME", "EDGE_PERPENDICULAR"}

#     snap_elements.difference_update(invalid)

#     return snap_elements