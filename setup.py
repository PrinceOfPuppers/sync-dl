import setuptools

setuptools.setup(
    name="sync-dl",
    version="0.0.1",
    author="Joshua McPherson",
    author_email="joshuamcpherson5@gmail.com",
    description="A tool for downloading and syncing remote playlists to your computer",
    url="https://github.com/PrinceOfPuppers/sync-dl",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=['youtube-dl'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    scripts=["sync_dl/sync-dl"]
)