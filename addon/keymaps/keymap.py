import bpy


keymap = None


def register(keyconfig):
    global keymap
    keymap = keyconfig.keymaps.new(name='Mesh', space_type='EMPTY')

    keymap.keymap_items.new('fl.fast_loop', 'INSERT', 'PRESS', alt=True, repeat=False)
    keymap.keymap_items.new('fl.fast_loop_classic', 'INSERT', 'PRESS', repeat=False)
    keymap.keymap_items.new('fl.edge_slide', 'ACCENT_GRAVE', 'PRESS', alt=True, repeat=False)
