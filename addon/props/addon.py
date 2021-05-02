import bpy
from .. import utils


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


class FL_Props(bpy.types.PropertyGroup):
    is_running: bpy.props.BoolProperty(
        name='op running',
        description='Is the operator running',
        default=False,
    )

    is_sliding: bpy.props.BoolProperty(
        name='is sliding',
        description='Is the operator running',
        default=False,
    )
    

class FL_Options(bpy.types.PropertyGroup):

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

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[ ('SINGLE', "Single", "", 2),
                ('MIRRORED', "Mirrored", "" , 4),
                ('MULTI_LOOP', "Multi Loop", "", 8),
                ('REMOVE_LOOP', "Remove Loop", "", 16),
                ('SELECT_LOOP', "Select Loop", "", 32),
                ('EDGE_SLIDE', "Edge Slide", "", 64),
        ],
        description="Mode",
        default='SINGLE'
        )

    insert_midpoint: bpy.props.BoolProperty(
        name='Midpoint Insert',
        description='Insert loops at the midpoint of the edge',
        default=False,
    )

    multi_loop_offset: bpy.props.BoolProperty(
        name='Multi Loop Offset',
        description='Offset the multi loop',
        default=False,
    )

    segments: bpy.props.IntProperty(
        name='Segments',
        description='Number segments when multi loop is active',
        default=3,
        soft_max=10,
        min=2,
        max=100,
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
    
