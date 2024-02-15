bl_info = {
    "name": "DA_Wand",
    "blender": (3, 6, 2),
    "category": "Object",
}

import bpy
import os
import sys

#this is setup and dependency install
import subprocess
from collections import namedtuple

Dependency = namedtuple("Dependency", ["module", "package", "name"])

# Declare all modules that this add-on depends on, that may need to be installed. The package and (global) name can be
# set to None, if they are equal to the module name. See import_module and ensure_and_import_module for the explanation
# of the arguments. DO NOT use this to import other parts of your Python add-on, import them as usual with an
# "import" statement.
dependencies = (Dependency(module="dill", package=None, name=None),
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

        register()

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

    #if we've already registered them
    try:
        for cls in preference_classes:
            bpy.utils.register_class(cls)
    except ValueError:
        pass
    
    if dependencies_installed:
        from .ronteractive2 import OnClick, DA_Icon, DA_Menu, register_properties, unregister_properties
        
        bpy.utils.register_tool(DA_Icon, after={'builtin.scale_cage'}, separator=True, group=True)
        bpy.utils.register_class(OnClick)
        bpy.utils.register_class(DA_Menu)
        register_properties()
    else:
        return

def unregister():
    
    from .ronteractive2 import OnClick, DA_Icon, DA_Menu, register_properties, unregister_properties

    for cls in preference_classes:
        bpy.utils.unregister_class(cls)

    bpy.utils.unregister_class(OnClick)
    bpy.utils.unregister_tool(DA_Icon)
    bpy.utils.unregister_class(DA_Menu)
    unregister_properties()


if __name__ == "__main__":
    register()