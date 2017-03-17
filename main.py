from gmusicapi import Mobileclient
from random import randint
import vlc
from time import time, sleep
import signal
from math import ceil
import requests
import threading
import uuid
from collections import OrderedDict
import os.path
from MusicQueuer import MusicQueuer


CACHE_LIMIT = 5

api = Mobileclient()
logged_in = api.login('th3p3r50n@gmail.com', '8r9u8ffMgoog', '30dbc03894bc223e')


table = [
    {"term": "s2", "(": "s3", ")": None, "&&": None, "||": None, "$": None, "stmt'": None, "stmt": 1,    "op": None},
    {"term": None, "(": None, ")": None, "&&": "s5", "||": "s6", "$":"acc", "stmt'": None, "stmt": None, "op": 4},
    {"term": None, "(": None, ")": None, "&&": "r1", "||": "r1", "$": "r1", "stmt'": None, "stmt": None, "op": None},
    {"term": "s8", "(": "s9", ")": None, "&&": None, "||": None, "$": None, "stmt'": None, "stmt": 7,    "op": None},
    {"term": "s2", "(": "s3", ")": None, "&&": None, "||": None, "$": None, "stmt'": None, "stmt": 10,   "op": None},
    {"term": "r4", "(": "r4", ")": None, "&&": None, "||": None, "$": None, "stmt'": None, "stmt": None, "op": None},
    {"term": "r5", "(": "r5", ")": None, "&&": None, "||": None, "$": None, "stmt'": None, "stmt": None, "op": None},
    {"term": None, "(": None, ")":"s11", "&&": "s5", "||": "s6", "$": None, "stmt'": None, "stmt": None, "op": 12},
    {"term": None, "(": None, ")": "r1", "&&": "r1", "||": "r1", "$": None, "stmt'": None, "stmt": None, "op": None},
    {"term": "s8", "(": "s9", ")": None, "&&": None, "||": None, "$": None, "stmt'": None, "stmt": 13,   "op": None},
    {"term": None, "(": None, ")": None, "&&": "r3", "||": "r3", "$": "r3", "stmt'": None, "stmt": None, "op": 4},
    {"term": None, "(": None, ")": None, "&&": "r2", "||": "r2", "$": "r2", "stmt'": None, "stmt": None, "op": None},
    {"term": "s8", "(": "s9", ")": None, "&&": None, "||": None, "$": None, "stmt'": None, "stmt": 14,   "op": None},
    {"term": None, "(": None, ")":"s15", "&&": "s5", "||": "s6", "$": None, "stmt'": None, "stmt": None, "op": 12},
    {"term": None, "(": None, ")": "r3", "&&": "r3", "||": "r3", "$": None, "stmt'": None, "stmt": None, "op": 12},
    {"term": None, "(": None, ")": "r2", "&&": "r2", "||": "r2", "$": None, "stmt'": None, "stmt": None, "op": None},
]

productions = [
    ("stmt'",   ["stmt"]),
    ("stmt",    ["term"]),
    ("stmt",    ["(", "stmt", ")"]),
    ("stmt",    ["stmt", "op", "stmt"]),
    ("op",      ["&&"]),
    ("op",      ["||"]),
]


class AlarmException(Exception):
    pass


def alarmHandler(signum, frame):
    raise AlarmException


class MusicBuffer(threading.Thread):

    def __init__(self, url, loc):
        threading.Thread.__init__(self)
        self.stop = threading.Event()
        self.url = url
        self.loc = loc

    def run(self):
        stream = requests.get(self.url, stream=True)
        with open(self.loc, 'wb') as output:
            for chunk in stream.iter_content(chunk_size=256):
                if chunk:
                    output.write(chunk)
                elif self.stop.is_set():
                    break


class CacheCleanup(threading.Thread):

    def __init__(self, file_list):
        threading.Thread.__init__(self)
        self.file_list = file_list

    def run(self):
        import os
        for file in self.file_list:
            os.remove(file)


class MusicPlayer(MusicQueuer):

    def __init__(self):
        MusicQueuer.__init__(self, table, productions, api)

        self.player = None
        self.song_id = None
        self.duration = None
        self.MusicBuffer = None
        self.cache = OrderedDict([])
        self.played_songs = []
        self.song_list_size = 0

    def start(self):
        query = input("Query: ")
        self.parse(query)
        self.song_list_size = len(self.queue)

        if self.song_list_size == 0:
            print("Found nothing...")
            self.start()
            return

        while True:
            self.play()

    def play(self):
        self.load_song()

        signal.signal(signal.SIGALRM, alarmHandler)
        signal.alarm(self.duration)
        try:
            self.player.play()
            start = time()

            while True:
                text = input()
                if text == "n":
                    break
                elif text == "p":
                    self.player.pause()
                    signal.alarm(0)
                    end = ceil(time() - start)
                    while input() != "p":
                        pass
                    self.player.play()
                    start = time()
                    self.duration = self.duration - end
                    signal.alarm(self.duration)
                elif text == "r":
                    self.player.stop()
                    self.load_song(self.song_id)
                    self.player.play()
                    signal.alarm(self.duration)
                elif text == "s":
                    self.player.stop()
                    print("Stopping...")
                    remove_cache = CacheCleanup(self.cache.values())
                    remove_cache.start()
                    remove_cache.join()
                    exit()
                elif text == "rr":
                    self.player.stop()
                    self.played_songs = self.played_songs[0:-1]
                    self.load_song(song=self.played_songs[-1])
                    self.player.play()
                    signal.alarm(self.duration)

            signal.alarm(0)
        except AlarmException:
            pass
        signal.signal(signal.SIGALRM, signal.SIG_IGN)

        self.player.stop()

    def load_song(self, song_id=None, song=None):

        if song is not None:
            self.song_id = song['nid']
            #song = song['track']
            self.duration = ceil(int(song['durationMillis']) / 1000)
            print(song['title'])
            print(song['album'] + ', ' + song['artist'] + '\n')

            song_id = self.song_id


        if song_id is None:
            rand = randint(0, self.song_list_size - 1)

            #while 'track' not in self.queue[rand].keys() or 'nid' not in self.queue[rand].keys():
            #    rand = randint(0, self.song_list_size -1)

            # song = self.queue[rand]['track']
            song = self.queue[rand]
            # self.song_id = self.queue[rand]['trackId']
            self.song_id = song['nid']

            self.duration = ceil(int(song['durationMillis']) / 1000)

            print(song['title'])
            print(song['album'] + ', ' + song['artist'] + '\n')

            if self.song_id in self.cache.keys():
                self.load_song(song_id=self.song_id)
                return

            file = self.setup_stream(self.song_id)
            self.played_songs.append(song)

        elif song_id in self.cache.keys():
            file = self.cache[song_id]

        else:
            file = self.setup_stream(song_id)

        while not os.path.isfile(file):
            sleep(1)

        self.player = vlc.MediaPlayer(file)

    def setup_stream(self, song_id):

        stream_url = api.get_stream_url(song_id=self.song_id, device_id='30dbc03894bc223e', quality=u'hi')

        if self.MusicBuffer is not None:
            self.MusicBuffer.stop.set()
            self.MusicBuffer.join()

        file = str(uuid.uuid4()) + '.mp3'
        self.cache[song_id] = file

        self.MusicBuffer = MusicBuffer(stream_url, file)
        self.MusicBuffer.start()

        if len(self.cache) > CACHE_LIMIT:
            remove_index = len(self.cache) - CACHE_LIMIT
            remove_list = list(self.cache.values())[0:remove_index]
            remove_thread = CacheCleanup(remove_list)
            remove_thread.start()
            self.cache = OrderedDict(list(self.cache.items())[remove_index:])

        return file


player = MusicPlayer()
player.start()