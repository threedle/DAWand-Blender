# DA Wand for Blender v0.7.1

### What's New
 - adding loading bar
### TODO
 - Warning checking on Blender unwrap - it works on SLIM unwrap, but proved incredibly hard to tell when the blender unwrap fails (it returns FINISHED even when it fails)
 - test install on windows
 - figure out why there is an attribute error on a triangulated suzanne monkey

### Installation
Two ways to install

Download as a .zip

*Option 1 - Direct Blender Install (preferred)*
 1. Open Blender
 2. Open the addons menu (Edit->Preferences->Add-ons)
 3. Click 'install' in the top right
 4. Click DAWand-Blender-main.zip. 
 5. You may have to restart Blender

*Option 2 - Blender File Paths (ideal for adjusting the code)*
 1. Extract the .zip.  
 2. Move DAWand-Blender-main to a new or existing 'my_scripts/addons' folder (it must be named this)
 2. If you haven't already, set your file paths to this my_scripts folder

After either of these has been done, go back to Edit->Preferences->Add-ons and search for "DA Wand"

Click the check next to DA Wand, if you get a circular import error, just click again.

At this point, a box that says "Install Dependencies" should appear. Click this to install DAWand's dependencies to Blender's Python - this may take a second, but the box should grey out


### Usage
1. Load in any triangle mesh, and press tab to enter Edit mode
2. There should be a wand in the tools on the left, select it to get started.
3. Click on a face to select the region.
3. If you want to see the new options, press 'n' or click the tiny left-facing arrow in the top right, and find DA Wand.

### Code used for dependency install
https://github.com/robertguetzkow/blender-python-examples/blob/master/add_ons/install_dependencies/install_dependencies.py
