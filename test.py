from gmusicapi import Mobileclient
from collections import deque
import re

from pprint import pprint

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

class MusicQueuer(object):

    def __init__(self, table, productions):
        self.prod = productions
        self.table = table
        self.api = api

        self.stack = [0]
        self.queue = []

        self.cur_lexeme = None
        self.op = None

    def updateQueue(self, value):
        value = value.lower()
        temp_queue = []

        if self.op == "or" or self.op is None:
            song_dictlist = self.api.get_all_songs()

            for song in song_dictlist:
                if value in song['album'].lower():
                    temp_queue.append(song)
                elif value in song['artist'].lower():
                    temp_queue.append(song)
                elif value in song['title'].lower():
                    temp_queue.append(song)

            if len(temp_queue) > 0:
                temp_queue.sort(key=lambda k: (k['album'], int(k['trackNumber'])))
                self.queue.extend(temp_queue)

        elif self.op == "and":
            song_dictlist = self.queue

            for song in song_dictlist:
                if value in song['album'].lower():
                    continue
                elif value in song['artist'].lower():
                    continue
                elif value in song['title'].lower():
                    continue
                else:
                    song_dictlist.remove(song)

            self.queue = song_dictlist

    def reduce(self, production):
        reduction = production[0]
        terms = production[1][:] # Copy the list so that we don't change the original

        if reduction == "stmt" and production == self.prod[3]:
            doUpdate = True
        else:
            doUpdate = False

        while len(terms) > 0:
            if isinstance(self.stack[-1], int):
                self.stack.pop()
            elif isinstance(self.stack[-1], tuple):
                if self.stack[-1][0] == terms[-1]:
                    prod = self.stack.pop()

                    if doUpdate:
                        if prod[0] == "stmt" and prod[1] != "stmt":
                            self.updateQueue(prod[1])
                        elif prod[0] == "op":
                            if prod[1] == "&&":
                                self.op = "and"
                            elif prod[1] == "||":
                                self.op = "or"

                    terms.pop()
            #elif self.stack[-1] == terms[-1]:
            #    self.stack.pop()
            #    terms.pop()
            else:
                raise Exception("Reduce error - String doesn't match grammar productions")

        cur_state = self.stack[-1]
        next_state = self.table[cur_state][reduction]

        if next_state is not None:
            if prod[0] == "term" or prod[1] == "&&" or prod[1] == "||":
                result = (reduction, prod[1])
            else:
                result = (reduction, "stmt")

            self.stack.append(result)
            self.stack.append(next_state)
        else:
            raise Exception("No table entry for state {} and input {}".format(cur_state, reduction))

    def tokenize(self, string):
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
        token_lexeme_list = deque(self.tokenize(string))

        if token_lexeme_list is None:
            raise Exception("Couldn't parse sting into token list")

        while len(token_lexeme_list) > 0:
            cur_token_lexeme = token_lexeme_list[0]

            if isinstance(cur_token_lexeme, tuple):
                cur_token = cur_token_lexeme[0]
                cur_lexeme = cur_token_lexeme[1]
            else:
                cur_token = cur_token_lexeme

            cur_state = self.stack[-1]
            table_action = self.table[cur_state][cur_token]


            if table_action is None:
                raise Exception("Parser hit none table item {}".format(self.stack))

            elif table_action[:1] == "s":
                token_lexeme_list.popleft()
                self.stack.append((cur_token, cur_lexeme))
                self.stack.append(int(table_action[1:]))

            elif isinstance(table_action, int):
                self.stack.append(table_action)

            elif table_action[:1] == "r":
                prod = self.prod[int(table_action[1:])]
                self.reduce(prod)

            elif table_action == "acc":
                break

            else:
                raise Exception("Malformed table entry {}".format(table_action))





q = MusicQueuer(table, productions)
q.parse("panic && (pretty || build )")
pprint(q.queue)
