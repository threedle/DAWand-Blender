import torch
from .networks import define_classifier
import os
from os.path import join
import numpy as np
from pathlib import Path
from .layers.meshing.mesh import Mesh
torch.autograd.set_detect_anomaly(False)

class DAWand:
    """ Conditional mesh segmentation """
    def __init__(self, opt):
        self.opt = opt
        self.gpu_ids = opt.gpu_ids
        self.is_train = opt.is_train
        self.device = torch.device('cuda:{}'.format(
            self.gpu_ids[0])) if self.gpu_ids else torch.device('cpu')
        self.machine = "gpu" if self.gpu_ids else "cpu"
        self.save_dir = join(opt.export_save_path, opt.name)
        self.network_load_dir = opt.network_load_path

        # Create save directory
        Path(self.save_dir).mkdir(parents=True, exist_ok=True)

        self.optimizer = None
        self.edge_features = None
        self.mesh = None
        self.input_nc = opt.input_nc

        # load/define networks
        self.net = define_classifier(opt, self.input_nc, opt.ncf, self.gpu_ids, opt.init_type, opt.init_gain)
        self.net.train(self.is_train)

        self.loss_fcn = torch.nn.BCELoss()
        if self.opt.loss == "ce":
            self.loss_fcn = torch.nn.CrossEntropyLoss()

        #### LOAD NETWORK
        try:
            self.load_network(opt.which_epoch, self.save_dir)
        except Exception as e:
            self.load_network(opt.which_epoch, self.network_load_dir)
        self.net.eval()

    def set_input(self, data):
        # NOTE: We assume the input data is already padded
        input_edge_features = np.stack(data['edge_features']) # B x F x E
        input_edge_features = torch.from_numpy((input_edge_features - data['mean'][0][None, :, None])/data['std'][0][None, :, None])
        input_edge_features = input_edge_features.float().to(self.device)
        skip_inputs = []

        self.anchor_fs = data['anchor_fs']
        self.anchor_fs_labels = None

        self.files = data['file']
        # NOTE: We build mesh here to avoid pickling issues
        meshdatas = data['meshdata']
        anchordatas = data['anchordata']
        augs = data['aug']
        self.mesh = []
        # Apply augs if necessary
        if self.opt.time:
            import time
            t0 = time.time()

        # NOTE: By default augs will be None
        # NOTE: Have to build mesh structure here because it is unpicklable
        for i in range(len(augs)):
            # NOTE: Building from serialization means arbitrary edge -> HE mapping
            mesh = Mesh(meshdata=meshdatas[i], meshname=os.path.splitext(self.files[i])[0])
            mesh.no = data['no'][i]
            mesh.export_dir = data['export_dir'][i]
            mesh.anchor_fs = data['anchor_fs'][i]

            # Anchor features
            for key, val in anchordatas[i].items():
                setattr(mesh, key, val)

            # Sometimes augmentations cause heat geodesic to compute NAs
            # Skip data in these cases
            if not torch.all(torch.isfinite(input_edge_features[i])):
                print(f"Warning: non-finite inputs found for mesh {mesh.no}. Skipping...")
                skip_inputs.append(i)
                continue

            self.mesh.append(mesh)

        # Skip bad inputs
        input_edge_features = input_edge_features[list(set(range(len(input_edge_features))).difference(set(skip_inputs)))]

        if self.opt.time:
            print(f"set_input: {time.time() - t0:0.5f}")

        # Edge case: all inputs skipped b/c non-finite
        if len(self.mesh) == 0:
            print(f"Warning: batch skipped because no finite inputs")
            return False

        # SET EDGE FEATURES
        self.edge_features = input_edge_features

        return True

    def forward(self, layer=None, export_pool=False):
        out, deep_features = self.net(self.edge_features, self.mesh, layer, export_pool=export_pool)

        if self.opt.time == True and torch.cuda.is_available():
            import time
            # Get GPU memory usage
            t = torch.cuda.get_device_properties(0).total_memory
            r = torch.cuda.memory_reserved(0)
            a = torch.cuda.memory_allocated(0)
            m = torch.cuda.max_memory_allocated(0)
            f = r-a  # free inside reserved
            print(f"{a/1024**3:0.3f} GB allocated. \nGPU max memory alloc: {m/1024**3:0.3f} GB. \nGPU total memory: {t/1024**3:0.3f} GB.\n")
            t0 = time.time()

        return out, deep_features

    ##################
    def load_optimizer(self, which_epoch):
        optim_filename = '%s_optim.pth' % which_epoch
        # NOTE: Network load dir will ONLY be used for finetuning
        if os.path.exists(join(self.save_dir, optim_filename)):
            try:
                load_path = join(self.save_dir, optim_filename)
                optim_state = torch.load(load_path, map_location=self.device)
                self.optimizer.load_state_dict(optim_state)
                print(f"Loaded optimizer from {optim_filename}")
            except Exception as e:
                print(e)
                print(f"Optimizer loading failed. Starting training from initial optimizer settings...")

    def load_network(self, which_epoch, loaddir):
        """load model from disk"""
        save_filename = '%s_net.pth' % which_epoch
        load_path = join(loaddir, save_filename)
        if os.path.exists(load_path):
            print('loading the model from %s' % load_path)
        else:
            raise ValueError(f"No saved model {load_path}")
        net = self.net
        if isinstance(net, torch.nn.DataParallel):
            net = net.module

        state_dict = torch.load(load_path, map_location=self.device)
        if hasattr(state_dict, '_metadata'):
            del state_dict._metadata
        net.load_state_dict(state_dict)

    def save_network(self, which_epoch, wipe=False):
        """save model to disk"""
        if wipe == True:
            import re
            # Wipe all previous epochs
            search = re.compile(r"\d+_[a-zA-Z]+.pth")
            deletefiles = list(filter(search.match, os.listdir(self.save_dir)))
            for file in deletefiles:
                os.unlink(os.path.join(self.save_dir, file))

        save_filename = '%s_net.pth' % (which_epoch)
        save_path = join(self.save_dir, save_filename)
        if len(self.gpu_ids) > 0 and torch.cuda.is_available():
            torch.save(self.net.module.cpu().state_dict(), save_path)
            self.net.cuda(self.gpu_ids[0])
        else:
            torch.save(self.net.cpu().state_dict(), save_path)

        # Also save the optimizer state
        if self.is_train == True:
            save_filename = '%s_optim.pth' % (which_epoch)
            save_path = join(self.save_dir, save_filename)
            torch.save(self.optimizer.state_dict(), save_path)

    def update_learning_rate(self):
        """update learning rate (called once every epoch)"""
        self.scheduler.step()
        lr = self.optimizer.param_groups[0]['lr']
        print('learning rate = %.7f' % lr)