import sys
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow


from sync_dl.yt_api.encrypted import getDecryptedProxy
from sync_dl import config as cfg
import json

# Any attempt to modify this script will result in sync-dl no longer being able to decrypt the client api key.
# This is by design, to prevent the api key from being stolen.

def newCredentials(scopes,credPath):
    trace = sys.gettrace()

    if trace is not None:
        #debugger is on, not getting flow
        return None

    clientSecretsEncrypted = f'{cfg.modulePath}/yt_api/encrypted/encrypted_client_secrets'

    decrypted = getDecryptedProxy(clientSecretsEncrypted).decode('utf8')

    clientConfig = json.loads(decrypted)

    flow = InstalledAppFlow.from_client_config(clientConfig,scopes=scopes)

    prompt = '\nMake sure you are using sync-dl which you Installed via pip.\nIf not, then this api key may be stolen! \n\nAuthentificate at:\n{url}'
    # start local server on localhost, port 8080
    flow.run_local_server(prompt = 'consent', authorization_prompt_message=prompt,open_browser=False)


    credentials = flow.credentials

    if os.path.exists(credPath):
        os.remove(credPath)
    with open(credPath,"wb") as f:
        pickle.dump(credentials,f)

    return credentials
