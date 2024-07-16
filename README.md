# DA Wand for Blender
Add-on that runs Richard Liu and 3DL's DAWand in Blender. (https://github.com/threedle/DA-Wand)

## Installation
1. Code -> Download ZIP
2. Open Blender
3. Open the addons menu (Edit->Preferences->Add-ons)
4. Click 'install' in the top right
5. Click DAWand-Blender-main.zip
6. You may have to restart Blender
7. Go back to Edit->Preferences->Add-ons and search for 'DA Wand'
8. Click the check next to DA Wand
9. Click 'Install Dependencies', which will take a few minutes to install. 

## Usage
1. Load in or create a triangle mesh. (You can triangulate any mesh using Blender's 'Triangulate Faces' option.
2. Put the mesh into edit mode by pressing <kbd>tab</kbd>, or go the UV editing workspace on Blender.
3. Press <kbd>n</kbd> to open the side panel, and click 'DAWand Options' to see the rest of the settings.
4. To get DAWand, find the Wand icon in the tools in Edit mode.
5. Click on a face to select the region.
6. Then, in the right-side settings menu, you can see more options and even unwrap the mesh.

## Credit  
Code used for dependency install:  
https://github.com/robertguetzkow/blender-python-examples/blob/master/add_ons/install_dependencies/install_dependencies.py

Much of the organization is based on Rignet's, so thanks to them:  
https://github.com/pKrime/brignet
