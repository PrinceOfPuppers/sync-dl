from re import compile

metaDataName = ".metaData"

filePrependRE = compile(r'\d+_')

manualAddId = '-manualAddition' # id given to mannually added songs (cannont conflict with url ids and cannot be empty string)

testPlPath = 'sync_dl/tests/testPlaylists'