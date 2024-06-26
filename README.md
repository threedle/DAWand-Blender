# DA Wand for Blender v0.6

### What's New
 - rearranged everything, now a dedicated 'unwrap button' with multiple modes
 - clear selection, clear uvs, and clear both buttons added (and they work)
 - Preserve UVs and Generate new map both working, will now not overwrite your UVs
 - TODO
 - Slight bug after clearing UVs where the UV map will be full of nans and the unwrap will fail without throwing an error.
 - Improve tooltips (get rid of undocumented operators)
 - clean up errors on launch (PT error and deselect all)
 - test install (though I think it's better now that there's no pygco)
 - clean up code and menus (I don't like DA_Wand, probably should rename)
 - maybe test on Blender 4.0
 - oh also maybe see if circular import is still happening or not
 - SLIM NOT WORKING??!?!?

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

