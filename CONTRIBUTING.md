# ISSUES
State your issue, what platform you are on, and, if applicable, the output of running the relevent command with the verbose flag:
```
sync-dl -v [REST_OF_COMMAND]
```
If your issue involves metadata corruption, the output of the -d and -p flags would be helpful
```
sync-dl -d [NAME_OF_PLAYLIST]
```
```
sync-dl -p [NAME_OF_PLAYLIST]
```
# Devlopment
The Hiarchy of the project is as follows (with scripts only depending on scripts beneath them in the list)


### `cli.py`       
-> The command line interface

### `commands.py`     
-> The commands run by cli, commands from here can also imported and envoked by other projects (such as the android app).

### `plManagement.py` 
-> Large functions used by the commands

### `helpers.py`
-> small functions and wrappers

### `ytdlWrappers.py`
-> everything which directly interfaces with youtube-dl

### `config.py`
-> configuration and global variables

### `config.ini`
-> holds user editable configuration, if this does exist a default one will be created by `config.py`

## Entry points
The entry point for the code is in `__init__.py` which calls the main function of `cli.py`. on windows `__init__.py` is the console script that is added to path, whereas and on linux bin/sync-dl is used, which simply calls the main() function of `__init__.py`.

`__init__.py` also holds a singleton called noInturrupt, which is used as a handler for SIGINT, it can also be used to simulate a SIGINT through code (used for canceling in the android app).

## encrypted/
This holds the encrypted oauth api key along with the obfuscated code needed to decrypt it, this is only used for the --push-order command. any modifications made to newCredentials.py will cause the decryption to fail (by design)

# PULL REQUESTS
Before all else be sure all changes pass the unit and integration tests
```
python3 test.py [PLAYLIST_URL]
```

Travis CI will also run these on your pull request, however its best if you also run them on your own machine. 

Say what the pull request is for: 
 - bug fix
 - new feature
 - improvement

And link to any relevent issues that the pull request is addressing.
