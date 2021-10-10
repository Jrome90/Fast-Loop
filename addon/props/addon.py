import bpy
from .. import utils
from .. utils import observer as obs

name = __name__.partition('.')[0]


class AddonProps(bpy.types.PropertyGroup):
    addon: bpy.props.StringProperty(
        name='Addon',
        description='The module for this addon',
        default=name,
    )

    @property
    def prefs(self):
        return utils.common.prefs()


class Loop_Cut(bpy.types.PropertyGroup):
    def on_loopcut_value_changed(self, context):
        utils.ops.options().on_loopcut_value_changed()

    percent: bpy.props.FloatProperty(name='Percent', 
    default=0.0, 
    min=0.0, 
    max=100.0, 
    subtype='PERCENTAGE',
    update=on_loopcut_value_changed)

    distance: bpy.props.FloatProperty(name='Distance', 
    default=1.0, 
    min=0.0,
    subtype='DISTANCE',
    unit='LENGTH',
    precision=4,
    update=on_loopcut_value_changed)

    @staticmethod
    def get_method():
        return utils.common.prefs().interpolation_type


class Loop_Cut_Slot_Prop(bpy.types.PropertyGroup):
    loop_cut_slot: bpy.props.CollectionProperty(name="Loop Cut Slot", type=Loop_Cut)

class Loop_Cut_Slots_Prop(bpy.types.PropertyGroup):
    loop_cut_slots: bpy.props.CollectionProperty(name="Loop Cut Slots", type=Loop_Cut_Slot_Prop)


class FL_Props(bpy.types.PropertyGroup):
    is_running: bpy.props.BoolProperty(
        name='op running',
        description='Is the operator running',
        default=False,
        options='SKIP_SAVE'
    )

def prop_changed(self, context, prop):
        if prop == "loop_position_override":
            self.notify_listeners(prop, self.loop_position_override)

class FL_Options(obs.Subject, bpy.types.PropertyGroup):

    _listeners  = {}

    dirty: bpy.props.BoolProperty(
        name='dirty',
        description='',
        default=False,
    )

    cancel: bpy.props.BoolProperty(
        name='Cancel',
        description='Exit out of the tool',
        default=False,
    )

    def mode_changed(self, context):
        if self.mode == 'SINGLE':
            self.segments = 1
        self.notify_listeners("mode", self.mode)
            
    mode: bpy.props.EnumProperty(
        name='Mode',
        items=[ ('SINGLE', "Single", "", 2),
                ('MULTI_LOOP', "Multi Loop", "", 8),
                ('REMOVE_LOOP', "Remove Loop", "", 16),
                ('SELECT_LOOP', "Select Loop", "", 32),
                ('EDGE_SLIDE', "Edge Slide", "", 64),
        ],
        description="Mode",
        default='SINGLE',
        update=mode_changed
        )

    prev_mode: bpy.props.EnumProperty(
        name='Prev_Mode',
        items=[ ('NONE', "None", "", 0),
                ('SINGLE', "Single", "", 2),
                ('MULTI_LOOP', "Multi Loop", "", 8),
                ('REMOVE_LOOP', "Remove Loop", "", 16),
                ('SELECT_LOOP', "Select Loop", "", 32),
                ('EDGE_SLIDE', "Edge Slide", "", 64),
        ],
        description="A way to store the previous mode so that it doesnt change when undo is executed",
        default='NONE',
        )

    multi_loop_offset: bpy.props.BoolProperty(
        name='Multi Loop Offset',
        description='Offset the multi loop',
        default=False,
    )

    insert_midpoint: bpy.props.BoolProperty(
        name='Midpoint Insert',
        description='Insert loops at the midpoint of the edge',
        default=False,
    )

    mirrored: bpy.props.BoolProperty(
        name='Mirrored',
        description='Insert loops mirrored about the midpoint of the edge',
        default=False,
    )

    perpendicular: bpy.props.BoolProperty(
        name='Perpendicular',
        description='Insert loops perpendicular to the edge',
        default=False,
    )

    loop_position_override: bpy.props.BoolProperty(
        name='Loop Position Override',
        description='Override the positions of the inserted loops using the list below',
        default=False,
        update = lambda s, c: prop_changed(s, c, "loop_position_override")
    )

    def segments_changed(self, context):
        scene = context.scene
        scene = bpy.context.scene
        scene.Loop_Cut_Lookup_Index = utils.math.clamp(0,self.segments-1, 8)

    segments: bpy.props.IntProperty(
        name='Segments',
        description='Number segments',
        default=1,
        soft_max=10,
        min=1,
        max=100,
        update=segments_changed
    )

    scale: bpy.props.FloatProperty(
        name='Scale',
        description='Multi Loop Scale',
        min=0.0,
        max=1.0,
        default=0.5,
    )
    
    def property_changed(self, context):
        self.dirty = True
    
    flipped: bpy.props.BoolProperty(
        name='Flipped',
        description='True or False',
        default=False,
        update=property_changed
    )

    use_even: bpy.props.BoolProperty(
        name='Even',
        description='',
        default=False,
        update=property_changed
    )

    use_snap_points: bpy.props.BoolProperty(
        name='Increment Snapping',
        description='Snap to points that evenly divide the edge',
        default=False,
        update=property_changed
    )

    lock_snap_points: bpy.props.BoolProperty(
        name='Lock snap points',
        description='Lock the snapping points to the current edge',
        default=False,
        update=property_changed
    )

    snap_divisions: bpy.props.IntProperty(
        name='Snap Divisions',
        description='Number of snap point divisions',
        default=2,
        soft_max=10,
        min=1,
        max=100,
        update=property_changed
    )

    snap_factor: bpy.props.FloatProperty(
        name='Factor',
        description='Used when the number of snap divisions is one',
        min=0.0,
        max=100.0,
        default=50.0,
        subtype='PERCENTAGE',
        update=property_changed
    )

    def on_loopcut_value_changed(self):       
        self.notify_listeners("loopcut_value_changed", None)

from .. keymaps.modal_keymapping import ModalKeymap
class ModalKeymapDisplay(bpy.types.PropertyGroup):

    even: bpy.props.StringProperty(name="even")
    flip: bpy.props.StringProperty(name="flip")
    midpoint: bpy.props.StringProperty(name="midpoint")
    mirrored: bpy.props.StringProperty(name="mirrored")
    perpendicular: bpy.props.StringProperty(name="perpendicular")
    select_new_loops: bpy.props.StringProperty(name="select new loops")
    multi_loop_offset: bpy.props.StringProperty(name="multi loop offset")
    scale: bpy.props.StringProperty(name="scale")
    snap_points: bpy.props.StringProperty(name="snap points")
    lock_snap_points: bpy.props.StringProperty(name="lock snap points")
    freeze_edge: bpy.props.StringProperty(name="freeze edge")
    increase_loop_count: bpy.props.StringProperty(name="increase loop count")
    decrease_loop_count: bpy.props.StringProperty(name="decrease loop count")

    def init(self, keymap: ModalKeymap):
        for attribute in self.__annotations__.keys():
            for key, item in keymap.get_all_mappings():
                if attribute == item:
                    hotkey = self.append_modifier_keys(key[0], key[2], key[3], key[4])
                    setattr(self, attribute, hotkey)
                    break
                
    @staticmethod
    def append_modifier_keys(key_string, ctrl, shift, alt):
        if ctrl:
            key_string += "+Ctrl"
        if shift:
            key_string += "+Shift"
        if alt:
            key_string += "+Alt"
        return key_string
        
        