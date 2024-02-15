import bpy
import bmesh
from bpy.props import IntProperty, BoolProperty, FloatProperty, PointerProperty, StringProperty, EnumProperty

from . data.intseg_data import IntSegData
import dill as pickle
import sys
sys.path.append('../DA_Wand')
from DA_Wand.models.layers.meshing.analysis import computeFaceAreas, computeDihedrals
from DA_Wand.models import create_model
from DA_Wand.models.layers.meshing import Mesh
from DA_Wand.models.layers.meshing.io import PolygonSoup
from DA_Wand.models.layers.meshing.edit import VertexStarCollapse, EdgeCollapse
from DA_Wand.models.networks import floodfill_scalar_v1, floodfill_scalar_v2
from DA_Wand.util.util import graphcuts 
import numpy as np
import os 
import torch 
import random 
from pathlib import Path



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


def oncall(point, meshfile, meshdir, ff, gc):

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
        
    opt.overwritecache = True 
    # opt.overwriteopcache = True   
    opt.overwriteanchorcache = True   
    opt.overwritemeanstd = True  
    if not torch.cuda.is_available():
        opt.gpu_ids = []
    else:
        opt.gpu_ids = [0] 
    model = create_model(opt)
    print(f"Model loaded from {model.save_dir}")
    
    dataset = IntSegData(opt)
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
        for f in bm.faces:
            if f.select:
                selected_face = f.index + len(bm.verts) #literally i have no clue

        #then export the obj for dawand
        dir_path = os.path.dirname(os.path.realpath(__file__))
        target_file = os.path.join(dir_path, 'tempobj.obj')
        bpy.ops.export_scene.obj(filepath=target_file, use_selection=True)
        #hopefully it will find where the add-on is located

        #to prevent errors when misclick
        #will make more rigorous later
        try:
            mapping = oncall(selected_face, 'tempobj.obj', dir_path, ff, gc)
        except UnboundLocalError:
            return{'FINISHED'}
        #after export we have to redeclare the bmesh

        #so we redeclare the bmesh
        bpy.ops.object.mode_set(mode='EDIT')
        obj = context.object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
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
        bpy.ops.uv.unwrap()
        
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


def unregister_properties():
    del bpy.types.WindowManager.floodfill
    del bpy.types.WindowManager.graphcuts
    del bpy.types.WindowManager.mode_enum