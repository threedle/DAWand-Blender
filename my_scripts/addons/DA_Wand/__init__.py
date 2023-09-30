bl_info = {
    "name": "DA_Wand",
    "blender": (3, 6, 2),
    "category": "Object",
}

#not sure what this code does, but was recommended when making an addon
#so may be important :)
#but I commented it out because I was having issues with
#installing all the dependencies

# if "bpy" in locals():
#   import imp
#   imp.reload(data)
#   imp.reload(models)
#   imp.reload(util)
#   imp.reload(ronteractive2)
# else:
#   from . import util, data, models
#   from . import ronteractive2

import bpy
import bmesh
import os
import sys
import numpy as np

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
    global vertex_set
    # global done_faces

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
        #we do the import here so we can install the dependencies
        from . import ronteractive2 as rn
        obj = context.object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        #check if in edit mode and bm is valid (i.e. there is a selection)
        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Please enter Edit Mode.")
            return {'CANCELLED'}

        if len(bm.verts) == 0:
            self.report({'ERROR'}, "Please select a valid face.")
            return {'CANCELLED'}

        #deselect all
        bpy.ops.mesh.select_all(action='DESELECT')

        # Select the face under the mouse cursor
        bpy.ops.view3d.select(location=(self.mouse_x, self.mouse_y))

        # Get the selected bmesh face
        selected_face = None
        selected_fi = None
        for f in bm.faces:
            if f.select:
                #print(f.index)
                selected_face = f.index + len(bm.verts) #literally i have no clue
                selected_fi = f.index

        if selected_face is None:
            self.report({'ERROR'}, "Please select a valid face.")
            return {'CANCELLED'}

        #print(selected_face)
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

        mapping = rn.oncall(selected_face, 'tempobj.obj', dir_path, done_faces=done_faces)

        #I guess you need this now
        bm.faces.ensure_lookup_table()

        for i in range(len(bm.faces)):
            if mapping[i] == 1:
                bm.faces[i].select = True
                # done_faces.append(i)

        #delete the obj file
        #not using this now, going to keep the temp file
        #and just replace it every time you run
        # if os.path.isfile(target_file):
        #     os.remove(target_file)
        # else:
        #     # If it fails, inform the user.
        #     self.report({'ERROR'}, "Couldn't find temp files to delete")

        #then bmesh update
        bmesh.update_edit_mesh(mesh)

        #switch to back edit mode and show selection

        #add a new uvmap and unwrap to it
        # bpy.ops.mesh.uv_texture_add()
        bpy.ops.uv.unwrap()

    #modal operator, not using right now, but will be needed for mousemove functions
    # def modal(self, context, event):
    #     #not sure if using modal is going to be best long term
    #     #may need to call mark seams when invoked
    #     if event.type == 'LEFTMOUSE':  #On Click
    #         self.mark_seams_by_index(context)
    #         return {'FINISHED'}
    #     elif event.type == 'ESC':  #Should cancel
    #         return {'CANCELLED'}

    #     return {'RUNNING_MODAL'}

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



#from here on is the depedency install code

import subprocess
from collections import namedtuple

Dependency = namedtuple("Dependency", ["module", "package", "name"])

# Declare all modules that this add-on depends on, that may need to be installed. The package and (global) name can be
# set to None, if they are equal to the module name. See import_module and ensure_and_import_module for the explanation
# of the arguments. DO NOT use this to import other parts of your Python add-on, import them as usual with an
# "import" statement.
dependencies = (Dependency(module="wheel", package=None, name=None),
                Dependency(module="dill", package=None, name=None),
                Dependency(module="scipy", package=None, name=None),
                Dependency(module="matplotlib", package=None, name=None),
                Dependency(module="scikit-learn", package=None, name=None),
                Dependency(module="robust-laplacian", package=None, name=None),
                Dependency(module="potpourri3d", package=None, name=None),
                Dependency(module="pygco", package=None, name=None),
                Dependency(module="torch", package=None, name=None),
                )

dependencies_installed = False



def install_pip():
    """
    Installs pip if not already present. Please note that ensurepip.bootstrap() also calls pip, which adds the
    environment variable PIP_REQ_TRACKER. After ensurepip.bootstrap() finishes execution, the directory doesn't exist
    anymore. However, when subprocess is used to call pip, in order to install a package, the environment variables
    still contain PIP_REQ_TRACKER with the now nonexistent path. This is a problem since pip checks if PIP_REQ_TRACKER
    is set and if it is, attempts to use it as temp directory. This would result in an error because the
    directory can't be found. Therefore, PIP_REQ_TRACKER needs to be removed from environment variables.
    :return:
    """

    try:
        # Check if pip is already installed
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True)
    except subprocess.CalledProcessError:
        import ensurepip

        ensurepip.bootstrap()
        os.environ.pop("PIP_REQ_TRACKER", None)


def install_and_import_module(module_name, package_name=None, global_name=None):
    """
    Installs the package through pip and attempts to import the installed module.
    :param module_name: Module to import.
    :param package_name: (Optional) Name of the package that needs to be installed. If None it is assumed to be equal
       to the module_name.
    :param global_name: (Optional) Name under which the module is imported. If None the module_name will be used.
       This allows to import under a different name with the same effect as e.g. "import numpy as np" where "np" is
       the global_name under which the module can be accessed.
    :raises: subprocess.CalledProcessError and ImportError
    """
    if package_name is None:
        package_name = module_name

    if global_name is None:
        global_name = module_name

    # Blender disables the loading of user site-packages by default. However, pip will still check them to determine
    # if a dependency is already installed. This can cause problems if the packages is installed in the user
    # site-packages and pip deems the requirement satisfied, but Blender cannot import the package from the user
    # site-packages. Hence, the environment variable PYTHONNOUSERSITE is set to disallow pip from checking the user
    # site-packages. If the package is not already installed for Blender's Python interpreter, it will then try to.
    # The paths used by pip can be checked with `subprocess.run([bpy.app.binary_path_python, "-m", "site"], check=True)`

    # Create a copy of the environment variables and modify them for the subprocess call
    environ_copy = dict(os.environ)
    environ_copy["PYTHONNOUSERSITE"] = "1"
    print("package", package_name)
    subprocess.run([sys.executable, "-m", "pip", "install", package_name], check=True, env=environ_copy)



class EXAMPLE_OT_install_dependencies(bpy.types.Operator):
    bl_idname = "example.install_dependencies"
    bl_label = "Install dependencies"
    bl_description = ("Downloads and installs the required python packages for this add-on. "
                      "Internet connection is required. Blender may have to be started with "
                      "elevated permissions in order to install the package")
    bl_options = {"REGISTER", "INTERNAL"}

    @classmethod
    def poll(self, context):
        # Deactivate when dependencies have been installed
        return not dependencies_installed

    def execute(self, context):
        try:
            install_pip()
            for dependency in dependencies:
                install_and_import_module(module_name=dependency.module,
                                          package_name=dependency.package,
                                          global_name=dependency.name)
        except (subprocess.CalledProcessError, ImportError) as err:
            self.report({"ERROR"}, str(err))
            return {"CANCELLED"}

        global dependencies_installed
        dependencies_installed = True

        # Register the panels, operators, etc. since dependencies are installed
        bpy.utils.register_tool(DA_Icon, after={'builtin.scale_cage'}, separator=True, group=True)
        bpy.utils.register_class(OnClick)

        return {"FINISHED"}


class EXAMPLE_preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout
        layout.operator(EXAMPLE_OT_install_dependencies.bl_idname, icon="CONSOLE")


preference_classes = (EXAMPLE_OT_install_dependencies,
                      EXAMPLE_preferences)


def register():
    global dependencies_installed
    try:
        import dill
        import scipy
        import sklearn
        import robust_laplacian
        import potpourri3d
        import matplotlib
        import pygco
        import torch
    except:
        dependencies_installed = False
    else:
        dependencies_installed = True


    for cls in preference_classes:
        bpy.utils.register_class(cls)

    if dependencies_installed:
        bpy.utils.register_tool(DA_Icon, after={'builtin.scale_cage'}, separator=True, group=True)
        bpy.utils.register_class(OnClick)
    else:
        return

def unregister():
    for cls in preference_classes:
        bpy.utils.unregister_class(cls)

    if dependencies_installed:
        bpy.utils.unregister_class(OnClick)
        bpy.utils.unregister_tool(DA_Icon)


if __name__ == "__main__":
    register()