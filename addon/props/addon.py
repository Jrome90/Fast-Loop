import bpy
from .. import utils
from .. utils import observer as obs

name = __name__.partition('.')[0]
path = __file__.partition('Fast Loop')[0]

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
    #TODO: Dont go through fl_options to update the loop cut values
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

    @staticmethod
    def setup(context):
        window_manager = context.window_manager
        slots = window_manager.Loop_Cut_Slots.loop_cut_slots

        unit_settings = bpy.context.scene.unit_settings
        unit_scale = unit_settings.scale_length
        length_unit = unit_settings.length_unit

        if len(slots.keys()) == 0:
            for i in range(9):
                slot = slots.add()
                for j in range(i+1):
                    percent = ((1.0 + j) / ( (i+1) + 1.0))
                    prop = slot.loop_cut_slot.add()
                    prop.percent = percent * 100
                    
                    if length_unit == "METERS":
                        prop.distance = (j + 1) * utils.math.cm_to_meters(10)
                    elif length_unit == "CENTIMETERS":
                        prop.distance = (j + 1) * utils.math.cm_to_meters(1)
                    elif length_unit == "MILLIMETERS":
                        prop.distance = (j + 1) * utils.math.mm_to_meters(1)
                    elif length_unit == "KILOMETERS":
                        prop.distance = (j + 1) * 0.1
                    else:
                        prop.distance = (j + 1)
                        
    @staticmethod
    def reset_active(context):
        unit_settings = bpy.context.scene.unit_settings
        unit_scale = unit_settings.scale_length
        length_unit = unit_settings.length_unit

        window_manager = context.window_manager
        slots = window_manager.Loop_Cut_Slots.loop_cut_slots
        index = window_manager.Loop_Cut_Lookup_Index
        slot = slots[index]
        for i, loop_cut in enumerate(slot.loop_cut_slot.values()):
            if loop_cut.get_method() == 'PERCENT':
                percent = ((1.0 + i) / ( (len(slot.loop_cut_slot.values())) + 1.0))
                loop_cut.percent = percent * 100
            else:
                if length_unit == "METERS":
                    loop_cut.distance = (i + 1) * utils.math.cm_to_meters(10)
                elif length_unit == "CENTIMETERS":
                    loop_cut.distance = (i + 1) * utils.math.cm_to_meters(1)
                elif length_unit == "MILLIMETERS":
                    loop_cut.distance = (i + 1) * utils.math.mm_to_meters(1)
                elif length_unit == "KILOMETERS":
                    loop_cut.distance = (i + 1) * 0.1
                else:
                    loop_cut.distance = (i + 1)


class SharedSnapData(bpy.types.PropertyGroup):

    def on_snap_data_update(self, context):
        if self.updated:
            if self.is_snapping:
                utils.ops.options().on_snap_data_update(self.location, self.use_context)
            else:
                utils.ops.options().on_snap_data_update(None, self.use_context)
            self.updated = False

  
    updated: bpy.props.BoolProperty(
        name='Snap Data Updated',
        description='Set to True to trigger an update event',
        default=False,
        update=on_snap_data_update,
        options={'SKIP_SAVE'}

    )

    use_context: bpy.props.BoolProperty(
        name='Use Context',
        description='Send context data to listener if set to True',
        default=False,
        options={'SKIP_SAVE'}

    )

    element_type: bpy.props.EnumProperty(
        name='Element Type',
        items=[
        ('VERTEX', "Vertex", "", 1),
        ('EDGE', "Edge", "", 2),
        ('FACE', "Face", "", 3),
        ('NONE', "None", "", 4),
        ],
        default= 'NONE',
        description='Type of element being snapped to',
        options={'SKIP_SAVE'}

    )

    element_index: bpy.props.IntProperty(
        name='Element Index',
        description='Index of the element being snapped to',
        default=-1,
        options={'SKIP_SAVE'}


    )
    
    location: bpy.props.FloatVectorProperty(
        name='Snap Location',
        description='Location of point being snapped to',
        subtype='XYZ',
        options={'SKIP_SAVE'}

    )

    is_snapping: bpy.props.BoolProperty(
        name='Is Snapping',
        description='Is a point being snapped to',
        default = False,
        options={'SKIP_SAVE'}
    )


class FL_Props(bpy.types.PropertyGroup):
    is_running: bpy.props.BoolProperty(
        name='op running',
        description='Is the operator running',
        default=False,
        options={'SKIP_SAVE'}
    )

    prompted: bpy.props.BoolProperty(
        name='prompted',
        description='',
        default=False,
        options={'SKIP_SAVE'}
    )


def property_changed2(self, context, prop, val):
    self.dirty = True
    self.notify_listeners(prop, val)


def snap_side_left_changed(self, context, val):
    if val:
        self.snap_right = False    

def snap_side_right_changed(self, context, val):
    if val: 
        self.snap_left = False

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

    def segments_changed(self, context):
        window_manager = context.window_manager
        window_manager.Loop_Cut_Lookup_Index = utils.math.clamp(0,self.segments-1, 8)

    segments: bpy.props.IntProperty(
        name='Segments',
        description='Number of segments.',
        default=1,
        soft_max=10,
        min=1,
        max=100,
        update=segments_changed
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

    # insert_midpoint: bpy.props.BoolProperty(
    #     name='Midpoint Insert',
    #     description='Insert loops at the midpoint of the edge',
    #     default=False,
    # )
    
    loop_position_override: bpy.props.BoolProperty(
        name='Loop Position Override',
        description='Override the positions of the inserted loops using the list below',
        default=False,
        options={'SKIP_SAVE'},
        update=lambda s, c: property_changed2(s, c, "loop_position_override", s.loop_position_override)
    )
    
    def property_changed(self, context):
        self.dirty = True

    use_even: bpy.props.BoolProperty(
        name='Even',
        description='Match the adjacent edge\'s shape.\nUse Flip to change what adjacent edge is used.',
        default=False,
        options={'SKIP_SAVE'},
        update=lambda s, c: property_changed2(s, c, "use_even", s.use_even)
    )
    
    flipped: bpy.props.BoolProperty(
        name='Flip',
        description='True or False.',
        default=False,
        options={'SKIP_SAVE'},
        update=lambda s, c: property_changed2(s, c, "flipped", s.flipped)
    )

    mirrored: bpy.props.BoolProperty(
        name='Mirrored',
        description='Insert loops mirrored about the midpoint of the active edge.',
        default=False,
        options={'SKIP_SAVE'},

        update=lambda s, c: property_changed2(s, c, "mirrored", s.mirrored)
    )

    perpendicular: bpy.props.BoolProperty(
        name='Perpendicular',
        description='Insert loops perpendicular to the active edge. ',
        default=False,
        options={'SKIP_SAVE'},
        update=lambda s, c: property_changed2(s, c, "perpendicular", s.perpendicular)
    )

    use_multi_loop_offset: bpy.props.BoolProperty(
        name='Multi Loop Offset',
        description='Offset the loops to start at the cursor.',
        default=False,
        options={'SKIP_SAVE'},
        update=lambda s, c: property_changed2(s, c, "use_multi_loop_offset", s.use_multi_loop_offset)

    )

    scale: bpy.props.FloatProperty(
        name='Scale',
        description='Value to scale multiple loops by.',
        min=0.0,
        max=1.0,
        default=0.5,
        options={'SKIP_SAVE'},
        update=lambda s, c: property_changed2(s, c, "scale", s.scale)
    )
    
    loop_space_value: bpy.props.StringProperty(
        name='Loop Space Value',
        options={'SKIP_SAVE'},
        default='50 %',
        description='Used to display the value of the spacing between loops in the HUD.',
        update=lambda s, c: property_changed2(s, c, "loop_space_value", s.loop_space_value)
    )

    insert_verts: bpy.props.BoolProperty(
        name='Insert Verts',
        description='Insert vertices on the active edge.',
        default=False,
        update=lambda s, c: property_changed2(s, c, "insert_verts", s.insert_verts)
    )

    insert_on_selected_edges: bpy.props.BoolProperty(
        name='Use Selected Edges',
        description='Select edges to guide the loop\'s direction',
        default=False,
        update=lambda s, c: property_changed2(s, c, "insert_on_selected_edges", s.insert_on_selected_edges)
    )

    freeze_edge: bpy.props.BoolProperty(
        name='Freeze Edge',
        description='Freeze the active edge to prevent it from changing when moving the cursor.',
        default=False,
        update=lambda s, c: property_changed2(s, c, "freeze_edge", s.freeze_edge)
    )

    use_snap_points: bpy.props.BoolProperty(
        name='Snap Points',
        description='Snap to points along the active edge.',
        default=False,
        update=lambda s, c: property_changed2(s, c, "use_snap_points", s.use_snap_points)
    )

    lock_snap_points: bpy.props.BoolProperty(
        name='Lock Snap Points',
        description='Lock the snapping points to the active edge.\nThis keeps the points from changing after loop(s) are inserted',
        default=False,
        update=lambda s, c: property_changed2(s, c, "lock_snap_points", s.lock_snap_points)
    )

    snap_divisions: bpy.props.IntProperty(
        name='Snap Divisions',
        description='Number of snap point divisions',
        default=1,
        soft_max=10,
        min=1,
        max=100,
        update=property_changed
    )

    # snap_factor: bpy.props.FloatProperty(
    #     name='Factor',
    #     description='Used when the number of snap divisions is one',
    #     min=0.0,
    #     max=100.0,
    #     default=50.0,
    #     subtype='PERCENTAGE',
    #     update=property_changed
    # )

    snap_distance: bpy.props.FloatProperty(
        name='Distance',
        description='Distance between snap points',
        default=0.0273, 
        min=0.001,
        subtype='DISTANCE',
        unit='LENGTH',
        precision=4,
        update=property_changed
    )

    use_opposite_snap_dist: bpy.props.BoolProperty(
        name='Use Opposite Snap Distance',
        description='Calculate snap distance from the opposite end.',
        default=False,
    )

    use_distance: bpy.props.BoolProperty(
        name='Use Distance',
        description='Space the snapping points by the specified distance',
        default=True,
        update=property_changed
    )

    auto_segment_count: bpy.props.BoolProperty(
        name='Auto',
        description='Calculate the number of segments based on the distance of the spacing and the edge length. \n \
                    E.g. A length of 1m and 10cm spacing will result in having a snap point every 10cm',
        default=False,
        update=property_changed
    )

    # snap_side: bpy.props.EnumProperty(
    #     name='Snap Side',
    #     items=[ ('LEFT', "Left", "", 2),
    #             ('CENTER', "Center", "", 8),
    #             ('RIGHT', "Right", "", 16),
    #     ],
    #     description="Side",
    #     default='LEFT',
    #     # update=mode_changed
    #     )

    ignore_left_update: bpy.props.BoolProperty(
        name='ignore_left_update',
        description='INTERNAL',
        default=False,
    )

    ignore_right_update: bpy.props.BoolProperty(
        name='ignore_right_update',
        description='INTERNAL',
        default=False,
    )

    snap_left: bpy.props.BoolProperty(
        name='Snap Left',
        description='Side',
        default=True,
        update=lambda s, c: snap_side_left_changed(s, c, s.snap_left)
    )

    snap_right: bpy.props.BoolProperty(
        name='Snap Right',
        description='Side',
        default=False,
        update=lambda s, c: snap_side_right_changed(s, c, s.snap_right)
    )

    snap_center: bpy.props.BoolProperty(
        name='Snap Center',
        description='Center',
        default=False,
    )


    def on_loopcut_value_changed(self):       
        self.notify_listeners("loopcut_value_changed", None)

    
    def on_snap_data_update(self, location, use_context):
        context = None
        if use_context:
            context = utils.ops.get_context_overrides(bpy.context.selected_editable_objects)
        self.notify_listeners("snap_gizmo_update", location, context)

    def reset_to_defaults(self):
        for attribute in self.bl_rna.properties.keys():
            if attribute not in {'rna_type', 'name', 'dirty', 'cancel', 'snap_divisions', 'snap_factor', 'snap_distance', 
                                'use_distance', 'auto_segment_count', 'panel_locked', 'snap_left', 'snap_center', 'snap_right'}:
                if hasattr(self, attribute):
                    default_value =  self.bl_rna.properties[attribute].default
                    setattr(self, attribute, default_value)


def prop_changed_ls(self, context, prop, value):
    if self.skip_notify:
        self.skip_notify = False
        return

    self.notify_listeners(prop, value)

# def active_index_changed(self, context, value):
#     if self.skip_notify:
#         self.skip_notify = False
#         return

#     self.notify_listeners(prop, value)

from ...signalslot.signalslot import Signal
class LoopSlice_Options(obs.Subject, bpy.types.PropertyGroup):

    _listeners  = {}

    skip_notify: bpy.props.BoolProperty(
        name='skip_notify',
        description='Flag to prevent notifying listeners',
        default=False,
    )

    def edit_mode_changed(self, context):
        default =  self.bl_rna.properties['edit_mode'].default
        default_value = self.bl_rna.properties['edit_mode'].enum_items[default].value
        value = self.get("edit_mode", default_value)
        self.notify_listeners("edit_mode", value)
  
    edit_mode: bpy.props.EnumProperty(
        name='Edit Mode',
        items=[ ('MOVE', "Move", "", 0),
                ('ADD', "Add", "", 1),
                ('REMOVE', "Remove", "", 2),
        ],
        description="Edit Mode",
        default='MOVE',
        update=edit_mode_changed
        )

    on_mode_changed = Signal(args=["mode"])
    on_active_index_changed = Signal(args=["index"])
    on_slice_count_changed = Signal(args=["value"])
    on_active_value_changed = Signal(args=["value"])
    on_split_changed = Signal(args=["value"])
    on_cap_sections_changed = Signal(args=["value"])
    on_gap_distance_changed = Signal(args=["value"])

    def on_get_mode(self):
        default =  self.bl_rna.properties['mode'].default
        default_value = self.bl_rna.properties['mode'].enum_items[default].value
        value = self.get("mode", default_value)

        return value
            
    mode: bpy.props.EnumProperty(
        name='Mode',
        items=[ ('FREE', "Free", "", 0),
                ('UNIFORM', "Uniform", "", 1),
                ('SYMMETRY', "Symmetry", "", 2),
              ],
        description="Mode",
        default='FREE',
        update=lambda s, c: s.on_mode_changed.emit(mode=s.mode)
        )

    slice_count: bpy.props.IntProperty(
        name='Slice Count',
        description='Number of slices',
        default=1,
        min=1,
        max=100,
        update=lambda s, c: prop_changed_ls(s, c, "slice_count", s.slice_count)
    )

    active_position: bpy.props.FloatProperty(
        name='Position',
        description='Slice Position',
        default=0.0,
        min=0.0,
        max=100.0,
        subtype='PERCENTAGE',
        update=lambda s, c: prop_changed_ls(s, c, "active_position", s.active_position)
    )

    active_index: bpy.props.IntProperty(
        name='Active Index',
        description='Active Slice Index',
        default=0,
        min=0,
        max=100,
        update=lambda s, c: prop_changed_ls(s, c, "active_index", s.active_index)
    )

    use_split: bpy.props.BoolProperty(
        name='Split Loops',
        description='Split the loops into two',
        default=True,
        update = lambda s, c: prop_changed_ls(s, c, "use_split", s.use_split)
    )

    cap_sections: bpy.props.BoolProperty(
        name='Cap Sections',
        description='Cap the loops after being split',
        default=False,
        update = lambda s, c: prop_changed_ls(s, c, "cap_sections", s.cap_sections)
    )

    gap_distance: bpy.props.FloatProperty(
        name='Gap Distance',
        description='Distance between the split edge loops',
        min=0.0,
        default=0.0,
        subtype='DISTANCE',
        unit='LENGTH',
        update=lambda s, c: prop_changed_ls(s, c, "gap_distance", s.gap_distance)
    )


from .. keymaps.modal_keymapping import ModalKeymap
class ModalKeymapDisplay(bpy.types.PropertyGroup):

    use_even: bpy.props.StringProperty(name="even")
    flipped: bpy.props.StringProperty(name="flip")
    mirrored: bpy.props.StringProperty(name="mirrored")
    perpendicular: bpy.props.StringProperty(name="perpendicular")
    use_multi_loop_offset: bpy.props.StringProperty(name="multi loop offset")
    loop_space_value: bpy.props.StringProperty(name="loop spacing")
    use_snap_points: bpy.props.StringProperty(name="snap points")
    lock_snap_points: bpy.props.StringProperty(name="lock snap points")
    freeze_edge: bpy.props.StringProperty(name="freeze edge")
    insert_verts: bpy.props.StringProperty(name="insert verts")
    insert_on_selected_edges: bpy.props.StringProperty(name="use selected edges")
    increase_loop_count: bpy.props.StringProperty(name="increase loop count")
    decrease_loop_count: bpy.props.StringProperty(name="decrease loop count")
    insert_midpoint: bpy.props.StringProperty(name="insert loop at midpointS")

    awaiting_input: bpy.props.BoolProperty(
        name='Awating Input',
        description='Keymap operator is awiating user input',
        default=False,
    )

    
    def init(self, keymap: ModalKeymap):

        if self.awaiting_input:
            return

        for attribute in FL_Options.bl_rna.properties.keys():
            if attribute not in {'rna_type', 'name', 'dirty', 'cancel', 'snap_divisions', 'snap_factor', 'snap_distance,', 'use_distance', 'auto_segment_count', 'mode', 'prev_mode',}:
                user_friendly_name = utils.ui.get_ordered_fl_keymap_actions().get(attribute, None)
                for key, item in keymap.get_all_mappings():
                    if user_friendly_name == item:
                        hotkey = utils.ui.append_modifier_keys(key[0], key[2], key[3], key[4])
                        setattr(self, attribute, hotkey)
                        break

        for attribute in self.__annotations__.keys():
            if attribute in {'increase_loop_count','decrease_loop_count', 'insert_midpoint'}:
                user_friendly_name = utils.ui.get_ordered_fl_keymap_actions().get(attribute, None)
                for key, item in keymap.get_all_mappings():
        
                        if user_friendly_name == item:
                            hotkey = utils.ui.append_modifier_keys(key[0], key[2], key[3], key[4])
                            setattr(self, attribute, hotkey)
                            break
        