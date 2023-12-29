from typing import *
from dataclasses import dataclass

import bmesh
from bpy.types import Object, Context
from bmesh.types import BMesh
from mathutils import Matrix

@dataclass
class EditObjectData():
    _bl_object: Object = None
    bm: BMesh = None
    world_matrix: Matrix = None
    inv_world_matrix: Matrix = None

    @property
    def name(self):
        return self._bl_object.data.name
    
    @property
    def data(self):
        return self._bl_object.data
    
    @property
    def get_bl_object(self):
        return self._bl_object
    

class MultiObjectEditing():
    """Mixin Do not instantiate this class."""

    active_object: EditObjectData = None
    selected_editable_objects: Dict[str, EditObjectData] = {}

    _world_mat: Matrix = None
    @property
    def world_mat(self):
        return self.active_object.world_matrix
    
    @world_mat.setter
    def world_mat(self, value):
       self.active_object.world_matrix = value

    _world_inv: Matrix = None
    @property
    def world_inv(self):
        return self.active_object.inv_world_matrix
    
    @world_inv.setter
    def world_inv(self, value):
       self.active_object.inv_world_matrix = value

    
    def add_selected_editable_objects(self, context: Context):
        objects = context.selected_editable_objects
        for obj in objects:
            if not obj.type in {'MESH'}:
                continue
                
            obj_name = obj.name
            if obj.mode not in {'EDIT'}:
                if obj.name in self.selected_editable_objects:
                    del self.selected_editable_objects[obj.data.name]

            obj.update_from_editmode()
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)

            world_matrix = obj.matrix_world
            inv_world_matrix = obj.matrix_world.inverted_safe()
            self.selected_editable_objects[obj_name] = EditObjectData(obj, bm, world_matrix, inv_world_matrix)