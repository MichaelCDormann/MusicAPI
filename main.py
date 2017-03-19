from gmusicapi import Mobileclient
from MusicController import *
import os.path


if __name__ == '__main__':
    path = os.path.dirname(os.path.realpath(__file__))
    settings = os.path.join(path, 'settings')
    if not os.path.exists(settings):
        print("No 'settings' file found. Check the documentation.")
        exit(0)

    with open(settings, 'r') as file:
        lines = file.readlines()
        if len(lines) != 3:
            print("Missing setting in settings file")
            exit(0)

    api = Mobileclient()
    logged_in = api.login(lines[0], lines[1], lines[2])
    music = MusicMenu(api)
    music.start()
