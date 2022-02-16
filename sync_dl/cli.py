import os
import sys
import logging

import argparse
import shelve


from sync_dl import __version__, InterruptTriggered
from sync_dl.plManagement import correctStateCorruption
import sync_dl.config as cfg

from sync_dl.commands import newPlaylist,smartSync,appendNew,manualAdd,swap, showPlaylist, compareMetaData, moveRange, peek, togglePrepends, addTimestampsFromComments
from sync_dl.ytapiInterface import logout, pushLocalOrder, transferSongs



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
    stream = logging.StreamHandler(sys.stdout)
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
    except Exception as e:
        if e.args == (13, 'Permission denied') or e.__class__ == PermissionError:
            cfg.logger.error(f"Could Not Access Playlist at {plPath}, Permission Denined")
        else:
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
    parser.set_defaults(func = lambda args: baseHandler(args, parser))

    subparsers = parser.add_subparsers()
    timestamps = subparsers.add_parser('timestamps', help='detect, add and remove tracks from songs', formatter_class=ArgsOnce)
    timestamps.add_argument('-s', '--scrape', nargs=1, metavar='I', type=int, help='detect tracks in pinned/top comments for song index I')
    timestamps.add_argument('-r', '--scrape-range', nargs=2, metavar=('I1','I2'), type=int, help='detect tracks in pinned/top comments for song index I1 to I2')
    timestamps.add_argument('-a', '--auto-accept', action='store_true', help='automatically accept new timestamps')
    timestamps.add_argument('-o', '--overwrite', action='store_true', help='allow overwriting of existing timestamps, will be prompted')
    timestamps.add_argument('--auto-overwrite', action='store_true', help='allow overwriting of existing timestamps, will not be prompted to approve overwritng/accepting')

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
    ytapi.add_argument('--logout', action='store_true', help='revokes youtube oauth access tokens and deletes them')
    ytapi.add_argument('--push-order', nargs=1, metavar='PLAYLIST', type=str, help='changes remote order of PLAYLIST to match local order (requires sign in with google)')
    ytapi.set_defaults(func = lambda args: ytapiHandler(args, ytapi))

    #transfer
    ytapiSubParsers = ytapi.add_subparsers()
    transfer = ytapiSubParsers.add_parser("transfer", help="transfer songs between playlist on both local and remote", formatter_class=ArgsOnce)
    transfer.add_argument('-t','--transfer',nargs=2, metavar=('S1','DI'), type = int, help='makes SRC_PLAYLIST song index I1 come after DEST_PLAYLIST song index NI (NI=-1 will move to start)') 
    transfer.add_argument('-r','--transfer-range',nargs=3, metavar=('S1','S2','DI'), type = int, help='makes SRC_PLAYLIST songs in range [I1, I2] come after DEST_PLAYLIST song index NI (NI=-1 will move to start)') 
    transfer.add_argument('SRC_PLAYLIST', type=str, help='the name of the playlist to transfer songs from')
    transfer.add_argument('DEST_PLAYLIST', type=str, help='the name of the playlist to transfer songs to')
    transfer.set_defaults(func = lambda args: transferHandler(args, transfer))


    config = subparsers.add_parser("config", help='change configuration (carries over between runs)', formatter_class=ArgsOnce)
    # the '\n' are used as defaults so they dont get confused with actual paths
    config.add_argument('-l','--local-dir',nargs='?',metavar='PATH',const='\n',type=str,help='sets music directory to PATH, manages playlists in PATH in the future. if no PATH is provided, prints music directory')
    config.add_argument('-f','--audio-format',nargs='?',metavar='FMT',const='\n',type=str,help='sets audio format to FMT (eg bestaudio, m4a, mp3, aac). if no FMT is provided, prints current FMT')
    config.add_argument('--list-formats',action='store_true', help='list all acceptable audio formats')
    config.add_argument('-t', '--toggle-timestamps', action='store_true', help='toggles automatic scraping of comments for timestamps when downloading')
    config.add_argument('-T', '--toggle-thumbnails', action='store_true', help='toggles embedding of thumbnails on download')
    config.add_argument('-s', '--show-config', action='store_true', help='shows current configuration')
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

    if args.audio_format:
        if args.audio_format == '\n':
            cfg.logger.info(cfg.audioFormat)
            return
        fmt = args.audio_format.lower()
        if fmt not in cfg.knownFormats:
            cfg.logger.error(f"Unknown Format: {fmt}\nKnown Formats Are: {', '.join(cfg.knownFormats)}")
            return

        if fmt != 'best' and not cfg.testFfmpeg():
            cfg.logger.error("ffmpeg is Required to Use Audio Format Other Than 'best'")
            return

        cfg.writeToConfig('audioFormat', fmt)
        cfg.setAudioFormat()
        cfg.logger.info(f"Audio Format Set to: {cfg.audioFormat}")

    if args.list_formats:
        cfg.logger.info(' '.join(cfg.knownFormats))

    if args.toggle_thumbnails:
        if cfg.embedThumbnail:
            cfg.writeToConfig('embedThumbnail', '0')
            cfg.setEmbedThumbnails()
        else:
            cfg.writeToConfig('embedThumbnail', '1')
            cfg.setEmbedThumbnails()

        if cfg.embedThumbnail:
            cfg.logger.info("Embedding Thumbnails: ON")
        else:
            cfg.logger.info("Embedding Thumbnails: OFF")

    if args.toggle_timestamps:
        cfg.autoScrapeCommentTimestamps = not cfg.autoScrapeCommentTimestamps
        if cfg.autoScrapeCommentTimestamps:
            cfg.logger.info("Automatic Comment Timestamp Scraping: ON")
        else:
            cfg.logger.info("Automatic Comment Timestamp Scraping: OFF")

        cfg.writeToConfig('autoScrapeCommentTimestamps', str(int(cfg.autoScrapeCommentTimestamps)))

    if args.show_config:
        cfg.logger.info(f"(-l) (--local-dir):         {cfg.musicDir}")

        cfg.logger.info(f"(-f) (--audio-format):      {cfg.audioFormat}")

        if cfg.autoScrapeCommentTimestamps:
            cfg.logger.info("(-t) (--toggle-timestamps): ON")
        else:
            cfg.logger.info("(-t) (--toggle-timestamps): OFF")

        if cfg.embedThumbnail:
            cfg.logger.info("(-T) (--toggle-thumbnails): ON")
        else:
            cfg.logger.info("(-T) (--toggle-thumbnails): OFF")

    if not (args.toggle_timestamps or args.local_dir or args.audio_format or args.list_formats or args.toggle_thumbnails or args.show_config):
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

    if args.push_order:

        plPath = getPlPath(args.push_order[0])
        if not playlistExists(plPath):
            return

        pushLocalOrder(plPath)

    else:
        parser.print_help()
        cfg.logger.error("Please Select an Option")

def transferHandler(args, parser):
    if not args.SRC_PLAYLIST:
        cfg.logger.error("SRC_PLAYLIST required for transfer")

    if not args.DEST_PLAYLIST:
        cfg.logger.error("DEST_PLAYLIST required for transfer")

    srcPlPath = getPlPath(args.SRC_PLAYLIST)
    if not playlistExists(srcPlPath):
        return

    destPlPath = getPlPath(args.DEST_PLAYLIST)
    if not playlistExists(destPlPath):
        return

    if args.transfer:
        transferSongs(srcPlPath, destPlPath, args.transfer[0], args.transfer[0], args.transfer[1])
    
    elif args.transfer_range:
        transferSongs(srcPlPath, destPlPath, args.transfer_range[0], args.transfer_range[1], args.transfer_range[2])

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

    autoAccept = args.auto_accept
    overwrite = args.overwrite
    autoOverwrite = args.auto_overwrite

    if autoOverwrite:
        autoAccept = True
        overwrite = True

    if args.scrape:
        addTimestampsFromComments(plPath, args.scrape[0], args.scrape[0], autoAccept=autoAccept, overwrite=overwrite, autoOverwrite=autoOverwrite)
    
    elif args.scrape_range:
        addTimestampsFromComments(plPath, args.scrape_range[0], args.scrape_range[1], autoAccept=autoAccept, overwrite=overwrite, autoOverwrite=autoOverwrite)

    else:
        parser.print_help()
        cfg.logger.error("Please Select an Option")


def checkAllStateCorruption(args):

    plPaths = []
    if 'PLAYLIST' in vars(args) and args.PLAYLIST:
        try:
            plPaths.append(getPlPath(args.PLAYLIST))
        except:
            pass

    if 'SRC_PLAYLIST' in vars(args) and args.SRC_PLAYLIST:
        try:
            plPaths.append(getPlPath(args.SRC_PLAYLIST))
        except:
            pass

    if 'DEST_PLAYLIST' in vars(args) and args.DEST_PLAYLIST:
        try:
            plPaths.append(getPlPath(args.DEST_PLAYLIST))
        except:
            pass

    for plPath in plPaths:
        metaDataPath = f"{plPath}/{cfg.metaDataName}"
        if os.path.exists(metaDataPath):
            with shelve.open(metaDataPath, 'c',writeback=True) as metaData:
                correctStateCorruption(plPath,metaData)
            cfg.logger.info(f"State Recovered For Playlist: {plPath}")

def cli():
    '''
    Runs command line application, talking in args and running commands
    '''
    args = setupParsers()

    setupLogger(args)

    try:
        args.func(args)

    except InterruptTriggered as e:
        checkAllStateCorruption(args)
        
    except Exception as e:
        cfg.logger.exception(e)
        checkAllStateCorruption(args)
        
