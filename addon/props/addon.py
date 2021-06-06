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
    percent: bpy.props.FloatProperty(name='Percent', 
    default=0.0, 
    min=0.0, 
    max=100.0, 
    subtype='PERCENTAGE')

    distance: bpy.props.FloatProperty(name='Distance', 
    default=1.0, 
    min=0.0,
    subtype='DISTANCE',
    unit='LENGTH',
    precision=4)

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
        default=True,
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

    select_new_edges: bpy.props.BoolProperty(
        name='Select Edge Loops',
        description='Select the newly created edge loops',
        default=False,
    )

    def segments_changed(self, context):
        scene = context.scene
        scene = bpy.context.scene
        scene.Loop_Cut_Lookup_Index = self.segments-1

    segments: bpy.props.IntProperty(
        name='Segments',
        description='Number segments when multi loop is active',
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
    
