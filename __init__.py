import bpy

addon_keymaps = []

# def tool_exists(tool_idname):
#     for workspace in bpy.data.workspaces:
#         for screen in workspace.screens:
#             for area in screen.areas:
#                 if area.type == 'VIEW_3D':
#                     for tool in area.spaces[0].tools:
#                         if tool.idname == tool_idname:
#                             return True
#     return False

def register():
    import dill
    import scipy
    import sklearn
    import robust_laplacian
    import potpourri3d
    import matplotlib
    import igraph
    import torch
    import igl

    from .DAWandBlender import OnClick, DA_Icon, DA_Menu, Clear_Anchors, Clear_UV, Clear_Sel, Unwrap, MarkSeams, ClearSeams, register_properties, unregister_properties

    # bpy.utils.register_tool(DA_Icon, after={'builtin.scale_cage'}, separator=True, group=True)
    bpy.utils.register_class(OnClick)
    bpy.utils.register_class(DA_Menu)
    bpy.utils.register_class(Clear_Anchors)
    bpy.utils.register_class(Unwrap)
    bpy.utils.register_class(Clear_Sel)
    bpy.utils.register_class(Clear_UV)
    bpy.utils.register_class(MarkSeams)
    bpy.utils.register_class(ClearSeams)

    #keymap garbage
    wm = bpy.context.window_manager
    keyconfigs = wm.keyconfigs
    kc = keyconfigs.addon

    #basically we only register the tool if we have a keymap
    #seems like a heavyweight solution but fixes it.
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='Mesh', space_type='EMPTY')
        kmi = km.keymap_items.new(DA_Icon.bl_idname, 'LEFTMOUSE', 'CLICK', ctrl=False, shift=False)
        addon_keymaps.append((km, kmi))
        bpy.utils.register_tool(DA_Icon, after={'builtin.scale_cage'}, separator=True, group=True)

    register_properties()

def unregister():

    from .DAWandBlender import OnClick, DA_Icon, DA_Menu, Clear_Anchors, Clear_UV, Clear_Sel, Unwrap, MarkSeams, ClearSeams, register_properties, unregister_properties

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_tool(DA_Icon)
    bpy.utils.unregister_class(OnClick)
    bpy.utils.unregister_class(DA_Menu)
    bpy.utils.unregister_class(Clear_Anchors)
    bpy.utils.unregister_class(Unwrap)
    bpy.utils.unregister_class(Clear_Sel)
    bpy.utils.unregister_class(Clear_UV)
    bpy.utils.unregister_class(MarkSeams)
    bpy.utils.unregister_class(ClearSeams)
    unregister_properties()


if __name__ == "__main__":
    register()