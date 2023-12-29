import bpy

from bpy.app.translations import contexts as i18n_contexts
import rna_keymap_ui

from ...signalslot.signalslot import Signal

from .. keymaps.modal_keymapping import ModalOperatorKeymapCache as km_cache
from .. import utils


def keymap_changed(self, context, keymap_event):
    print(f"Event: {keymap_event} value{self.mirrored_keymap}")
    bpy.ops.ui.keymap_input_operator('INVOKE_DEFAULT')

class AddonPrefs(bpy.types.AddonPreferences):
    bl_idname = utils.common.module()

    on_hud_scale_changed = Signal()
    on_display_panel_pos_changed = Signal()

    show_percentages_changed = Signal()
    show_slider_changed = Signal()
    slider_scale_changed = Signal(args=['scale'])
    slider_position_changed = Signal(args=['[position]'])

    tabs : bpy.props.EnumProperty(name="Tabs",
    items = [("GENERAL", "General", ""),
        ("KEYMAPS", "Keymaps", ""),
         ("DISPLAY_SETTINGS", "Display Settings", ""),
        ],
    default="GENERAL")

    use_spacebar: bpy.props.BoolProperty(name="Enable Industry Compatible Keymap Support", default=False, description="Enabling this switches alt(press) -> to spacebar(toggle) for edge slide.")
    occlude_lines: bpy.props.BoolProperty(name="Don't draw lines behind geometry", default=False, description="Don't draw lines if they are behind geometry.")
    occlude_points: bpy.props.BoolProperty(name="Don't draw points behind geometry", default=False, description="Don't draw points if they are behind geometry.")
    draw_loop_vertices: bpy.props.BoolProperty(name="Draw vertices of the loop preview", default=False, description="Draw the vertices of the loop preview.")

    line_width : bpy.props.IntProperty(
        name="Line Width", 
        description="Loop preview line width.",
        default=1, 
        min=1, 
        max=10,
        subtype='PIXEL'
    )

    loop_color : bpy.props.FloatVectorProperty(
        name="Loop Color",
        description="Loop preview color.",
        default=(0.0, 1.0, 0.5, 0.9),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    distance_line_color : bpy.props.FloatVectorProperty(
        name="Distance Line Color",
        description="Color of the distance markers.",
        default=(1.0, 1.0, 1.0, 0.5),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    distance_display_text_color : bpy.props.FloatVectorProperty(
        name="Distance display text color ",
        description="Color of the text displaying the distance.",
        default=(0.507, 0.933, 1.0, 1.0),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    vertex_size : bpy.props.IntProperty(
        name="Point Size", 
        description="Loop preview point size.",
        default=5,
        min=1, 
        max=10,
        subtype='PIXEL'
    )

    vertex_color : bpy.props.FloatVectorProperty(
        name="Point Color",
        description="Loop preview point color.",
        default=(0.789, 1.0, 0.0, 1.0),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    # select_vertex_size : bpy.props.IntProperty(
    #     name="Select Vertex Point Size", 
    #     description="point size",
    #     default=6,
    #     min=1, 
    #     max=50,
    #     subtype='PIXEL'
    # )

    # select_vertex_color : bpy.props.FloatVectorProperty(
    #     name="Select Vertex Point Color",
    #     description="point color",
    #     default=(1.0, 0.0, 1.0, 0.5),
    #     min=0.0,
    #     max=1.0,
    #     size=4,
    #     subtype='COLOR'
    # )

    center_point_size : bpy.props.IntProperty(
        name="Center Point Size", 
        description="point size.",
        default=6,
        min=1, 
        max=50,
        subtype='PIXEL'
    )

    center_point_color : bpy.props.FloatVectorProperty(
        name="Center Point Color",
        description="point color.",
        default=(0.0, 1.0, 1.0, 0.8),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    snap_tick_width : bpy.props.IntProperty(
        name="Snap Tick Width", 
        description="Width of the snap tick marks.",
        default=2,
        min=1, 
        max=10,
        subtype='PIXEL'
    )

    slider_scale: bpy.props.FloatProperty(
        name="Slider Scale", 
        default=1.0, 
        min=0.5, 
        max=10.0, 
        soft_max=2.0,
        step=1,
        description="Adjust the scale of the slider.",
        update=lambda s, c: s.slider_scale_changed.emit(scale=s.slider_scale)

    )

    slider_x : bpy.props.IntProperty(
        name="Slider X", 
        description="X Position of the slider (Set to -1 to use center).",
        default=-1,
        min=-1,
        subtype='PIXEL',
        update=lambda s, c: s.slider_position_changed.emit(position=(s.slider_x, s.slider_y))
    )

    slider_y : bpy.props.IntProperty(
        name="Slider Y", 
        description="Y Position of the slider (Set to -1 to use default).",
        default=-1,
        min=-1,
        subtype='PIXEL',
        update=lambda s, c: s.slider_position_changed.emit(position=(s.slider_x, s.slider_y))

    )

    slider_width : bpy.props.IntProperty(
        name="Slider Width", 
        description="",
        default=200,
        min=50,
        subtype='PIXEL'
    )

    operator_panel_x : bpy.props.IntProperty(
        name="Operator Display Panel X", 
        description="X Position of the Operator Display Panel.",
        default=170,
        min=0,
        subtype='PIXEL',
        update=lambda s, c: s.on_display_panel_pos_changed.emit()
    )

    operator_panel_y : bpy.props.IntProperty(
        name="Operator Display Panel Y", 
        description="Y Position of the Operator Display Panel.",
        default=170,
        min=0,
        subtype='PIXEL',
        update=lambda s, c: s.on_display_panel_pos_changed.emit()
    )

    panel_locked: bpy.props.BoolProperty(
        name='Panel UI Locked',
        description='',
        default=False,
    )

    panel_minimized: bpy.props.BoolProperty(
        name='Panel UI Minimized',
        description='',
        default=False,
    )

    hud_scale: bpy.props.FloatProperty(
        name="HUD Scale", 
        default=1.0, 
        min=0.5, 
        max=10.0, 
        soft_max=2.0,
        step=1,
        description="Adjust the scale of the HUD.",
        update=lambda s, c: s.on_hud_scale_changed.emit()

    )

    show_bar: bpy.props.BoolProperty(
        name='Display Segment Bar',
        description='Enable to display the segment bar.',
        default=True,
        update=lambda s, c: s.show_slider_changed.emit()

    )

    show_percents: bpy.props.BoolProperty(
        name='Display percentage',
        description='Enable to display the percent of each segment.',
        default=True,
        update=lambda s, c: s.show_percentages_changed.emit()
    )

    interpolation_type: bpy.props.EnumProperty(
        name='Interpolation Type',
        items=[ ('PERCENT', "Percent", "", 1),
                ('DISTANCE', "Distance", "", 2),
              
        ],
        description="",
        default='PERCENT',
        )

    set_edge_flow_enabled: bpy.props.BoolProperty(
        name='Set Edge Flow',
        description='Set the flow of the edge loops.',
        default=False,
    )
    
    tension : bpy.props.IntProperty(
        name="Tension",
        name="Tension",
        default=180, 
        min=-500, 
        max=500
    )

    iterations : bpy.props.IntProperty(
        name="Iterations", 
        default=1, 
        min=1, 
        max=32
    )

    min_angle : bpy.props.IntProperty(
        name="Min Angle", 
        default=0, 
        min=0, 
        max=180, 
        subtype='FACTOR' 
    )

    keymap_error: bpy.props.StringProperty(name="Keymap Error")

    kilometers: bpy.props.BoolProperty(name="Kilometers")
    meters: bpy.props.BoolProperty(name="Meters")
    centimeters: bpy.props.BoolProperty(name="Centimeters")
    millimeters: bpy.props.BoolProperty(name="Millimeters")
    micrometers: bpy.props.BoolProperty(name="Micrometers")

    miles: bpy.props.BoolProperty(name="Miles")
    feet: bpy.props.BoolProperty(name="Feet")
    inches: bpy.props.BoolProperty(name="Inches")
    thou: bpy.props.BoolProperty(name="Thou")


    metric_unit_default: bpy.props.EnumProperty(
        name='Metric Default Unit',
        items=[ ('KILOMETERS', "Kilometers", "km", 1),
                ('METERS', "Meters", "m", 3),
                ('CENTIMETERS', "Centimeters", "cm", 4),
                ('MILLIMETERS', "Millimeters", "mm", 5),
                ('MICROMETERS', "Micrometers", "um", 6),
              
        ],
        description="Use this unit when one is not provided for numeric input.",
        default='METERS',
        )


    imperial_unit_default: bpy.props.EnumProperty(
        name='Imperial Default Unit',
        items=[ ('MILES', "Miles", "mi", 1),
                ('FEET', "Feet", "ft", 3),
                ('INCHES', "Inches", "in", 4),
                ('THOU', "Thou", "thou", 5),
              
        ],
        description="",
        default='INCHES',
        )
    
    def is_len_unit_enabled(self)-> bool:
        return any([self.kilometers, self.meters, self.centimeters, self.millimeters, self.micrometers, \
                    self.miles, self.feet, self.inches, self.thou])


    def draw(self, context):
        wm = context.window_manager
        key_map = None
        try:
            key_map = (km_cache.get_keymap("FL_OT_fast_loop"))
            self.keymap_error = ""
        except FileNotFoundError:
            self.keymap_error = "HotkeyPrefs.JSON file not found. Click the button below to generate the file. "

        layout = self.layout
        row = layout.row()
        row.prop(self, "tabs", expand=True)

        box = layout.box()

        if self.tabs == "GENERAL":
            self.draw_general(context, box)

        elif self.tabs == "KEYMAPS":
            self.draw_keymaps(context, key_map, box)
        elif self.tabs == "DISPLAY_SETTINGS":
            self.draw_display_settings(context, box)

    def draw_general(self, context, layout):
        layout.prop(self, "use_spacebar", toggle=True)  

        layout.operator("ui.reset_operator", text="Click this if an error occured while a fast Loop operator was running, and now it wont start.")

    def draw_display_settings(self, context, layout):
        layout.label(text="General")

        box = layout.box()
        # box.enabled = False
        box.label(text="Operator Display Panel")
        box.prop(self, "operator_panel_x")
        box.prop(self, "operator_panel_y")

        box = layout.box()
        box.label(text="Sliders")
        box.prop(self, "slider_scale")
        box.prop(self, "slider_x")
        box.prop(self, "slider_y")
        box.prop(self, "slider_width")

        box = layout.box()
        box.label(text="HUD")
        box.prop(self, "hud_scale")



        layout.label(text="Draw Loop")
        box = layout.box()
        box.label(text="Warning: The setting below can cause parts of the line to disappear when enabled.", icon='ERROR')
        box.prop(self, "occlude_lines") 

        box.prop(self, "line_width") 
        box.prop(self, "loop_color") 

        layout.label(text="Draw Loop Points")
        box = layout.box()
        box.prop(self, "draw_loop_vertices")
        box.prop(self, "occlude_points")
        box.prop(self, "vertex_size") 
        box.prop(self, "vertex_color") 

        layout.label(text="Snapping")
        box = layout.box()
        box.prop(self, "center_point_color") 
        # box.prop(self, "select_vertex_color") 
        # box.prop(self, "select_vertex_size") 
        box.prop(self, "center_point_size") 
        box.prop(self, "snap_tick_width") 
        # box.prop(self, "snap_tick_minor_length")
        # box.prop(self, "snap_tick_major_length") 

        layout.label(text="Distance Display")
        box = layout.box()
        box.prop(self, "distance_line_color")
        box.prop(self, "distance_display_text_color")

    
    def draw_keymaps(self, context, key_map, layout):
        wm = context.window_manager
        modal_keymap_box = layout.box()
        modal_keymap_box.label(text="Fast Loop:")
        if self.keymap_error:
            modal_keymap_box.label(text=self.keymap_error, icon='ERROR')
        
        if key_map is not None:
            # wm.keymap_strings.init(key_map)
            self.generate_modal_keymap_ui(context, key_map, modal_keymap_box)
      
        layout.operator("ui.save_keymap_operator", text="Save modal keymap preferences")
        kc = wm.keyconfigs.user

        layout.label(text="Operator:")

        km_name = self.get_operator_keymaps()
        km = kc.keymaps.get(km_name)
        if km:
            self.draw_km(kc, km, layout)
        
        
    @staticmethod
    def get_operator_keymaps():
        km_name = 'Mesh'
        return km_name

    @staticmethod
    def draw_km(kc, km, layout):
        layout.context_pointer_set("keymap", km)

        row = layout.row()
        row.prop(km, "show_expanded_items", text="", emboss=False)
        row.label(text=km.name, text_ctxt=i18n_contexts.id_windowmanager)

        if km.show_expanded_items:
            col = layout.column()

            for kmi in km.keymap_items:
                if kmi.idname == "fl.fast_loop":
                    rna_keymap_ui.draw_kmi(["ADDON", "USER", "DEFAULT"], kc, km, kmi, col, 0)

                if kmi.idname == "fl.edge_slide":
                    rna_keymap_ui.draw_kmi(["ADDON", "USER", "DEFAULT"], kc, km, kmi, col, 0)


    def generate_modal_keymap_ui(self, context, keymap, layout):

        wm = context.window_manager
        wm.keymap_strings.init(keymap)

        for action, action_name in utils.ui.get_ordered_fl_keymap_actions().items():
            row = layout.row()
            row.label(text=f"Toggle {action_name} ")
            op = row.operator("ui.keymap_input_operator", text=(f"{getattr(wm.keymap_strings, action)}").capitalize())
            op.active_keymap = action
            op.operator = "FL_OT_fast_loop"