import setuptools
from ntpath import dirname

with open('README.md', 'r') as f:
    longDescription = f.read()

# single sourcing version number to __init__.py
def getVersion(pkgDir):
    currentPath = dirname(__file__)
    initPath = f"{currentPath}/{pkgDir}/__init__.py"

    with open(initPath) as f:
        for line in f.readlines():
            if line.startswith("__version__"):
                delim = '"' if '"' in line else "'"
                return line.split(delim)[1]
    
        else:
            raise RuntimeError("Unable to find version string.")
    
setuptools.setup(
    name="sync-dl",
    version=getVersion("sync_dl"),
    author="Joshua McPherson",
    author_email="joshuamcpherson5@gmail.com",
    description="A tool for downloading and syncing remote playlists to your computer",
    long_description = longDescription,
    long_description_content_type = 'text/markdown',
    url="https://github.com/PrinceOfPuppers/sync-dl",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=['yt-dlp', 'sync-dl-ytapi>=1.1.2'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
    ],
    python_requires='>=3.6',
    scripts=["bin/sync-dl"],
    entry_points={
        'console_scripts': ['sync-dl = sync_dl:main'],
    },
)


