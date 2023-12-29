from functools import partial

import bpy
from bpy.types import GizmoGroup

from ... import utils

def get_props():
    return utils.ops.fl_props()

def execute_update_shared_snap_data(element_index, element_type, location):

    window_manager = bpy.context.window_manager
    shared_snap_data = window_manager.Shared_Snap_Data
    shared_snap_data.element_index = element_index
    shared_snap_data.element_type = element_type
    if location is not None and element_index is not None:
        shared_snap_data.location = location
        shared_snap_data.is_snapping = True
    else:
        shared_snap_data.is_snapping = False
    shared_snap_data.use_context = True

    #Trigger an update event
    shared_snap_data.updated = True

class RP_GGT_SnapGizmoGroup(GizmoGroup):
    
    bl_idname = "fl.snap_gizmo_group"
    bl_label = "Edit pivot GG"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D'}


    def __init__(self) -> None:
        super().__init__()

        self.snap_gizmo = None
        self.highlight = None

    @classmethod
    def poll(cls, context):
        return True
  
    def setup(self, context):
        window_manager = bpy.context.window_manager
        shared_snap_data = window_manager.Shared_Snap_Data
        shared_snap_data.element_index = -1
        shared_snap_data.element_type = 'NONE'
        shared_snap_data.location = (0,0,0)
        shared_snap_data.is_snapping = False
        shared_snap_data.use_context = False
        self.snap_gizmo = self.gizmos.new("GIZMO_GT_snap_3d")
        

    def invoke_prepare(self, context, gizmo):
        pass

    
    def refresh(self, context):
        pass


    def draw_prepare(self, context):
        if self.snap_gizmo is not None:
            index, elem_type = get_element_type_and_index(self.snap_gizmo.snap_elem_index)
            update_shared_snap_data(index, elem_type, self.snap_gizmo.location)

def is_snap_data_changed(context, element_type, element_index)-> bool:
    window_manager = context.window_manager
    shared_snap_data = window_manager.Shared_Snap_Data

    if shared_snap_data.element_type != "NONE" or element_type != "NONE":
        return True
    return False

def update_shared_snap_data(element_index, element_type, location):
    bpy.app.timers.register(partial(execute_update_shared_snap_data, element_index, element_type, location), first_interval=0.01)


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