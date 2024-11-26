#claude one-shot to generate python wheels

#run python3 wheeler.py to generate the wheels
#then make sure Blender is in your path
#then run Blender --command extension build --split-platforms

import os
import subprocess

def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    if process.returncode != 0:
        print(f"Error: {error.decode('utf-8')}")
    else:
        print(f"Output: {output.decode('utf-8')}")

def download_wheels(packages, platforms):
    wheel_dir = "./wheels"
    os.makedirs(wheel_dir, exist_ok=True)

    for package in packages:
        for platform in platforms:
            command = f"pip download {package} --only-binary=:all: --python-version 3.11 --platform {platform} -d {wheel_dir}"

            # No deps for libigl specifically
            if package == "libigl":
                command = f"pip download {package} --only-binary=:all: --python-version 3.11 --platform {platform} --no-deps -d {wheel_dir}"

            print(f"Downloading wheel for {package} on {platform}")
            run_command(command)

# packages = [
#     "dill==0.3.4",
#     "scipy==1.9.0",
#     "scikit-learn==1.5.2",
#     "robust-laplacian==0.2.4",
#     "potpourri3d==0.0.7",
#     "matplotlib==3.5.1",
#     "python-igraph==0.10.1",
#     "torch==1.11.0",
#     "libigl==2.5.1"
# ]

packages = [
    "dill",
    "scipy",
    "scikit-learn",
    "robust-laplacian",
    "potpourri3d",
    "matplotlib",
    "python-igraph",
    "torch",
    "libigl",
    "importlib_resources"
]

platforms = [
    "macosx_14_0_x86_64",  # macOS Intel
    "macosx_14_0_arm64",   # macOS Apple Silicon
    "manylinux2014_x86_64",  # Linux
    "win_amd64"            # Windows
]

download_wheels(packages, platforms)

print("Wheel download complete. Check the './wheels' directory for the downloaded wheels.")