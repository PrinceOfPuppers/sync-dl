About:
    An application for downloading and syncing remote playlists to your computer. Created to avoid having
    music deleted but still have the convenience of browsing and adding and reordering new music using 
    remote services such as youtube.

    the application does not store any metadata in songs, metadata is stored next to them in a .metadata
    file, the music files are managed through numbering, allowing them to be played alphanumerically using
    any playback service (such as VLC)


Smart Sync:
    Adds new music from remote playlist to local playlist, also takes ordering of remote playlist
    without deleting songs no longer available in remote playlist.

    songs that are no longer available in remote, will remain after the song they are currently after
    in the local playlist


Usage:
    syncdl [options] PLAYLIST

    where playlist is simply the name of the directory you wish to store the playlist in. playlist directory will
    always be in current working directory unless a music directory is specified using the -l, --local-dir option
    to hard set a music directory

Options:
    -h, --help                      prints help message

    -n, --new-playlist URL          downloads new playlist from URL with name PLAYLIST 

    -s, --smart-sync                apply smart sync local playlist with remote playlist

    -a, --append-new                append new songs in remote playlist to end of local playlist

    -M, --manual-add PATH INDEX     manually add song at PATH to playlist in posistion INDEX

    -m, --move I1 I2                moves song from I1 to I2 in local playlist

    -w, --swap I1 I2                swaps order of songs at I1 and I2

    -p, --print                     prints playlist information

    -d, --view-metadata             prints out playlist metadata information compared to remote playlist information

    -l, --local-dir PATH            sets local music directory to PATH, overrides current working directory and 
                                    manages playlists in PATH in the future
    
    -v, --verbose                   runs application in verbose mode

    -q, --quiet                     runs application with no print outs