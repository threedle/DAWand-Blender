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

def run_forward_pass(model, dataset, face_list, return_features=False):
    dataset.update_anchor(face_list)
    input_meta = dataset[0]
    input_meta = {key: [val] for key,val in input_meta.items()}

    model.set_input(input_meta)

    with torch.no_grad():
        preds, features = model.forward()

        if return_features:
            return preds, features
    return preds


#for this I basically just butchered the interactive.py code
#to get rid of the all of the polyscope options and any customization options
#will hopefully add back in all of the customization eventually
#basically just completely nuked the callback because I didn't know how it worked
#and it was just for the UI as far as could tell
#though I'm assuming it optimizes over many clicks
#will def have to add that funcitonality back in lol

def oncall(point, meshfile, meshdir, done_faces = None):

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
    opt.name = "dawand"
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

    # Set cache folder to meshfile name
    opt.cachefolder = f"{meshname}_cache"
    opt.operatorcachefolder = f"{meshname}_opcache"
    opt.anchorcachefolder = f"{meshname}_anchorcache"

    opt.overwritecache = True
    opt.overwriteopcache = True
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
    postprocess = ["gc", "ff"]
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

            # If done faces is passed, then remove all done faces from the selection
            if done_faces is not None:
                preds[done_faces] = 0

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

        return hard_preds
