from gmusicapi import Mobileclient
from pprint import pprint

api = Mobileclient()
logged_in = api.login('th3p3r50n@gmail.com', '8r9u8ffMgoog', '30dbc03894bc223e')

songs = api.get_all_songs()
songs.sort(key=lambda k: (k['album'], int(k['trackNumber'])))
#songs.sort(key=lambda k: k['trackNumber'])
pprint(songs)
print(len(songs))