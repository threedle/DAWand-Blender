## Hello
Hey everyone, here is the first working version of the interactive demo
of DAWAND in Blender

I have only tested on Blender 3.6 on my Mac, so would love to hear if it works
or if there are problems on other Blender versions and other machines

Also, if you actually use Blender often, let me know how the install process can be improved/compares
to other add-ons, as well as what you think the idea workflow for dawand integration should be
(right now it just adds a uv map on every click - i don't think that's ideal)

I also have no idea if this can use a gpu or not (probably not)

## Installation
Download the my_scripts file (it has to be named this way as far as I can tell)
If you already have other blender addons in a my_scripts folder, you should be able to move the
DA_wand folder into your addons folder within my_scripts

Open blender

Edit->Preferences->File Paths
There is slightly different UI in each blender version, but there should be something like
"script directories" or just "scripts", and set this to the my_scripts file you just downloaded

You may have to restart blender at this point

Then Edit->Preferences->Add-ons
and search for "DA_Wand"

Click the check next to DA_Wand

At this point, a box that says "Install Dependencies" should appear
Click this to install DAWand's dependencies to Blender's python
This may take a second, but the box should grey out

After this, you're all set!
Load in a triangle mesh, and enter either UV editing or Modeling and press tab to enter edit mode
And there *should* now be a wand in the tools on the left!
Click on the wand, then click on any face in your mesh
It may take a second, but it should select the correct faces
and unwrap them (you can see the UV map in UV Editing)

IF you get an error about circular imports when you click, try clicking again, sometimes it just doesn't work
for the first click

## Credits
Want to acknowledge all of the non-docs sources that were extremely helpful in getting this set up!
There are likely many more that I lost along the way

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


