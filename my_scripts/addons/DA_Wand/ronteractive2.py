import bpy
import bmesh
from bpy.props import IntProperty, BoolProperty, FloatProperty, PointerProperty, StringProperty, EnumProperty

from . data.dawand_data import DAWandData
import dill as pickle
import sys
sys.path.append('../DA_Wand')
from DA_Wand.models import create_model
from DA_Wand.models.layers.meshing import Mesh
from DA_Wand.models.layers.meshing.io import PolygonSoup
from DA_Wand.models.networks import floodfill_scalar_v2
from DA_Wand.util.util import graphcuts
import numpy as np
import os
import torch
from pathlib import Path
from enum import Enum



#Demo code
def run_forward_pass(model, dataset, face_list, return_features=False):
    # TODO: Will likely need to debug this so all the preprocessing works on multiple anchors
    dataset.update_anchor(face_list)
    input_meta = dataset[0]
    input_meta = {key: [val] for key,val in input_meta.items()}

    model.set_input(input_meta)

    with torch.no_grad():
        preds, features = model.forward()

        if return_features:
            return preds, features
    return preds


def oncall(point, meshfile, meshdir, ff, gc, done_faces = None):

    #no parser hehe
    dir_path = os.path.dirname(os.path.realpath(__file__))
    modeldir = os.path.join(dir_path, 'checkpoints')
    modelname = 'dawand'
    optname = 'opt'
    normalize = 'store_true'

    with open(os.path.join(modeldir, f"{optname}.pkl"), 'rb') as f:
        opt = pickle.load(f)
    opt.export_save_path = modeldir
    opt.dataroot = meshdir
    opt.test_dir = meshdir
    opt.network_load_path = modeldir

    # TODO: temporary opt fix
    opt.arch = "meshcnn"

    # Turn off all extraneous settings
    opt.name = ""
    opt.time = False
    opt.semantic_loss = False
    opt.is_train = False
    opt.testaug = False
    opt.num_aug = 0
    opt.serial_batches = True  # no shuffle
    opt.time = False
    opt.export_view_freq = 0
    opt.export_preds = False
    opt.continue_train = False
    opt.floodfillparam = False
    opt.test_aug = False
    opt.which_epoch = modelname
    opt.ff_epoch = modelname
    opt.export_pool = False
    opt.distortion_loss = None
    opt.delayed_distortion_epochs = float('inf')
    opt.solo_distortion = False
    opt.shuffle_topo = False
    opt.num_threads = 0
    opt.supervised = False
    opt.gcsupervision = False
    opt.floodfillparam = False

    # NOTE: hacky way to guarantee only 1 copy of mesh in dataset but it works
    meshname = meshfile.replace(".obj", "")
    opt.subset = [f"{meshname}_0"]
    opt.max_dataset_size = 1
    opt.max_sample_size = 1
    opt.interactive = True

    opt.overwritecache = False
    # opt.overwriteopcache = True
    opt.overwriteanchorcache = True
    opt.overwritemeanstd = True
    if not torch.cuda.is_available():
        opt.gpu_ids = []
    else:
        opt.gpu_ids = [0]
    model = create_model(opt)
    print(f"Model loaded from {model.save_dir}")

    dataset = DAWandData(opt, meshfile)
    soup = PolygonSoup.from_obj(os.path.join(meshdir, meshfile))
    mesh = Mesh(soup.vertices, soup.indices)

    if normalize:
        mesh.normalize()
        mesh.export_obj(meshdir, f"{meshname}_norm")

    current_index_list = []
    current_anchor_pos = []
    previous_preds = None
    preds = None
    pred_cache = {}
    mode = "model"
    prev_mode = "model"
    mode_options = ['model']

    # Default settings
    alpha = 1
    beta = 0.7
    gamma = 0.5
    dthreshold = 0.3
    ethreshold = 100
    method = None
    if ff and gc:
        postprocess = ["gc", "ff"]
    elif ff:
        postprocess = ["ff"]
    elif gc:
        postprocess = ["gc"]
    else:
        postprocess = []
    ff = True
    gc = True
    uvmode = False
    include_anchor = True
    patchgrow = False
    face_index = None
    changed = True

    isometric = 0

    vertices, faces, _ = mesh.export_soup()
    vrange = np.arange(len(vertices))
    frange = np.arange(len(vertices), len(vertices) + len(faces))

    current_struct = ''

    #we'll need to get this index from blender
    structure, index = 'mesh', point #this is where it gets the currently selected guy

    #shouldn't need any postprocess options lol

    # == Execute inference if change detected in selection (append anchor to inference) ==
    face_index = index - min(frange)
    new_selection = (face_index not in current_index_list)
    if structure == "mesh" and new_selection and index in frange:
        print(f"Current anchors list: {current_index_list}, New anchor: {face_index}")
        current_index_list = [face_index]
        current_anchor_pos = []
        preds = None
        previous_preds = None

        # Run inference on new anchor set
        if mode == "model":
            preds = run_forward_pass(model, dataset, current_index_list)
            preds = preds.squeeze().detach().cpu().numpy()
            # Reset the pred cache
            pred_cache = {'model': preds}

            # Run postprocesses
            predkey = "model"
            for post in postprocess:
                if post == "gc":
                    preds = graphcuts(preds, mesh, anchors=current_index_list)
                    predkey += "_gc"
                    pred_cache[predkey] = preds
                if post == "ff":
                    preds = floodfill_scalar_v2(mesh, torch.from_numpy(preds).float(), face_index, previous_preds = torch.from_numpy(previous_preds).float() if (previous_preds is not None and patchgrow) else None).detach().numpy()
                    predkey += "_ff"
                    pred_cache[predkey] = preds

            previous_preds = preds
            hard_preds = np.round(preds)

        anchor_pos = np.mean([mesh.vertices[v.index] for v in mesh.topology.faces[face_index].adjacentVertices()], axis=0, keepdims=True)
        current_anchor_pos.append(anchor_pos)

        # Anchor colors are all fixed except most recent
        anchor_colors = [[0,0,1] for _ in current_anchor_pos[:-1]] + [[0,1,0]]
        return(hard_preds)


#Blender Call



done_faces = [] # List of faces that have already been assigned
vertex_set = None

def uv_from_vert_first(uv_layer, v):
    for l in v.link_loops:
        uv_data = l[uv_layer]
        return uv_data.uv
    return None

def uv_from_vert_average(uv_layer, v):
    uv_average = np.zeros(2)
    total = 0.0
    for loop in v.link_loops:
        uv_average += np.array(loop[uv_layer].uv)
        total += 1.0

    if total != 0.0:
        return uv_average * (1.0 / total)
    else:
        return None

class OnClick(bpy.types.Operator):
    bl_idname = "object.modal_operator"
    bl_label = "OnClick"

    #don't know what these are for, but were in the modal quickstart
    def __init__(self):
        print("Start")

    def __del__(self):
        print("End")

    #for the modal stuff, like mousemove - not using
    def execute(self, context):
        return {'FINISHED'}

    #main function
    def mark_seams_by_index(self, context):
        obj = context.object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        wm = context.window_manager
        #hopefully these will let us turn these on
        ff = wm.floodfill
        gc = wm.graphcuts

        #some set up for the modes
        mode = wm.mode_enum
        prevselected = []

        uvmode = wm.uv_mode
        #check if in edit mode
        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Please enter Edit Mode.")
            return {'CANCELLED'}


        if mode == "EX":
            for f in bm.faces:
                if f.select:
                    prevselected.append(f.index)

        #deselect all
        bpy.ops.mesh.select_all(action='DESELECT')

        # Select the face under the mouse cursor
        bpy.ops.view3d.select(location=(self.mouse_x, self.mouse_y))

        # Get the selected bmesh face
        selected_face = None
        selected_fi = None
        for f in bm.faces:
            if f.select:
                selected_face = f.index + len(bm.verts) #literally i have no clue
                selected_fi = f.index

        if selected_face is None:
            self.report({'ERROR'}, "Please select a valid face.")
            return {'CANCELLED'}

        mesh_changed = False
        if vertex_set is None:
            mesh_changed = True
        else:
            mesh_changed = not np.allclose(vertex_set, bm.verts)

        # Only export if the current mesh vertex set has changed
        mesh_changed = False
        if vertex_set is None:
            mesh_changed = True
        else:
            mesh_changed = not np.allclose(vertex_set, bm.verts)

        if mesh_changed:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            target_file = os.path.join(dir_path, 'tempobj.obj')
            bpy.ops.export_scene.obj(filepath=target_file, keep_vertex_order=True,
                                    use_materials=False, use_uvs=False, use_normals=False, use_triangles=True)


        #after export we have to redeclare the bmesh

        #so we redeclare the bmesh
        bpy.ops.object.mode_set(mode='EDIT')
        obj = context.object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        # Get faces with assigned UVs within valid texel range to ignore from predicted selection
        uv_layer = bm.loops.layers.uv.active
        current_uvs = None
        if uv_layer is not None:
            current_uvs = []
            for face in bm.faces:
                faceuv = []
                for loop in face.loops:
                    uv = loop[uv_layer].uv
                    faceuv.append(uv)
                current_uvs.append(faceuv)
            current_uvs = np.array(current_uvs)

        if current_uvs is None:
            done_faces = []
        else:
            # Look for all faces with any valid UVs (within 0-1 range)
            done_faces = np.where(np.any(np.all((current_uvs > 0.0) & (current_uvs < 1.0), axis=2), axis=1))[0]

        mapping = oncall(selected_face, 'tempobj.obj', dir_path, ff, gc, done_faces=done_faces)
        selected_faces = np.where(mapping == 1)[0]

        bm.faces.ensure_lookup_table()

        for i in range(len(bm.faces)):
            if mapping[i] == 1:
                bm.faces[i].select = True
        if mode == "EX":
            for face in prevselected:
                bm.faces[face].select = True

        #then bmesh update
        bmesh.update_edit_mesh(mesh)

        #switch to back edit mode and show selection

        #replaces the current uv unwrap = may want to change this later
        #bpy.ops.mesh.uv_texture_add()
        if uvmode == "BLENDERUNWRAP":
            bpy.ops.uv.unwrap()
        elif uvmode == "SLIM":
            from DA_Wand.util.util import SLIM

            soup = PolygonSoup.from_obj(os.path.join(dir_path, 'tempobj.obj'))

            # Get submesh selection
            # NOTE: Don't build Mesh object if possible! Expensive ...
            selectfs = soup.indices[selected_faces]
            selectvs = np.sort(np.unique(selectfs))
            subvs = soup.vertices[selectvs]
            vmap = np.zeros(len(soup.vertices), dtype=np.int64)
            vmap[selectvs] = np.arange(len(subvs))
            subfs = vmap[selectfs]

            slimuv, slimenergy = SLIM(subvs, subfs)

            uv_layer = bm.loops.layers.uv.active

            # Define a uv layer if one doesn't exist
            if uv_layer is None:
                bm.loops.layers.uv.new("DAWandUV")
                uv_layer = bm.loops.layers.uv.get("DAWandUV")

            ## Update UVs of selected faces
            for fi in selected_faces:
                face = bm.faces[fi]
                for loop in face.loops:
                    v = loop.vert
                    subv = vmap[v.index]
                    loop[uv_layer].uv = slimuv[subv]


    def modal(self, context, event):

        context.area.tag_redraw()
        if event.type == 'ESC':  #Should cancel
            return {'CANCELLED'}


    def invoke(self, context, event):
        #call modal functions - not using
        #self.execute(context)
        #context.window_manager.modal_handler_add(self)

        #get mouse location of initial click
        self.mouse_x = int(event.mouse_region_x)
        self.mouse_y = int(event.mouse_region_y)
        #switch to face mode
        bpy.ops.mesh.select_mode(type="FACE")
        self.mark_seams_by_index(context)
        return {'FINISHED'}


class DA_Icon(bpy.types.WorkSpaceTool):
    #set up the ui
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = 'da_icon.da_tool'
    bl_label = 'DA Wand'
    bl_description = (
        'Click on a face to select a local sub-region with low-distortion parameterization\n'
        'and create the corresponding uv map'
    )
    #set the icon and cursor
    dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "icons")
    #print(dir_path)
    icon = os.path.join(dir_path, 'wand.wand')
    #print(icon)
    bl_icon = icon
    #sets the functionality
    bl_keymap = (
       ('object.modal_operator', {'type': 'LEFTMOUSE', 'value': 'CLICK'}, {'properties': [('deselect_all', True)]}),
       )

class DA_Menu(bpy.types.Panel):
    #other UI - hopefully will open up on click
    bl_label = "DAWand Options"
    bl_idname = "DA_Wand_layout"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'DA Wand'



    def draw(self, context):
        layout = self.layout

        wm = context.window_manager

        row = layout.row()
        row.label(text="Mode")

        row = layout.row()
        layout.prop(wm, "mode_enum")

        row = layout.row()
        row.label(text="UV Mode")

        row = layout.row()
        layout.prop(wm, "uv_mode")

        row = layout.row()
        row.label(text="Segmentation Options")

        row = layout.row()
        row.prop(wm, 'floodfill')

        row = layout.row()
        row.prop(wm, 'graphcuts')




def register_properties():
    bpy.types.WindowManager.floodfill = BoolProperty(name='Flood Fill', default=True,
                                                    description='Fills gaps, leave on for best results')
    bpy.types.WindowManager.graphcuts = BoolProperty(name='Graph Cuts', default=True,
                                                     description='I actually dont know what this does')
    bpy.types.WindowManager.mode_enum = EnumProperty(
        name = "",
        description = "select an option",
        items = [
            ('OV', 'Overwrite', 'Successive clicks will overwrite your current selection'),
            ('EX', 'Extension', 'Successive clicks extend the current selection')
        ]
    )
    bpy.types.WindowManager.uv_mode = EnumProperty(
        name="",
        description = "select and option",
        items = [
            ('BLENDERUNWRAP', 'Blender Unwrap', "Uses Blender's built-in unwrap"),
            ('SLIM', 'Slim', 'Uses SLIM Unwrap'),
            ('NONE', "Don't Unwrap", "Doesn't unwrap on click")
        ]
    )
class UVType(Enum):
    BLENDERUNWRAP = 0
    SLIM = 1
    LSCM = 2
    TUTTE = 3


def unregister_properties():
    del bpy.types.WindowManager.floodfill
    del bpy.types.WindowManager.graphcuts
    del bpy.types.WindowManager.mode_enum