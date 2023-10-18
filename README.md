# DA Wand - Blender 0.2

### What's New
-Reorganized much of the code in __init__.py and ronteractive2.py
-Added graphcuts and floodfill options (though still reloading the model each time)
-These can be accessed in the 'n' menu in Blender
-I *think* the circular import error has been fixed
-Improved install

### Installation
Two ways to install

*1*
Download this repo as a .zip
Open Blender
Open the addons menu (Edit->Preferences->Add-ons)
Click 'install' in the top right
Then open this zip file
You may have to restart Blender

*2*
Download this repo as a .zip and extract
Move the DA_Wand folder to your existing 'my_scripts/addons' folder
If you haven't already, set your file paths to this my_scripts folder

After either of these has been done:
Go back to Edit->Preferences->Add-ons
and search for "DA_Wand"

Click the check next to DA_Wand
At this point, a box that says "Install Dependencies" should appear
Click this to install DAWand's dependencies to Blender's Python
This may take a second, but the box should grey out

**NOTE:** If there is an error raised with the pygco install, then make sure you have python installed on your base system (e.g. brew install python), and that the system "Python.h" file can be found through setting the C_INCLUDE_PATH environment variable (**the Python version must match the Blender python version**). See [this link.](https://stackoverflow.com/questions/35778495/fatal-error-python-h-file-not-found-while-installing-opencv)


### Usage
Load in any triangle mesh, and press tab to enter Edit mode
There should be a wand in the tools on the left.
If you want to see the new options, press 'n' or click the tiny left-facing arrow in the top right, and find DA_Wand

### Credits
Want to acknowledge all of the non-docs sources that were extremely helpful in getting this set up!

Rignet (pretty much everywhere):
https://devtalk.blender.org/t/neural-rigging-for-blender-with-rignet/19708

Creating a tool:
https://b3d.interplanety.org/en/creating-custom-tool-in-blender/

Working with bmesh:
https://b3d.interplanety.org/en/finding-nearby-faces/

Debugging:
https://blender.stackexchange.com/a/142317

Dependency installation:
https://blender.stackexchange.com/questions/168448/bundling-python-library-with-addon
https://github.com/robertguetzkow/blender-python-examples/blob/master/add_ons/install_dependencies/install_dependencies.py

Initial package management:
https://stackoverflow.com/questions/70639689/how-to-use-the-anaconda-environment-on-blender
https://blender.stackexchange.com/questions/56011/how-to-install-pip-for-blenders-bundled-python

