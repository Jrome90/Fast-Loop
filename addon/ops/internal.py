import bpy

class UI_OT_override_reset(bpy.types.Operator):
    bl_idname = 'ui.overrride_reset'
    bl_label = 'Override Reset'
    bl_options = {'REGISTER','INTERNAL'}

    bl_description = "Reset the current slot"

    def execute(self, context):
        self.reset(context)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)

    def reset(self, context):
        scene = context.scene
        slots = scene.Loop_Cut_Slots.loop_cut_slots
        index = scene.Loop_Cut_Lookup_Index
        slot = slots[index]
        for i, loop_cut in enumerate(slot.loop_cut_slot.values()):
            if loop_cut.get_method() == 'PERCENT':
                percent = ((1.0 + i) / ( (len(slot.loop_cut_slot.values())) + 1.0))
                loop_cut.percent = percent * 100
            else:
                loop_cut.distance = 0.0