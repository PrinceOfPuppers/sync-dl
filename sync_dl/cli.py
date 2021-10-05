import os
import logging

import argparse
import shelve

from sync_dl import __version__
from sync_dl.plManagement import correctStateCorruption
import sync_dl.config as cfg

from sync_dl.commands import newPlaylist,smartSync,appendNew,manualAdd,swap, showPlaylist, compareMetaData, moveRange, peek, togglePrepends, addTimestampsFromComments

# import optional modules, otherwise replace commands with stubs
try:
    from sync_dl_ytapi.commands import pushLocalOrder,logout

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

    def logout():
        installed = promptInstall()

        if not installed:
            return 
        from sync_dl_ytapi.commands import logout
        cfg.logger.info("----------------------------------")
        logout()

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

def getCwd():
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


def getPlPath(playlist):
    cwd = getCwd()

    return f"{cwd}/{playlist}"

def setupParsers():
    description = ("A tool for downloading and syncing remote playlists to your computer. Created to avoid having\n"
                    "music deleted but still have the convenience of browsing and adding and reordering new music using\n"
                    "remote services such as youtube.")

    parser = argparse.ArgumentParser(description=description,formatter_class=ArgsOnce)
    parser.add_argument('-v','--verbose',action='store_true', help='runs application in verbose mode' )
    parser.add_argument('-q','--quiet',action='store_true', help='runs application with no print outs' )
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    parser.add_argument('-f','--force-m4a', action='store_true', help='Will only download m4a, rather than seeking for best audio' )
    parser.set_defaults(func = lambda args: baseHandler(args, parser))

    subparsers = parser.add_subparsers()
    timestamps = subparsers.add_parser('timestamps', help='detect, add and remove tracks from songs', formatter_class=ArgsOnce)
    timestamps.add_argument('-s', '--scrape', nargs=1, metavar='I', type=int, help='detect tracks in pinned/top comments for song index I')
    timestamps.add_argument('-r', '--scrape-range', nargs=2, metavar=('I1','I2'), type=int, help='detect tracks in pinned/top comments for song index I1 to I2')
    timestamps.add_argument('PLAYLIST', type=str, help='the name of the directory for the playlist')
    timestamps.set_defaults(func = lambda args: timestampsHandler(args, timestamps))
    
    new = subparsers.add_parser('new', help='downloads new playlist from URL with name PLAYLIST', formatter_class=ArgsOnce)
    new.add_argument('URL', type=str, help='playlist URL')
    new.add_argument('PLAYLIST', type=str, help='the name of the directory for the playlist')
    new.set_defaults(func = lambda args: newHandler(args, new))

    sync = subparsers.add_parser("sync", help='smart sync playlist, unless options are added', formatter_class=ArgsOnce)
    sync.add_argument('-s','--smart-sync', action='store_true', help='smart sync local playlist with remote playlist')
    sync.add_argument('-a','--append-new', action='store_true', help='append new songs in remote playlist to end of local playlist')
    sync.add_argument('PLAYLIST', type=str, help='the name of the directory for the playlist')
    sync.set_defaults(func = lambda args: syncHandler(args, sync))


    edit = subparsers.add_parser("edit", help='change order of local playlist', formatter_class=ArgsOnce)
    edit.add_argument('-M','--manual-add',nargs=2, metavar=('PATH','INDEX'), type=str, help = 'manually add song at PATH to playlist in position INDEX')
    edit.add_argument('-m','--move',nargs=2, metavar=('I1','NI'), type = int, help='makes song index I1 come after NI (NI=-1 will move to start)')
    edit.add_argument('-r','--move-range',nargs=3, metavar=('I1','I2','NI'), type = int, help='makes songs in range [I1, I2] come after song index NI (NI=-1 will move to start)')
    edit.add_argument('-w','--swap',nargs=2, metavar=('I1','I2'), type = int, help='swaps order of songs index I1 and I2')
    edit.add_argument('-T','--toggle-prepends', action='store_true', help='toggles number prepends on/off')
    edit.add_argument('PLAYLIST', type=str, help='the name of the directory for the playlist')
    edit.set_defaults(func = lambda args: editHandler(args, edit))

    #changing remote
    ytapi = subparsers.add_parser("ytapi", help='push local playlist order to youtube playlist', formatter_class=ArgsOnce)
    ytapi.add_argument('--push-order', action='store_true', help='changes remote order to match local order (requires sign in with google)')
    ytapi.add_argument('--logout', action='store_true', help='revokes youtube oauth access tokens and deletes them')
    ytapi.add_argument('PLAYLIST', type=str, help='the name of the directory for the playlist')
    ytapi.set_defaults(func = lambda args: ytapiHandler(args, ytapi))

    config = subparsers.add_parser("config", help='change configuration', formatter_class=ArgsOnce)
    # the '\n' are used as defaults so they dont get confused with actual paths
    config.add_argument('-l','--local-dir', nargs='?',metavar='PATH',const='\n',type=str, help='sets music directory to PATH, manages playlists in PATH in the future. if no PATH is provided, prints music directory' )
    config.set_defaults(func= lambda args: configHandler(args, config))

    #info
    info = subparsers.add_parser("info", help='get info about playlist', formatter_class=ArgsOnce)
    info.add_argument('-p','--print',action='store_true', help='shows song titles and urls for local playlist' )
    info.add_argument('-d','--diff',action='store_true', help='shows differences between local and remote playlists' )
    info.add_argument('--peek',nargs='?',metavar='FMT', const=cfg.defualtPeekFmt, type=str, help='prints remote PLAYLIST (url or name) without downloading, optional FMT string can contain: {id}, {url}, {title}, {duration}, {uploader}')
    info.add_argument('PLAYLIST',nargs='?', type=str, help='the name of the directory for the playlist')
    info.set_defaults(func = lambda args: infoHandler(args, info))

    args = parser.parse_args()
    return args

def baseHandler(_,parser):
    parser.print_help()

def newHandler(args,_):
    plPath = getPlPath(args.PLAYLIST)
    if os.path.exists(plPath):
        cfg.logging.error(f"Cannot Make Playlist {args.PLAYLIST} Because Directory Already Exists at Path: \n{plPath}")
        return
    newPlaylist(plPath, args.URL)



def syncHandler(args,parser):
    plPath = getPlPath(args.PLAYLIST)
    if not playlistExists(plPath):
        return

    #smart syncing
    if args.smart_sync:
        smartSync(plPath)

    #appending
    elif args.append_new:
        appendNew(plPath)

    else:
        parser.print_help()
        cfg.logger.error("Please Select an Option")



def configHandler(args,parser):
    if args.local_dir:
        if args.local_dir == '\n':
            if cfg.musicDir=='':
                cfg.logger.error("Music Directory Not Set, Set With: sync-dl config -l PATH")
            else:
                cfg.logger.info(cfg.musicDir)
            return
        if not os.path.exists(args.local_dir):
            cfg.logger.error("Provided Music Directory Does not Exist")
            return
        #saves args.local_dir to config
        music = os.path.abspath(args.local_dir)

        cfg.writeToConfig('musicDir',music)
        cfg.musicDir = music

    else:
        parser.print_help()
        cfg.logger.error("Please Select an Option")


def editHandler(args,parser): 

    plPath = getPlPath(args.PLAYLIST)
    if not playlistExists(plPath):
        return

    if args.move:
        moveRange(plPath,args.move[0],args.move[0],args.move[1])
    
    elif args.move_range:
        moveRange(plPath,args.move_range[0],args.move_range[1],args.move_range[2])

    elif args.swap:
        swap(plPath,args.swap[0],args.swap[1])

    elif args.manual_add:
        if not args.manual_add[1].isdigit():
            cfg.logger.error("Index must be positive Integer")
        else:
            manualAdd(plPath,args.manual_add[0],int(args.manual_add[1]))

    # if no options are selected, show help
    elif not args.toggle_prepends:
        parser.print_help()
        cfg.logger.error("Please Select an Option")

    if args.toggle_prepends:
        togglePrepends(plPath)


def ytapiHandler(args,parser):
    if args.logout:
        logout()
        return

    plPath = getPlPath(args.PLAYLIST)
    if not playlistExists(plPath):
        return

    if args.push_order:
        pushLocalOrder(plPath)

    else:
        parser.print_help()
        cfg.logger.error("Please Select an Option")

def infoHandler(args,parser):
    if args.peek:
        if not args.PLAYLIST:
            if args.peek != cfg.defualtPeekFmt: #removes the need to have posistional args before empty nargs='?' option
                url = args.peek
                fmt = cfg.defualtPeekFmt
            else:
                cfg.logger.error("Playlist URL Required")
                return
        else:
            url = args.PLAYLIST
            fmt = args.peek

        peek(url,fmt)
        return

    # if no playlist was provided all further functions cannot run
    if not args.PLAYLIST:
        cfg.logger.error("Playlist Name Required")
        return

    plPath = getPlPath(args.PLAYLIST)
    if not playlistExists(plPath):
        return

    #viewing playlist     
    if args.print:
        showPlaylist(plPath)

    if args.diff:
        compareMetaData(plPath)

    if (not args.print) and (not args.diff):
        parser.print_help()
        cfg.logger.error("Please Select an Option")

def timestampsHandler(args,parser):
    plPath = getPlPath(args.PLAYLIST)
    if not playlistExists(plPath):
        return

    if args.scrape:
        addTimestampsFromComments(plPath, args.scrape[0], args.scrape[0])
    
    elif args.scrape_range:
        addTimestampsFromComments(plPath, args.scrape_range[0], args.scrape_range[1])

    else:
        parser.print_help()
        cfg.logger.error("Please Select an Option")

def cli():
    '''
    Runs command line application, talking in args and running commands
    '''
    args = setupParsers()

    if args.force_m4a:
        cfg.params["format"] = 'm4a'

    setupLogger(args)

    try:
        args.func(args)

    except Exception as e:
        cfg.logger.exception(e)
        if args.PLAYLIST:
            plPath = getPlPath(args.PLAYLIST)
            metaDataPath = f"{plPath}/{cfg.metaDataName}"
            if os.path.exists(metaDataPath):
                with shelve.open(metaDataPath, 'c',writeback=True) as metaData:
                    correctStateCorruption(plPath,metaData)
                cfg.logger.info("State Recovered")
