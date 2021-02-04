import os
import sys
import logging

import argparse
import pkg_resources
import shelve


from sync_dl.plManagement import correctStateCorruption
import sync_dl.config as cfg


from sync_dl.commands import newPlaylist,smartSync,appendNew,manualAdd,move,swap, showPlaylist, compareMetaData, moveRange, peek

# import optional modules, otherwise replace commands with stubs
try:
    from sync_dl_ytapi.commands import pushLocalOrder

except:
    def promptInstall():
        answer = input("Missing Optional Dependancies For This Command.\nWould You Like to Install Them? (y/n): ").lower()
        if answer!='y':
            return False

        try:
            import subprocess
            subprocess.run(["pip","install",'sync-dl-ytapi'],check=True)
        except:
            cfg.logger.error("Unable to Install Optional Dependancies")
            return False
        cfg.logger.info("Optional Dependancies Installed")
        return True
    
    #stubs 
    def pushLocalOrder(plPath):

        installed = promptInstall()

        if not installed:
            return 
        from sync_dl_ytapi.commands import pushLocalOrder
        cfg.logger.info("----------------------------------")
        pushLocalOrder(plPath)



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

    #positional
    parser.add_argument('PLAYLIST',nargs='?', type=str, help='the name of the directory for the playlist')

    plManagmentGroup = parser.add_argument_group("playlist management")
    plManagmentGroup = plManagmentGroup.add_mutually_exclusive_group() #makes plManagement mutually exclusive
    #playlist managing
    
    #group = parser.add_mutually_exclusive_group()

    plManagmentGroup.add_argument('-n','--new-playlist', metavar='URL', type=str, help='downloads new playlist from URL with name PLAYLIST')
    plManagmentGroup.add_argument('-s','--smart-sync', action='store_true', help='apply smart sync local playlist with remote playlist')
    plManagmentGroup.add_argument('-a','--append-new', action='store_true', help='append new songs in remote playlist to end of local playlist')

    plManagmentGroup.add_argument('-M','--manual-add',nargs=2, metavar=('PATH','INDEX'), type=str, help = 'manually add song at PATH to playlist in position INDEX')

    plManagmentGroup.add_argument('-m','--move',nargs=2, metavar=('I1','I2'), type = int, help='moves song index I1 to I2')
    plManagmentGroup.add_argument('-r','--move-range',nargs=3, metavar=('I1','I2','NI'), type = int, help='makes songs in range [I1, I2] come after song index NI (NI=-1 will move to start)')
    plManagmentGroup.add_argument('-w','--swap',nargs=2, metavar=('I1','I2'), type = int, help='swaps order of songs index I1 and I2')

    #changing remote
    apiGroup = parser.add_argument_group("youtube api")
    apiGroup.add_argument('--push-order', action='store_true', help='(experimental) changes remote order to match local order')
    

    configGroup = parser.add_argument_group("configuration")
    # the '\n' are used as defaults so they dont get confused with actual paths
    configGroup.add_argument('-l','--local-dir', nargs='?',metavar='PATH',const='\n',type=str, help='sets music directory to PATH, manages playlists in PATH in the future. if no PATH is provided, prints music directory' )
    
    #info
    infoGroup = parser.add_argument_group("info")
    infoGroup.add_argument('-v','--verbose',action='store_true', help='runs application in verbose mode' )
    infoGroup.add_argument('-q','--quiet',action='store_true', help='runs application with no print outs' )


    infoGroup.add_argument('-p','--print',action='store_true', help='prints out playlist metadata information compared to remote playlist information' )
    infoGroup.add_argument('-d','--view-metadata',action='store_true', help='prints out playlist metadata information compared to remote playlist information' )
    
    version = pkg_resources.require("sync_dl")[0].version
    infoGroup.add_argument('--version', action='version', version='%(prog)s ' + version)

    infoGroup.add_argument('--peek',nargs='?',metavar='FMT', const=cfg.defualtPeekFmt, type=str, help='prints remote PLAYLIST (url) without downloading, optional FMT string can contain: {id}, {url}, {title}, {duration}, {uploader}')





    args = parser.parse_args()
    return args

def setupLogger(args):
    '''sets cfg.logger level based on verbosity'''
    #verbosity
    stream = logging.StreamHandler()
    if args.verbose:
        cfg.logger.setLevel(logging.DEBUG)
        stream.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    elif args.quiet:
        cfg.logger.setLevel(logging.ERROR)
        stream.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    else:
        cfg.logger.setLevel(logging.INFO)
        stream.setFormatter(logging.Formatter("%(message)s"))
    cfg.logger.addHandler(stream)

def getCwd(args):
    #setting and getting cwd
    if args.local_dir:
        if args.local_dir == '\n':
            if cfg.musicDir=='':
                cfg.logger.critical("Music Directory Not Set, Set With: sync-dl -l PATH")
            else:
                cfg.logger.critical(cfg.musicDir)
            sys.exit()
        if not os.path.exists(args.local_dir):
            cfg.logger.error("Provided Music Directory Does not Exist")
            sys.exit()
        #saves args.local_dir to config
        music = os.path.abspath(args.local_dir)

        cfg.writeToConfig('musicDir',music)
        cfg.musicDir = music

    if cfg.musicDir == '':
        return os.getcwd()
    else:
        return cfg.musicDir


def playlistExists(plPath):
    '''tests if valid playlist with metadata file exists at provided path'''
    #everything past this point only works if the playlist exists
    if not os.path.exists(plPath):
        cfg.logger.error(f"Directory {plPath} Doesnt Exist")
        return False
    
    try:
        shelve.open(f'{plPath}/{cfg.metaDataName}').close()
    except:
        cfg.logger.error(f"No Playlist Exists at {plPath}, Could not Find Metadata")
        return False
    #if not os.path.exists(f'{plPath}/{cfg.metaDataName}'):
    #    cfg.logger.error(f"No Playlist Exists at {plPath}, Could not Find Metadata")
    #    return False
    return True


def cli():
    '''
    Runs command line application, talking in args and running commands
    '''
    args = parseArgs()

    setupLogger(args)

    cwd = getCwd(args)

    #peek command runs without PLAYLIST posistional argument
    if args.peek:
        if not args.PLAYLIST:

            if args.peek != cfg.defualtPeekFmt: #removes the need to have posistional args before empty nargs='?' option
                url = args.peek
                fmt = cfg.defualtPeekFmt
            else:
                cfg.logger.error("Playlist URL Required")
                sys.exit()
        else:
            url = args.PLAYLIST
            fmt = args.peek

        peek(url,fmt)
        sys.exit()

    # if no playlist was provided all further functions cannot run
    if args.PLAYLIST:
        plPath = f"{cwd}/{args.PLAYLIST}"
    else:
        if not args.local_dir: #only option which can run without playlist
            cfg.logger.error("Playlist Name Required")
        sys.exit()

    if args.new_playlist: 
        newPlaylist(plPath,args.new_playlist)
        sys.exit()

    if not playlistExists(plPath):
        sys.exit()


    #viewing playlist     
    if args.print:
        showPlaylist(plPath)

    if args.view_metadata:
        compareMetaData(plPath)



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
                cfg.logger.error("Index must be positive Integer")
            else:

                manualAdd(plPath,args.manual_add[0],int(args.manual_add[1]))

        #moving/swaping songs
        elif args.move:
            move(plPath,args.move[0],args.move[1])
        
        elif args.move_range:
            moveRange(plPath,args.move_range[0],args.move_range[1],args.move_range[2])

        elif args.swap:
            swap(plPath,args.swap[0],args.swap[1])
        
        elif args.push_order:
            pushLocalOrder(plPath)

    #fixing metadata corruption in event of crash
    except Exception as e:
        cfg.logger.exception(e)
        correctStateCorruption(plPath)
        cfg.logger.info("State Recovered")

    except: #sys.exit calls
        correctStateCorruption(plPath)
        cfg.logger.info("State Recovered")