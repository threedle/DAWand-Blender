# DA Wand for Blender v0.3

### What's New
 - Added new 'overwrite' and 'extension' modes
 - Install should be better BUT reload isn't working anymore, so you must restart Blender if you want to change any code

### Installation
Two ways to install

First, clone this repo or download it as a .zip and extract

*Option 1 - Direct Blender Install (preferred)*
 1. Open Blender
 2. Open the addons menu (Edit->Preferences->Add-ons)
 3. Click 'install' in the top right
 4. Navigate DA_Wand_Blender and open DA_Wand.zip
 5. You may have to restart Blender

*Option 2 - Blender File Paths (ideal for adjusting the code)*
 1. Move the DA_Wand folder inside the DA_Wand_Blender to a new or existing 'my_scripts/addons' folder (it must be named this)
 2. If you haven't already, set your file paths to this my_scripts folder

After either of these has been done, go back to Edit->Preferences->Add-ons and search for "DA_Wand"

Click the check next to DA_Wand, if you get a circular import error, just click again.

At this point, a box that says "Install Dependencies" should appear. Click this to install DAWand's dependencies to Blender's Python - this may take a second, but the box should grey out

**NOTE:** If there is an error raised with the pygco install, then make sure you have python installed on your base system (e.g. brew install python), and that the system "Python.h" file can be found through setting the C_INCLUDE_PATH environment variable (**the Python version must match the Blender python version**). See [this link.](https://stackoverflow.com/questions/35778495/fatal-error-python-h-file-not-found-while-installing-opencv)


### Usage
1. Load in any triangle mesh, and press tab to enter Edit mode
2. There should be a wand in the tools on the left, select it to get started.
3. Click on a face to select the region.
3. If you want to see the new options, press 'n' or click the tiny left-facing arrow in the top right, and find DA_Wand.

### Credits
Want to acknowledge all of the non-docs sources that were extremely helpful in getting this set up!

Rignet (pretty much everywhere):
 - https://devtalk.blender.org/t/neural-rigging-for-blender-with-rignet/19708

Creating a tool:
 - https://b3d.interplanety.org/en/creating-custom-tool-in-blender/

Working with bmesh:
 - https://b3d.interplanety.org/en/finding-nearby-faces/

Debugging:
 - https://blender.stackexchange.com/a/142317

Dependency installation:
 - https://blender.stackexchange.com/questions/168448/bundling-python-library-with-addon
 - https://github.com/robertguetzkow/blender-python-examples/blob/master/add_ons/install_dependencies/install_dependencies.py

Initial package management:
 - https://stackoverflow.com/questions/70639689/how-to-use-the-anaconda-environment-on-blender
 - https://blender.stackexchange.com/questions/56011/how-to-install-pip-for-blenders-bundled-python

