import bpy
import bmesh
from bpy.props import IntProperty, BoolProperty, FloatProperty, PointerProperty, StringProperty, EnumProperty

import sys
import os

dir_path = (os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.join(dir_path, 'DA_Wand'))

from data.dawand_data import DAWandData
from models.layers.meshing.analysis import computeFaceAreas, computeDihedrals
from models import create_model
from models.layers.meshing import Mesh
from models.layers.meshing.io import PolygonSoup
from models.layers.meshing.edit import VertexStarCollapse, EdgeCollapse
from models.networks import floodfill_scalar_v2
from util.util import graphcuts, clear_directory

import dill as pickle
import numpy as np
import torch
import random
from pathlib import Path
from enum import Enum

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

class steps(Enum):
    Nothing = 0
    Starting = 1
    Exporting = 2
    Preprocessing = 3
    Processing = 4
    Finished = 5

dir_path = ""

class OnClick(bpy.types.Operator):
    bl_idname = "object.modal_operator"
    bl_label = "OnClick"
    
    step = steps.Nothing
    _timer = None

    prevselected = []
    selected_face = None
    mapping = []
    ff, gc = None, None

    model = None
    mesh = None
    dataset = None
    frange = None

    def reset(self, context):
        self.step = steps.Nothing
        
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        wm.progress = self.step.value

        self.prevselected = []
        self.selected_face = None
        self.mapping = []
        self.ff, self.gc = None, None

        self.model = None
        self.mesh = None
        self.dataset = None
        self.frange = None

    def preprocess(self, meshfile, meshdir):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        modeldir = os.path.join(dir_path, 'DA_Wand/checkpoints')
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
        opt.cachefolder = "__dawandcache__"
        opt.anchorcachefolder = "__dawandcache__"
        # opt.overwriteopcache = True
        opt.overwriteanchorcache = True
        opt.overwritemeanstd = True
        if not torch.cuda.is_available():
            opt.gpu_ids = []
        else:
            opt.gpu_ids = [0]

        self.model = create_model(opt)
        print(f"Model loaded from {self.model.save_dir}")

        self.dataset = DAWandData(opt, meshfile)
        soup = PolygonSoup.from_obj(os.path.join(meshdir, meshfile))
        self.mesh = Mesh(soup.vertices, soup.indices)

        if normalize:
            self.mesh.normalize()
            self.mesh.export_obj(meshdir, f"{meshname}_norm")

        
        # prev_mode = "model"
        # mode_options = ['model']

        # Default settings
        # alpha = 1
        # beta = 0.7
        # gamma = 0.5
        # dthreshold = 0.3
        # ethreshold = 100
        # method = None
        
        # if ff and gc:
        #     postprocess = ["gc", "ff"]
        # elif ff:
        #     postprocess = ["ff"]
        # elif gc:
        #     postprocess = ["gc"]
        # else:
        #     postprocess = []
        # ff = True
        # gc = True
        #uvmode = False
        #include_anchor = True
        
        #changed = True

        #isometric = 0

        vertices, faces, _ = self.mesh.export_soup()
        #vrange = np.arange(len(vertices))
        self.frange = np.arange(len(vertices), len(vertices) + len(faces))

        #current_struct = ''

    def process(self):    
        patchgrow = False
        face_index = None
        current_index_list = []
        current_anchor_pos = []
        previous_preds = None
        preds = None
        pred_cache = {}

        frange = self.frange
        model = self.model
        dataset = self.dataset
        mesh = self.mesh

        #we'll need to get this index from blender
        structure, index = 'mesh', self.selected_face #this is where it gets the currently selected guy

        #def process():
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
            preds = run_forward_pass(model, dataset, current_index_list)
            preds = preds.squeeze().detach().cpu().numpy()
            # Reset the pred cache
            pred_cache = {'model': preds}

            # Run postprocesses
            predkey = "model"
            if self.gc:
                preds = graphcuts(preds, mesh)
                predkey += "_gc"
                pred_cache[predkey] = preds
            if self.ff:
                preds = floodfill_scalar_v2(mesh, torch.from_numpy(preds).float(), face_index, previous_preds = torch.from_numpy(previous_preds).float() if (previous_preds is not None and patchgrow) else None).detach().numpy()
                predkey += "_ff"
                pred_cache[predkey] = preds

            previous_preds = preds
            hard_preds = np.round(preds)

            anchor_pos = np.mean([mesh.vertices[v.index] for v in mesh.topology.faces[face_index].adjacentVertices()], axis=0, keepdims=True)
            current_anchor_pos.append(anchor_pos)

            # Anchor colors are all fixed except most recent
            #anchor_colors = [[0,0,1] for _ in current_anchor_pos[:-1]] + [[0,1,0]]
            self.mapping = hard_preds


    #don't know what these are for, but were in the modal quickstart
    def __init__(self):
        print("Start")

    def __del__(self):
        print("End")

    #for the modal stuff, like mousemove - not using
    def execute(self, context):
        return {'FINISHED'}
        

    def modal(self, context, event):
        context.area.tag_redraw()
        if event.type == 'ESC':  #Should cancel
            self.report({'ERROR'}, "Cancelled by ESC press")
            self.reset(context)
            return {'CANCELLED'}
        
        wm = context.window_manager
        self.ff = wm.floodfill
        self.gc = wm.graphcuts

        if self.step == steps.Starting:
            obj = context.object
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)

            #some set up for the modes
            self.prevselected = []
            self.selected_face = None

            #check if in edit mode
            if obj.mode != 'EDIT':
                self.report({'ERROR'}, "Please enter Edit Mode.")
                self.reset(context)
                return {'CANCELLED'}

            #save what is currently selected
            for f in bm.faces:
                if f.select:
                    self.prevselected.append(f.index)

            #MAIN SELECTION LOGIC

            #deselect all
            bpy.ops.mesh.select_all(action='DESELECT')

            # Select the face under the mouse cursor
            bpy.ops.view3d.select(location=(self.mouse_x, self.mouse_y))

            # Get the selected bmesh face
            self.selected_face = None
            for f in bm.faces:
                if f.select:
                    self.selected_face = f.index + len(bm.verts)

            if self.selected_face is None:
                self.report({'ERROR'}, "Please select a valid face.")
                self.reset(context)
                return {'CANCELLED'}
            
            for face in self.prevselected:
                    bm.faces[face].select = True

        elif self.step == steps.Exporting:
            # Only export if the current mesh vertex set has changed
            mesh_changed = False
            if vertex_set is None:
                mesh_changed = True
            else:
                mesh_changed = not np.allclose(vertex_set, bm.verts)

            global dir_path
            if mesh_changed:
                dir_path = os.path.dirname(os.path.realpath(__file__))
                target_file = os.path.join(dir_path, 'tempobj.obj')
            
                bpy.ops.wm.obj_export(filepath=target_file, export_uv=False, 
                                    export_normals=False, export_materials=False,
                                    export_selected_objects=True)
                
                # Also need to wipe the cache
                if os.path.exists(os.path.join(dir_path, '__dawandcache__')):
                    clear_directory(os.path.join(dir_path, '__dawandcache__'))

            #redeclare the bmesh
            bpy.ops.object.mode_set(mode='EDIT')
            obj = context.object
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)

        elif self.step == steps.Preprocessing:
            try:
                self.preprocess('tempobj.obj', dir_path)  
            except IndexError:
                self.report({'ERROR'}, f"Something went wrong when loading the mesh, ensure the object is selected before entering edit mode")
                self.reset(context)
                return {'CANCELLED'}
            except AssertionError:
                self.report({'ERROR'},  'Only triangle meshes are supported. Try "Triangulate Faces" to use DA Wand on this mesh')
                self.reset(context)
                return {'CANCELLED'}
            except AttributeError:
                self.report({'ERROR'},  'Something went wrong, likely due to the mesh having disconnected components, so DA Wand may not work on this mesh')
                self.reset(context)
                return {'CANCELLED'}
       
        elif self.step == steps.Processing:
            self.process()
        else:
            obj = context.object
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)
            bm.faces.ensure_lookup_table()

            #select the faces
            for i in range(len(bm.faces)):
                if self.mapping[i] == 1:
                    bm.faces[i].select = True

            #and select everything that was selected before
            #we are always extending the CLICK
            for face in self.prevselected:
                    bm.faces[face].select = True

            #at this point, all of the faces should be selected
            #but the user can still select more if they want

            #then bmesh update
            bmesh.update_edit_mesh(mesh)
            self.reset(context)
            return {'FINISHED'}

        self.step = steps(self.step.value + 1)
        wm.progress = self.step.value * 20
        return {'INTERFACE'}

    def invoke(self, context, event):
        wm = context.window_manager
        #get mouse location of initial click
        self.mouse_x = int(event.mouse_region_x)
        self.mouse_y = int(event.mouse_region_y)
        #switch to face mode
        bpy.ops.mesh.select_mode(type="FACE")

        self.step = steps.Starting
        wm.progress = self.step.value * 20

        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}
        #self.mark_seams_by_index(context)
        #return {'FINISHED'}


class Clear_Anchors(bpy.types.Operator):
    bl_idname = "clear.anchors"
    bl_label = "clearanchors"
    bl_description = "Clears all face UVs and selection"

    def execute(self, context):
        obj = context.object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        #check if in edit mode
        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Please enter Edit Mode.")
            return {'CANCELLED'}
        
        #hopefully remove the uvs
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is not None:
            for i in range(len(bm.faces)):
                for j in range(len(bm.faces[i].loops)):
                    bm.faces[i].loops[j][uv_layer].uv = (0, 0)
       
        bmesh.update_edit_mesh(mesh)
        
        #deselect
        bpy.ops.mesh.select_all(action='DESELECT')

        return {'FINISHED'}
    
class Clear_Sel(bpy.types.Operator):
    bl_idname = "clear.sel"
    bl_label = "clearsel"
    bl_description = "Deselects faces but maintains each face's UVs"

    def execute(self, context):
        obj = context.object

        #check if in edit mode
        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Please enter Edit Mode.")
            return {'CANCELLED'}
        
        #deselect
        bpy.ops.mesh.select_all(action='DESELECT')

        return {'FINISHED'}
    
class Clear_UV(bpy.types.Operator):
    bl_idname = "clear.uv"
    bl_label = "clearuv"
    bl_description = "Erases all face UVs but keeps your current selection"

    def execute(self, context):
        obj = context.object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        #check if in edit mode
        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Please enter Edit Mode.")
            return {'CANCELLED'}
        
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is not None:
            for i in range(len(bm.faces)):
                for j in range(len(bm.faces[i].loops)):
                    bm.faces[i].loops[j][uv_layer].uv = (0, 0)
       
        bmesh.update_edit_mesh(mesh)

        return {'FINISHED'}
    
class Unwrap(bpy.types.Operator):
    bl_idname = "unwrap.button"
    bl_label = "unwrapbutton"
    bl_description = "Unwraps the mesh using the above settings"

    def execute(self, context):
        obj = context.object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        wm = context.window_manager

        #variables needed for unwrapping
        uvmode = wm.uv_mode
        newmap = wm.newmap
        freeze = wm.freeze
        
        global dir_path

        #check if in edit mode
        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Please enter Edit Mode.")
            return {'CANCELLED'}


        select_for_unwrap = []
        #this will tell us what is selected now
        for f in bm.faces:
            if f.select:
                select_for_unwrap.append(f.index)

        #if we don't have any faces here, then nothing is selected 
        if not select_for_unwrap:
            self.report({'ERROR'}, "Please select faces before unwrapping")
            return {'CANCELLED'}

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
        

        #if we want to preserve the old uvs
        if freeze:
            #remove the done uvs from the selection list
            select_final = [face for face in select_for_unwrap if face not in done_faces]
            #select final will be what we unwrap, but we will remember
            #in case we need to reselect
            #and select only those
            bpy.ops.mesh.select_all(action='DESELECT')
            for face in select_final:
                bm.faces[face].select = True
        else:
            select_final = select_for_unwrap
            
        #if we don't have any faces here, we already have uvs  
        if not select_final:
            self.report({'ERROR'}, "All selected faces already have UVs, either select new faces, or turn off Preserve UVs")
            return {'CANCELLED'}


        # Define a uv layer if one doesn't exist, or if generating a new map
        if uv_layer is None or newmap:
            bm.loops.layers.uv.new(f"DAWandUV_{len(obj.data.uv_layers)}")
            uv_layer = bm.loops.layers.uv.get(f"DAWandUV_{len(obj.data.uv_layers)-1}")
            mesh.uv_layers.active = obj.data.uv_layers[f"DAWandUV_{len(obj.data.uv_layers)-1}"]
            mesh.uv_layers[f"DAWandUV_{len(obj.data.uv_layers)-1}"].active_render = True



        if uvmode == "BLENDERUNWRAP":
            #Attempt to unwrap
            bpy.ops.uv.unwrap()
        elif uvmode == "SLIM":
            from util.util import SLIM

            soup = PolygonSoup.from_obj(os.path.join(dir_path, 'tempobj.obj'))
            polymesh = Mesh(soup.vertices, soup.indices)
            subvs, subfs = polymesh.export_submesh(select_final)

            v_to_subv = np.zeros(len(polymesh.vertices), dtype=int)
            v_to_subv[polymesh.faces[select_final].flatten()] = subfs.flatten()

            try:
                slimuv, slimenergy = SLIM(subvs, subfs)
            except:
                self.report({'ERROR'}, "SLIM unwrap failed, likely because it was unable to solve islands")
                return {'CANCELLED'}

            uv_layer = bm.loops.layers.uv.active

            for fi in select_final:
                face = bm.faces[fi]
                for loop in face.loops:
                    v = loop.vert
                    subv = v_to_subv[v.index]
                    loop[uv_layer].uv = slimuv[subv]

        if freeze and not newmap:
             for face in select_for_unwrap:
                bm.faces[face].select = True
        
        bmesh.update_edit_mesh(mesh)

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
    icon = os.path.join(dir_path, 'wand.wand')
    bl_icon = icon
    #sets the functionality
    bl_keymap = (
       ('object.modal_operator', {'type': 'LEFTMOUSE', 'value': 'CLICK'}, {'properties': []}),
       )

class DA_Menu(bpy.types.Panel):
    #other UI - hopefully will open up on click
    bl_label = "DAWand Options"
    bl_idname = "DA_PT_Menu"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'DA Wand'

    def draw(self, context):
        layout = self.layout

        wm = context.window_manager

        row = layout.row()
        row.label(text="Segmentation Options")

        row = layout.row()
        row.prop(wm, 'floodfill')

        row = layout.row()
        row.prop(wm, 'graphcuts')

        row = layout.row()
        row.operator(Clear_Sel.bl_idname, text="Clear Selection")
        row.operator(Clear_UV.bl_idname, text="Clear UVs")

        row = layout.row()
        row.operator(Clear_Anchors.bl_idname, text="Clear Selection and UVs")

        row = layout.row()
        row.label(text="Unwrap options")

        layout.prop(wm, "uv_mode")

        row = layout.row()
        row.prop(wm, 'newmap')

        row = layout.row()
        row.prop(wm, 'freeze')

        row = layout.row()
        row.operator(Unwrap.bl_idname, text="Unwrap")

        if wm.progress > 0:
            row = layout.row()
            step = steps(int(wm.progress / 20))
            row.label(text=f"{step.name}...")
            row = layout.row()
            row.prop(wm, 'progress', slider=True)


def register_properties():
    bpy.types.WindowManager.floodfill = BoolProperty(name='Flood Fill', default=True,
                                                    description='Fills gaps, leave on for best results')
    bpy.types.WindowManager.graphcuts = BoolProperty(name='Graph Cuts', default=True,
                                                     description='Clamps the boundary to sharp edges, leave on for best results')
    bpy.types.WindowManager.uv_mode = EnumProperty(
        name="",
        description = "select an option",
        items = [
            ('BLENDERUNWRAP', 'Blender Unwrap', "Uses Blender's built-in unwrap"),
            ('SLIM', 'Slim', 'Uses SLIM Unwrap'),
        ]
    )

    bpy.types.WindowManager.newmap = BoolProperty(name='Generate New UVMap', default=False,
                                            description='Generates a new UVmap on unwrap')

    bpy.types.WindowManager.freeze = BoolProperty(name='Preserve Current UVs', default=False,
                                             description='If checked, this will only unwrap the new selection, preserving the UVs from previous unwraps')
    
    bpy.types.WindowManager.progress = FloatProperty(name="Total Progress", default=0,
                                                                     description='Progress of selection',
                                                                     min=0, max=100,
                                                                     options={'HIDDEN', 'SKIP_SAVE'}, precision = 0
                                                                     )

def unregister_properties():
    del bpy.types.WindowManager.floodfill
    del bpy.types.WindowManager.graphcuts
    del bpy.types.WindowManager.uv_mode
    del bpy.types.WindowManager.newmap
    del bpy.types.WindowManager.freeze
    del bpy.types.WindowManager.progress