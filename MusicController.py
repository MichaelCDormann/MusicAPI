from gmusicapi import Mobileclient
from random import randint
from time import time, sleep
from math import ceil
from collections import OrderedDict
from MusicQueuer import MusicQueuer
import vlc
import requests
import threading
import uuid
import os.path


class CacheCleanup(threading.Thread):

    def __init__(self, file_list):
        threading.Thread.__init__(self)
        self.file_list = file_list

    def run(self):
        import os
        for file in self.file_list:
            os.remove(file)


class MusicBuffer(threading.Thread):

    def __init__(self, url, loc):
        threading.Thread.__init__(self)
        self.stop = threading.Event()
        self.url = url
        self.loc = loc

    def run(self):
        path, file = os.path.split(self.loc)
        if not os.path.exists(path):
            os.makedirs(path)

        stream = requests.get(self.url, stream=True)
        with open(self.loc, 'wb') as output:
            for chunk in stream.iter_content(chunk_size=256):
                if chunk:
                    output.write(chunk)
                elif self.stop.is_set():
                    break


class MusicPlayer(threading.Thread):

    def __init__(self, music_queuer_instance, cache_limit):
        threading.Thread.__init__(self)

        self._MusicQueuer = music_queuer_instance
        self._MusicBuffer = None

        self.cache_limit = cache_limit

        if self._MusicQueuer.shuffle:
            self._song_index = randint(0, self._MusicQueuer.queue_size - 1)
        else:
            self._song_index = 0
        self._duration = 0

        self._vlc_player = None
        self._played_songs = []
        self._cache = OrderedDict([])

        self._start_time = 0

        self.stop = threading.Event()
        self.signal = threading.Event()
        self.play_pause = threading.Event()
        self.next = threading.Event()
        self.repeat = threading.Event()
        self.previous = threading.Event()

    def run(self):
        self.__load()
        while not self.stop.is_set():
            self._vlc_player.play()
            start_time = time()

            self.signal.wait(self._duration)

            if self.signal.is_set():
                if self.play_pause.is_set():
                    self.__play_pause(start_time)
                    self.play_pause.clear()
                if self.next.is_set():
                    self.__next()
                    self.next.clear()
                if self.repeat.is_set():
                    self.__repeat()
                    self.repeat.clear()
                if self.previous.is_set():
                    self.__previous()
                    self.previous.clear()
                self.signal.clear()
            elif not self.stop.is_set():
                self.__next()

        self._vlc_player.stop()

        self._MusicBuffer.stop.set()
        self._MusicBuffer.join()

        cleanup = CacheCleanup(self._cache.values())
        cleanup.start()
        cleanup.join()

    def __load(self):
        song = self._MusicQueuer.queue[self._song_index]
        song_id = song['nid']

        if song_id[0] != 'T':
            song_id = 'T' + song_id

        self._duration = ceil(int(song['durationMillis']) / 1000)

        print(song['title'])
        print('{}, {}\n'.format(song['album'], song['artist']))

        if song_id in self._cache.keys():
            file = self._cache[song_id]
        else:
            stream_url = self._MusicQueuer.api.get_stream_url(song_id=song_id, quality=u'hi')

            if self._MusicBuffer is not None:
                self._MusicBuffer.stop.set()
                self._MusicBuffer.join()

            name = str(uuid.uuid4()) + '.mp3'
            file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'cache', name)
            self._cache[song_id] = file

            self._MusicBuffer = MusicBuffer(stream_url, file)
            self._MusicBuffer.start()

            if len(self._cache) > self.cache_limit:
                remove_index = len(self._cache) - self.cache_limit
                remove_list = list(self._cache.values())[0:remove_index]
                remove_thread = CacheCleanup(remove_list)
                remove_thread.start()
                self._cache = OrderedDict(list(self._cache.items())[remove_index:])

            while not os.path.isfile(file):
                sleep(1)

            self._played_songs.append(self._song_index)

        self._vlc_player = vlc.MediaPlayer(file)

    def __play_pause(self, start_time):
        self._vlc_player.pause()
        end_time = time()
        elapsed_time = end_time - start_time

        self.signal.clear()
        self.signal.wait()

        self._duration = elapsed_time

    def __next(self):
        self._vlc_player.stop()
        if self._MusicQueuer.shuffle:
            self._song_index = randint(0, self._MusicQueuer.queue_size - 1)
        else:
            self._song_index += 1
        self.__load()

    def __repeat(self):
        self._vlc_player.stop()
        self.__load()

    def __previous(self):
        self._vlc_player.stop()
        self._played_songs = self._played_songs[0:-1]
        self._song_index = self._played_songs[-1]
        self.__load()


class MusicMenu(MusicQueuer):

    def __init__(self, api, cache_limit=10):
        MusicQueuer.__init__(self, api)

        self.api = api

        self._cache_limit = cache_limit

        self.shuffle = False
        self._MusicPlayer = None

    def start(self):
        uinput = ''
        print("Started! Type 'help' for help.")
        while uinput != 'q':
            uinput = input("\n").strip()

            if uinput == "help":
                self.list_help()
            elif uinput[0:5] == "play:":
                self.parse(uinput[5:])
                self.play_queue()
            elif uinput[0:8] == "shuffle:":
                self.shuffle = True
                self.parse(uinput[8:])
                self.play_queue()
            elif uinput[0:10] == "playlists:":
                playlist_list = uinput[10:].split(",")
                playlist_list = [x.strip() for x in playlist_list]
                self.addPlaylist(playlist_list)
                self.play_queue()
            elif uinput[0:18] == "shuffle playlists:":
                playlist_list = uinput[18:].split(",")
                playlist_list = [x.strip() for x in playlist_list]
                self.shuffle = True
                self.addPlaylist(playlist_list)
                self.play_queue()
            elif uinput == "list playlists":
                self.list_playlists()

            elif uinput == "p":
                self._MusicPlayer.play_pause.set()
                self._MusicPlayer.signal.set()
            elif uinput == "n":
                self._MusicPlayer.next.set()
                self._MusicPlayer.signal.set()
            elif uinput == "r":
                self._MusicPlayer.repeat.set()
                self._MusicPlayer.signal.set()
            elif uinput == "rr":
                self._MusicPlayer.previous.set()
                self._MusicPlayer.signal.set()
            elif uinput == "s":
                self._MusicPlayer.stop.set()
                self._MusicPlayer.signal.set()
                self._MusicPlayer = None
                print("Stopped")
            elif uinput != "q":
                print("Unidentified input: {}".format(uinput))

        if self._MusicPlayer is not None:
            self._MusicPlayer.stop.set()
            self._MusicPlayer.signal.set()
            self._MusicPlayer.join()
        print("Exiting...")
        exit(0)

    def list_help(self):
        print("help \t\t\t\t\t  - Prints this page\n"
              "play: {query} \t\t\t  - Create a queue matching {query} and play it.\n"
              "shuffle: {query}\t\t  - Same as 'play:' but shuffles the queue\n"
              "playlists: {list}\t\t  - Play a list of playlists, queued in whatever order gmusic returned\n"
              "shuffle playlists: {list} - Same as 'playlists:' but with an added shuffle element\n"
              "list playlists\t\t\t  - List the current user's available playlists\n"
              "\n"
              "{query} is an and/or expression. Eg 'song_name && artist_name' or '(album1 || album2) && artist'\n"
              "\tValid expression characters are: &&(and), ||(or), !(not), and parenthesis\n"
              "{list} is comma separated list\n"
              "\n"
              "While playing:\n"
              "\tp \t\t - Pause\n"
              "\tn \t\t - Next\n"
              "\tr \t\t - Replay current song\n"
              "\trr\t\t - Return to previous song\n"
              "\ts \t\t - Stop playing and return to main menu\n"
              "\n"
              "q - Exit the program any time.")

    def list_playlists(self):
        playlists = self._api.get_all_playlists()
        for playlist in playlists:
            print(playlist['name'])

    def play_queue(self):
        if self._MusicPlayer is None:
            self._MusicPlayer = MusicPlayer(self, self._cache_limit)
            self._MusicPlayer.start()
        else:
            self._MusicPlayer.stop.set()
            self._MusicPlayer.join()

            self.play_queue()
