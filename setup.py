import setuptools

with open('README.md', 'r') as f:
    longDescription = f.read()

setuptools.setup(
    name="sync-dl",
    version="0.3.4",
    author="Joshua McPherson",
    author_email="joshuamcpherson5@gmail.com",
    description="A tool for downloading and syncing remote playlists to your computer",
    long_description = longDescription,
    long_description_content_type = 'text/markdown',
    url="https://github.com/PrinceOfPuppers/sync-dl",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=['youtube-dl'],
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


