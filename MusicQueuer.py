from collections import deque
import re


TABLE = [
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

PRODUCTIONS = [
    ("stmt'",   ["stmt"]),
    ("stmt",    ["term"]),
    ("stmt",    ["(", "stmt", ")"]),
    ("stmt",    ["stmt", "op", "stmt"]),
    ("op",      ["&&"]),
    ("op",      ["||"]),
]


class MusicQueuer(object):

    def __init__(self, api):
        self._prod = PRODUCTIONS
        self._table = TABLE
        self._api = api

        self._stack = [0]
        self.queue = []
        self.queue_size = 0

        self._op = None

    def addPlaylist(self, playlist_list):
        requested_shared_playlist_tokens = []

        user_playlists = self._api.get_all_playlists()
        for playlist in user_playlists:
            if playlist['name'].lower() in playlist_list and playlist['type'] == 'SHARED':
                requested_shared_playlist_tokens.append(playlist['shareToken'])

        playlist_contents = self._api.get_all_user_playlist_contents()
        for playlist in playlist_contents:
            if playlist['name'].lower() in playlist_list:
                for track in playlist['tracks']:
                    if 'track' in list(track.keys()):
                        self.queue.append(track['track'])

        for token in requested_shared_playlist_tokens:
            playlist_songs = self._api.get_shared_playlist_contents(token)
            for song in playlist_songs:
                self.queue.append(song['track'])

    def __updateQueue(self, value):
        value = value.lower()
        temp_queue = []

        if value[0] == "!":
            notOp = True
            value = value[1:]
        else:
            notOp = False

        if self._op == "or" or self._op is None:
            song_dictlist = self._api.get_all_songs()

            for song in song_dictlist:
                action = False
                if value in song['album'].lower():
                    action = True
                elif value in song['artist'].lower():
                    action = True
                elif value in song['title'].lower():
                    action = True

                if action ^ notOp:
                    temp_queue.append(song)

            if len(temp_queue) > 0:
                temp_queue.sort(key=lambda k: (k['album'], int(k['trackNumber'])))
                self.queue.extend(temp_queue)

        elif self._op == "and":
            for song in self.queue[:]:
                action = True
                if value in song['album'].lower():
                    action = False
                elif value in song['artist'].lower():
                    action = False
                elif value in song['title'].lower():
                    action = False

                if action ^ notOp:
                    self.queue.remove(song)

        self.queue_size = len(self.queue)


    def __reduce(self, production):
        reduction = production[0]
        terms = production[1][:] # Copy the list so that we don't change the original
        items_to_query = []

        if reduction == "stmt" and production == self._prod[3]:
            doUpdate = True
        else:
            doUpdate = False

        while len(terms) > 0:
            if isinstance(self._stack[-1], int):
                self._stack.pop()
            elif isinstance(self._stack[-1], tuple):
                if self._stack[-1][0] == terms[-1]:
                    prod = self._stack.pop()

                    if doUpdate:
                        if (prod[0] == "stmt" or prod[0] == "op") and prod[1] != "stmt":
                            items_to_query.append(prod[1])
                    terms.pop()
            else:
                raise Exception("Reduce error - String doesn't match grammar productions")

        if len(items_to_query) > 0:
            items_to_query.reverse()
            for item in items_to_query:
                if item != "&&" and item != "||":
                    self.__updateQueue(item)
                else:
                    if item == "&&":
                        self._op = "and"
                    elif item == "||":
                        self._op = "or"

            items_to_query.clear()

        cur_state = self._stack[-1]
        next_state = self._table[cur_state][reduction]

        if next_state is not None:
            if prod[0] == "term" or prod[1] == "&&" or prod[1] == "||":
                result = (reduction, prod[1])
            else:
                result = (reduction, "stmt")

            self._stack.append(result)
            self._stack.append(next_state)
        else:
            raise Exception("No table entry for state {} and input {}".format(cur_state, reduction))

    def __tokenize(self, string):
        lexeme_list = re.split("(&&)|(\|\|)|(\))|(\()", string)
        lexeme_list = [i.strip() for i in lexeme_list if i is not None]

        token_lexeme_list = [
            ("term", i) if
                i != "&&" and
                i != "||" and
                i != "(" and
                i != ")"
            else (i, i) for i in lexeme_list if i != ''
        ]

        token_lexeme_list.extend("$")

        return token_lexeme_list

    def parse(self, string):
        self._stack = [0]
        self.queue = []
        self.queue_size = 0

        self._op = None

        string = string.lower()
        token_lexeme_list = deque(self.__tokenize(string))

        if token_lexeme_list is None:
            raise Exception("Couldn't parse sting into token list")
        elif len(token_lexeme_list) == 1:
            print("Nothing entered")
            return
        elif len(token_lexeme_list) == 2:
            if isinstance(token_lexeme_list[0], tuple):
                self.__updateQueue(token_lexeme_list[0][1])
            return

        while len(token_lexeme_list) > 0:
            cur_token_lexeme = token_lexeme_list[0]

            if isinstance(cur_token_lexeme, tuple):
                cur_token = cur_token_lexeme[0]
                cur_lexeme = cur_token_lexeme[1]
            else:
                cur_token = cur_token_lexeme

            cur_state = self._stack[-1]
            table_action = self._table[cur_state][cur_token]


            if table_action is None:
                raise Exception("Parser hit none table item {}".format(self._stack))

            elif table_action[:1] == "s":
                token_lexeme_list.popleft()
                self._stack.append((cur_token, cur_lexeme))
                self._stack.append(int(table_action[1:]))

            elif isinstance(table_action, int):
                self._stack.append(table_action)

            elif table_action[:1] == "r":
                prod = self._prod[int(table_action[1:])]
                self.__reduce(prod)

            elif table_action == "acc":
                break

            else:
                raise Exception("Malformed table entry {}".format(table_action))
