import bpy

from bpy.app.translations import contexts as i18n_contexts
import rna_keymap_ui

from .. import utils


m_buttons = ['MOUSE_LMB', 'MOUSE_RMB']

class AddonPrefs(bpy.types.AddonPreferences):
    bl_idname = utils.common.module()

    tabs : bpy.props.EnumProperty(name="Tabs",
    items = [("GENERAL", "General", ""),
        ("KEYMAPS", "Keymaps", ""),
        ("HELP", "Help", ""),],
    default="GENERAL")

    use_rcs: bpy.props.BoolProperty(name="Swap left and right mouse buttons (Enable if you use right click select)", default=False, description="")
    disable_pie: bpy.props.BoolProperty(name="Disable pie menu", default=False, description="If enabled, right click will cause the operator to be cancelled")
    use_spacebar: bpy.props.BoolProperty(name="Toggle Edge Slide with spacebar", default=False, description="Press the space bar to toggle edge slide instead of holding down alt")
    occlude_lines: bpy.props.BoolProperty(name="Don't draw lines behind geometry", default=False, description="Don't draw lines if they are behind geometry")

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
        description='Set the flow of the edge loops',
        default=False,
    )
    
    tension : bpy.props.IntProperty(
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

    def draw(self, context):

        layout = self.layout
        row = layout.row()
        row.prop(self, "tabs", expand=True)

        box = layout.box()

        if self.tabs == "GENERAL":
            self.draw_general(context, box)

        elif self.tabs == "KEYMAPS":
            self.draw_keymaps(context, box)

        elif self.tabs == "HELP":
            self.draw_help(context, box)

    def draw_general(self, context, layout):
        layout.prop(self, "use_rcs")
        layout.prop(self, "disable_pie")  
        layout.prop(self, "use_spacebar")  
        layout.prop(self, "occlude_lines")  

        layout.operator("ui.reset_operator", text="Click this if an error occured while a fast Loop operator was running, and now it wont start.")
    
    def draw_keymaps(self, context, layout):

        wm = context.window_manager
        kc = wm.keyconfigs.user

        layout.label(text="Operator:")

        km_name = self.get_operator_keymaps()
        km = kc.keymaps.get(km_name)
        if km:
            self.draw_km(kc, km, layout)
    
    def draw_help(self, context, layout):
        def add_shortcut_info(keymap, text_box, icons_box):
            m_buttons = ['MOUSE_LMB', 'MOUSE_RMB']

            for text, icons in keymap.items():
                text_box.label(text=text)
                icon_row = icons_box.row()
                icon_row.alignment = 'LEFT'
                
                for icon in icons:
                    if icon in {'MOUSE_LMB', 'MOUSE_RMB'}:
                        i = m_buttons.index(icon) 
                        if self.use_rcs:
                            icon = m_buttons[i-1]
                    if icon is not None:
                        icon_row.label(icon=icon)
                    else:
                        icon_row.label()
                        

        flc = layout
        flc.label(text="Fast Loop Classic")
        row = flc.row()
        row.alignment = 'LEFT'     
        text_box = row.box()
        text_box.alignment = 'LEFT'
        icons_box = row.box()
        icons_box.alignment = 'LEFT'
        
        add_shortcut_info({"Insert Loop": ['MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Insert Loop With Flow": ['EVENT_SHIFT', 'MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Select Loop": ['EVENT_CTRL', 'MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Slide Loop": ['EVENT_ALT', 'MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Slide Loop Even": ['EVENT_CTRL', 'EVENT_ALT', 'MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Adjust Loop Preserve Space": ['EVENT_SHIFT', 'EVENT_ALT', 'MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Remove Loop": ['EVENT_CTRL', 'EVENT_SHIFT', 'MOUSE_LMB']}, text_box, icons_box)

        fl=layout
        fl.label(text="Fast Loop")
        row = fl.row()
        row.alignment = 'LEFT'     
        text_box = row.box()
        text_box.alignment = 'RIGHT'
        icons_box = row.box()
        icons_box.alignment = 'LEFT'

        add_shortcut_info({"Insert Loop": ['MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Change Loop Number 1-9": ['ADD', 'REMOVE']}, text_box, icons_box)
        add_shortcut_info({"Insert Loop With Flow": ['EVENT_SHIFT', 'MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Select Loop": ['EVENT_CTRL', 'MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Slide Loop": ['EVENT_ALT', 'MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Slide Loop Even": ['EVENT_CTRL', 'EVENT_ALT', 'MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Adjust Loop Preserve Space": ['EVENT_SHIFT', 'EVENT_ALT', 'MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Remove Loop": ['EVENT_CTRL', 'EVENT_SHIFT', 'MOUSE_LMB']}, text_box, icons_box)
        
        #add_shortcut_info({"Single": ['EVENT_S']}, text_box, icons_box)
        add_shortcut_info({"Mirrored": ['EVENT_M']}, text_box, icons_box)
        add_shortcut_info({"Midpoint": ['EVENT_C']}, text_box, icons_box)
        add_shortcut_info({"Perpendicular: /": ['ERROR']}, text_box, icons_box)
        add_shortcut_info({"Select New Edges": ['EVENT_Q']}, text_box, icons_box)
        add_shortcut_info({"Multi Loop Offset": ['EVENT_O']}, text_box, icons_box)
        add_shortcut_info({"Toggle Change Scale": ['EVENT_W']}, text_box, icons_box)
        add_shortcut_info({"Snap Points": ['EVENT_S']}, text_box, icons_box)
        add_shortcut_info({"Lock Snap Points": ['EVENT_X']}, text_box, icons_box)
        add_shortcut_info({"Pie Menu": ['MOUSE_RMB']}, text_box, icons_box)

        es=layout
        es.label(text="Edge Slide")
        row = es.row()
        row.alignment = 'LEFT'     
        text_box = row.box()
        text_box.alignment = 'RIGHT'
        icons_box = row.box()
        icons_box.alignment = 'LEFT'
        
        add_shortcut_info({"Slide Edge": ['MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Slide Edge Even": ['EVENT_CTRL','MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Slide Edge Preserve Space": ['EVENT_SHIFT','MOUSE_LMB']}, text_box, icons_box)
        add_shortcut_info({"Toggle Edge/Vertex Constraint Translation Along Axis (XYZ)": ['EVENT_X', 'EVENT_Y', 'EVENT_Z']}, text_box, icons_box)
        add_shortcut_info({"Toggle Selection Mode": ['EVENT_S']}, text_box, icons_box)


        
        
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

                if kmi.idname == "fl.fast_loop_classic":
                    rna_keymap_ui.draw_kmi(["ADDON", "USER", "DEFAULT"], kc, km, kmi, col, 0)

                if kmi.idname == "fl.edge_slide":
                    rna_keymap_ui.draw_kmi(["ADDON", "USER", "DEFAULT"], kc, km, kmi, col, 0)


