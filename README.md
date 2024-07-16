# DA Wand for Blender v0.7.2

### What's New
 - loading bar done
### TODO
 - Warning checking on Blender unwrap - it works on SLIM unwrap, but proved incredibly hard to tell when the blender unwrap fails (it returns FINISHED even when it fails)
 - test install on windows
 - figure out why there is an attribute error on a triangulated suzanne monkey

## Installation
1. Code -> Download ZIP
2. Open Blender
3. Open the addons menu (Edit->Preferences->Add-ons)
4. Click 'install' in the top right
5. Click DAWand-Blender-main.zip
6. You may have to restart Blender
7. Go back to Edit->Preferences->Add-ons and search for "DA Wand"
8. Click the check next to DA Wand
9. Click 'Install Dependencies', which will take a couple minutes to install. 

### Usage
1. Load in any triangle mesh, and press tab to enter Edit mode
2. There should be a wand in the tools on the left, select it to get started.
3. Click on a face to select the region.
3. If you want to see the new options, press 'n' or click the tiny left-facing arrow in the top right, and find DA Wand.

### Code used for dependency install
https://github.com/robertguetzkow/blender-python-examples/blob/master/add_ons/install_dependencies/install_dependencies.py
