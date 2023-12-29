from collections import namedtuple

from .. props import addon
from ..ops.fast_loop_helpers import (get_options)

AllPropsNoSnap = namedtuple('AllPropsNoSnap', ['common', 'multi_loop', 'sub'])

class BaseProps():
    @property
    def fast_loop_options(self)-> addon.FL_Options:
        return get_options()

# What would these properties be classified under?
# Need a better name
class SubProps(BaseProps):
    @property
    def insert_verts(self):
        return self.fast_loop_options.insert_verts

    @insert_verts.setter
    def insert_verts(self, value):
        self.fast_loop_options.insert_verts = value

    @property
    def insert_on_selected_edges(self):
        return self.fast_loop_options.insert_on_selected_edges

    @insert_on_selected_edges.setter
    def insert_on_selected_edges(self, value):
        self.fast_loop_options.insert_on_selected_edges = value
    
    @property
    def loop_position_override(self):
        return self.fast_loop_options.loop_position_override
    
    @loop_position_override.setter
    def loop_position_override(self, value):
        self.fast_loop_options.loop_position_override = value

    
class CommonProps(BaseProps):
    flipped = False
    @property
    def flipped(self):
        return self.fast_loop_options.flipped

    @flipped.setter
    def flipped(self, value):
        self.fast_loop_options.flipped = value

    use_even = False
    @property
    def use_even(self):
        return self.fast_loop_options.use_even
    
    @use_even.setter
    def use_even(self, value):
        self.fast_loop_options.use_even = value
    
    cancelled = False
    @property
    def cancelled(self):
        return self.fast_loop_options.cancel
    
    @cancelled.setter
    def cancelled(self, value):
        self.fast_loop_options.cancel = value 

    @property
    def mirrored(self):
        return self.fast_loop_options.mirrored
    
    @mirrored.setter
    def mirrored(self, value):
        self.fast_loop_options.mirrored = value

    # perpendicular = False
    @property
    def perpendicular(self):
        return self.fast_loop_options.perpendicular
    
    @perpendicular.setter
    def perpendicular(self, value):
        self.fast_loop_options.perpendicular = value

    @property
    def freeze_edge(self):
        return self.fast_loop_options.freeze_edge

    @freeze_edge.setter
    def freeze_edge(self, value):
        self.fast_loop_options.freeze_edge = value

    @property
    def segments(self):
        return self.fast_loop_options.segments

    @segments.setter
    def segments(self, value):
        self.fast_loop_options.segments = value

class MultiLoopProps(BaseProps):
    @property
    def scale(self):
        return self.fast_loop_options.scale
    
    @scale.setter
    def scale(self, value):
        self.fast_loop_options.scale = value

    # Used to display either distance values or scale in the HUD. 
    @property
    def loop_space_value(self):
        return self.fast_loop_options.loop_space_value
    
    @loop_space_value.setter
    def loop_space_value(self, value):
        self.fast_loop_options.loop_space_value = str(value)
    
    # use_multi_loop_offset = False
    @property
    def use_multi_loop_offset(self):
        return self.fast_loop_options.use_multi_loop_offset
    
    @use_multi_loop_offset.setter
    def use_multi_loop_offset(self, value):
        self.fast_loop_options.use_multi_loop_offset = value

class SnapProps(BaseProps):
    @property
    def use_snap_points(self):
        return self.fast_loop_options.use_snap_points
    
    @use_snap_points.setter
    def use_snap_points(self, value):
        self.fast_loop_options.use_snap_points = value

    # snap_divisions = 2
    @property
    def snap_divisions(self):
        return self.fast_loop_options.snap_divisions
    
    @snap_divisions.setter
    def snap_divisions(self, value):
       self.fast_loop_options.snap_distance = value
    
    # lock_snap_points = False
    @property
    def lock_snap_points(self):
        return self.fast_loop_options.lock_snap_points

    @lock_snap_points.setter
    def lock_snap_points(self, value):
        self.fast_loop_options.lock_snap_points = value
    
    @property
    def use_distance(self):
        return self.fast_loop_options.use_distance
        
    # @use_distance.setter
    # def use_distance(self, value):
    #     self.use_distance = value
     
    @property
    def auto_segment_count(self):
        return self.fast_loop_options.auto_segment_count

    @auto_segment_count.setter
    def auto_segment_count(self, value):
        self.fast_loop_options.auto_segment_count = value

    @property
    def snap_distance(self):
        return self.fast_loop_options.snap_distance
    
    @snap_distance.setter
    def snap_distance(self, value):
        self.fast_loop_options.snap_distance = value
    
    @property
    def snap_select_vertex(self):
        return self._snap_select_vertex
        
    @snap_select_vertex.setter
    def snap_select_vertex(self, value):
        self._snap_select_vertex = value
     
    @property
    def auto_segment_count(self):
        return self.fast_loop_options.auto_segment_count

