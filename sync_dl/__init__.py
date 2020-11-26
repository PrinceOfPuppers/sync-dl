import os
import logging

import argparse

import shelve

from sync_dl.plManagement import correctStateCorruption
import sync_dl.config as cfg

from sync_dl.commands import newPlaylist,smartSync,appendNew,manualAdd,move,swap, showPlaylist, compareMetaData
    
#modified version of help formatter which only prints args once in help message
class ArgsOnce(argparse.HelpFormatter):
    def __init__(self,prog):
        super().__init__(prog,max_help_position=40)

    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return metavar
        else:
            parts = []

            if action.nargs == 0:
                parts.extend(action.option_strings)

            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    parts.append('%s' % option_string)
                parts[-1] += ' %s'%args_string
            return ', '.join(parts)


def parseArgs():
    description = ("A tool for downloading and syncing remote playlists to your computer. Created to avoid having\n"
                    "music deleted but still have the convenience of browsing and adding and reordering new music using\n"
                    "remote services such as youtube.")


    parser = argparse.ArgumentParser(description=description,formatter_class=ArgsOnce)

    #posistional
    parser.add_argument('PLAYLIST',nargs='?', type=str, help='the name of the directory for the playlist')

    #playlist managing
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-n','--new-playlist', metavar='URL', type=str, help='downloads new playlist from URL with name PLAYLIST')
    group.add_argument('-s','--smart-sync', action='store_true', help='apply smart sync local playlist with remote playlist')
    group.add_argument('-a','--append-new', action='store_true', help='append new songs in remote playlist to end of local playlist')

    group.add_argument('-M','--manual-add',nargs=2, metavar=('PATH','INDEX'), type=str, help = 'manually add song at PATH to playlist in posistion INDEX')

    group.add_argument('-m','--move',nargs=2, metavar=('I1','I2'), type = int, help='moves song index I1 to I2 in local playlist')
    group.add_argument('-w','--swap',nargs=2, metavar=('I1','I2'), type = int, help='swaps order of songs index I1 and I2')
    
    
    parser.add_argument('-l','--local-dir',metavar='PATH',type=str, help='sets local music directory to PATH, overrides current working directory and manages playlists in PATH in the future' )
    
    parser.add_argument('-v','--verbose',action='store_true', help='runs application in verbose mode' )
    parser.add_argument('-q','--quiet',action='store_true', help='runs application with no print outs' )

    #info 
    parser.add_argument('-p','--print',action='store_true', help='prints out playlist metadata information compared to remote playlist information' )
    parser.add_argument('-d','--view-metadata',action='store_true', help='prints out playlist metadata information compared to remote playlist information' )

    args = parser.parse_args()
    return args

def setLogging(args):
    '''sets logging level based on verbosity'''
    #verbosity
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]
        )
    elif args.quiet:
        logging.basicConfig(level=logging.ERROR,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]
        )
    else:
        logging.basicConfig(level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler()]
        )

def getCwd(args):
    #setting and getting cwd
    if args.local_dir:
        if not os.path.exists(args.local_dir):
            logging.error("Provided Music Directory Does not Exist")
            exit()
        #saves args.local_dir to config
        music = os.path.abspath(args.local_dir)


        cfg.parser.set('DEFAULT','musicDir',music)
        with open(f'{cfg.modulePath}/config.ini', 'w') as configfile:
            cfg.parser.write(configfile)

        cfg.musicDir = music

    if cfg.musicDir == '':
        return os.getcwd()
    else:
        return cfg.musicDir


def playlistExists(plPath):
    '''tests if valid playlist with metadata file exists at provided path'''
    #everything past this point only works if the playlist exists
    if not os.path.exists(plPath):
        logging.error(f"Directory {plPath} Doesnt Exist")
        return False
    
    if not os.path.exists(f'{plPath}/{cfg.metaDataName}'):
        logging.error(f"No Playlist Exists at {plPath}, Could not Find Metadata")
        return False
    return True



def main():
    args = parseArgs()

    setLogging(args)

    cwd = getCwd(args)


    # if no playlist was provided all further functions cannot run
    if args.PLAYLIST:
        plPath = f"{cwd}/{args.PLAYLIST}"
    else:
        if not args.local_dir: #only option which can run without playlist
            logging.error("Playlist Name Required")
        exit()

    if args.new_playlist: 
        newPlaylist(plPath,args.new_playlist)


    if not playlistExists(plPath):
        exit()


    #viewing playlist     
    if args.print:
        with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            showPlaylist(metaData,print,plPath,"https://www.youtube.com/watch?v=")

    if args.view_metadata:
        with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            compareMetaData(metaData,print)



    #playlist managing
    try:
        #smart syncing
        if args.smart_sync:
            smartSync(plPath)

        #appending
        elif args.append_new:
            appendNew(plPath)

        #manual adding
        elif args.manual_add:
            if not args.manual_add[1].isdigit():
                logging.error("Index must be positive Integer")
            else:

                manualAdd(plPath,args.manual_add[0],int(args.manual_add[1]))

        #moving/swaping songs
        elif args.move:
            move(plPath,args.move[0],args.move[1])

        elif args.swap:
            swap(plPath,args.swap[0],args.swap[1])

    #fixing metadata corruption in event of crash
    except Exception as e:
        logging.exception(e)
        correctStateCorruption(plPath)
        logging.info("State Recovered")