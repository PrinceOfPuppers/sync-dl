<img align="left" width="80" height="80" src="https://raw.githubusercontent.com/PrinceOfPuppers/sync-dl/main/icon.png">

# sync-dl
<p>
<img src="https://img.shields.io/pypi/dm/sync-dl">
<img src="https://img.shields.io/pypi/l/sync-dl">
<img src="https://img.shields.io/pypi/v/sync-dl">
<img src="https://img.shields.io/badge/python-%E2%89%A53.6-blue">
<img src="https://travis-ci.com/PrinceOfPuppers/sync-dl.svg?branch=main">

</p>



> A tool for downloading and syncing remote playlists to your computer
- [INSTALLATION](#INSTALLATION)
- [ABOUT](#ABOUT)
- [USAGE](#USAGE)
- [EXAMPLE](#EXAMPLE)
- [DEVLOPMENT](#DEVLOPMENT)


# INSTALLATION
Requires ffmpeg or avconv, however one of these comes pre-installed on most machines. 

Install sync-dl via pypi using pip:
``` 
pip install sync-dl
```

# ABOUT
Created to avoid having music deleted but still have the convenience of browsing, adding and reordering new music using youtube.

The application does not store any of its metadata in songs, metadata is stored next to them in a .metadata file, the music files are managed through numbering, allowing them to be played alphanumerically using any playback service (such as VLC).


# Usage
```
sync-dl [options] COMMAND [options] PLAYLIST
```

sync-dl has the several subcommands, run `sync-dl -h` to see them all and `sync-dl [COMMAND] -h` to get info on a particular one.
As an example, here is the new command which creates new playlists from a youtube [URL]:

```
sync-dl new [URL] [PLAYLIST]
```

The playlist will be put it in directory [PLAYLIST], which is relative to the current working directory unless you specify your music directory using:

```
sync-dl config -l [PATH]
```

Where [PATH] is where you wish to store all your playlists in, ie) `~/Music`.


## Smart Sync:
The main feature of sync-dl:
```
sync-dl sync -s PLAYLIST
```

Adds new music from remote playlist to local playlist, also takes ordering of remote playlist
without deleting songs no longer available in remote playlist.

Songs that are no longer available in remote, will remain after the song they are currently after
in the local playlist to maintain playlist flow.


## Push Order:
```
sync-dl ytapi --push order [PLAYLIST]
```
sync-dl has a submodule which uses the youtube api the preform the reverse of Smart Sync called Push Order. sync-dl will prompt you to install the submodule if you use any of its options ie) --push-order. you must also sign in with google (so sync-dl can edit the order of your playlist).

For more information see https://github.com/PrinceOfPuppers/sync-dl-ytapi

## Many More!
Includes tools managing large playlists, For example `sync-dl edit --move-range [I1] [I2] [NI] [PLAYLIST]` which allows a user to move a block of songs From [I1] to [I2] to after song [N1].

Moving large blocks of songs on youtube requires dragging each song individually up/down a the page as it trys to dynamically load the hunders of songs you're scrolling past, which you would have to do every time you would want to add new music to somewhere other than the end of the playlist... (ask me how I know :^P)


# EXAMPLE
```
sync-dl config -l my/local/music/folder
```
Will use my/local/music/folder to store and manipulate playlists in the future.
```
sync-dl new https://www.youtube.com/playlist?list=PL-lQgJ3eJ1HtLvM6xtxOY_1clTLov0qM3 sweetJams
```
Will create a new playlist at my/local/music/folder/sweetJams and
download the playlist at the provided url to it.

```
sync-dl timestamps --scrape-range 0 4 sweetJams
```
Will scrape youtube comments for timestamps to add to songs 0 to 4 of sweetJams. Will ask you to review them before it adds them (can be changed with option -a).

```
sync-dl edit -m 1 5 sweetJams
```
Will move song number 1 in the playlist to position 5.

```
sync-dl sync -a sweetJams
```
Will check for any new songs in the remote playlist and append them to the end of sweetJams.

```
sync-dl sync -s sweetJams
```
Will use smart sync on sweetJams, downloading new songs from the remote playlist and reordering the playlist to match the order of the remote playlist without deleting any songs that are no longer available.

```
sync-dl edit --move-range 0 4 8 sweetJams
```
Will move all songs from 0 to 4 to after song 8.

```
sync-dl info -p sweetJams
```
Will give you all the urls for the songs in sweetJams.

```
sync-dl ytapi --push-order sweetJams
```
Will prompt you to install sync-dl-ytapi and sign in with google (if you havent already), after doing so it will push the local order of the playlist to youtube.

```
sync-dl ytapi --logout
```
Will remove invalidate and delete access and refresh token for the youtube api, requiring you to log in next time you use `sync-dl ytapi --pushorder`.


# DEVLOPMENT
To build for devlopment run:
```
git clone https://github.com/PrinceOfPuppers/sync-dl.git

cd sync-dl

pip install -e .
```
This will build and install sync-dl in place, allowing you to work on the code without having to reinstall after changes.


## Automated Testing
```
python test.py [options] TEST_PLAYLIST_URL
```
Will run all unit and integration tests, for the integration tests it will use the playlist TEST_PLAYLIST_URL, options are -u and -i to only run the unit/integration tests respectively.

Testing requires sync-dl-ytapi to be installed aswell, and will test its helper functions.
