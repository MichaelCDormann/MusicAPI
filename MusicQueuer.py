from collections import deque
import re

class MusicQueuer(object):

    def __init__(self, table, productions, api):
        self._prod = productions
        self._table = table
        self._api = api

        self._stack = [0]
        self.queue = []

        self._op = None

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
                            #self.__updateQueue(prod[1])
                            items_to_query.append(prod[1])
                        #elif prod[0] == "op":
                        #    if prod[1] == "&&":
                        #        self._op = "and"
                        #    elif prod[1] == "||":
                        #        self._op = "or"

                    terms.pop()
            #elif self._stack[-1] == terms[-1]:
            #    self._stack.pop()
            #    terms.pop()
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
