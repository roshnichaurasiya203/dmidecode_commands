import re
import subprocess
import json
from itertools import takewhile
from enum import Enum

__all__ = ['DmiParser']

bios = subprocess.run(['sudo', 'dmidecode', '-t', 'bios'], stdout=subprocess.PIPE).stdout.decode('utf-8')

DmiParserState = Enum (
    'DmiParserState',
    (
        'GET_SECT',
        'GET_PROP',
        'GET_PROP_ITEM',
    )
)


class DmiParserSectionHandle(object):
    def __init__(self):
        self.id= ''
        self.type = ''
        self.bytes = 0

    def __str__(self):
        return json.dumps(self.__dict__)


class DmiParserSectionProp(object):
    def __init__(self, value:str):
        self.values = []

        if value:
            self.append(value)

    def __str__(self):
        return json.dumps(self.__dict__)

    def append(self, item:str):
        self.values.append(item)


class DmiParserSection(object):
    def __init__(self):
        self.handle = None
        self.name = ''
        self.props = {}

    def __str__(self):
        return json.dumps(self.__dict__)

    def append(self, key:str, prop:str):
        self.props[key] = prop


class DmiParser(object):
    def __init__(self, text:str, **kwargs):
        self._text = text
        self._kwargs = kwargs
        self._indentLv = lambda l: len(list(takewhile(lambda c: "\t" == c, l)))
        self._sections = []

        if type(text) is not str:
            raise TypeError("%s want a %s but got %s" %(
                self.__class__, type(__name__), type(text)))

        self._parse(text)

    def __str__(self):
        return json.dumps(self._sections, **self._kwargs)

    def _parse(self, text:str):
        lines = self._text.splitlines()
        rhandle = r'^Handle\s(.+?),\sDMI\stype\s(\d+?),\s(\d+?)\sbytes$'
        section = None
        prop = None
        state = None
        k, v = None, None

        for i, l in enumerate(lines):
            if i == len(lines) - 1 or DmiParserState.GET_SECT == state:
                # Add previous section if exist
                if section:
                    # Add previous prop if exist
                    if prop:
                        section.append(k, json.loads(str(prop)))
                        prop = None

                    self._sections.append(json.loads(str(section)))
                    section = None

            if not l:
                continue

            if l.startswith('Handle'):
                state = DmiParserState.GET_SECT
                handle = DmiParserSectionHandle()
                match = re.match(rhandle, l)
                handle.id, handle.type, handle.bytes = match.groups()
                continue

            if DmiParserState.GET_SECT == state:
                section = DmiParserSection()
                section.handle = json.loads(str(handle))
                section.name = l
                state = DmiParserState.GET_PROP
                continue

            if DmiParserState.GET_PROP == state:
                k, v = [x.strip() for x in l.split(':', 1)]
                prop = DmiParserSectionProp(v)
                lv = self._indentLv(l) - self._indentLv(lines[i+1])

                if v:
                    if not lv:
                        section.append(k, json.loads(str(prop)))
                        prop = None
                    elif -1 == lv:
                        state = DmiParserState.GET_PROP_ITEM
                        continue
                else:
                    if -1 == lv:
                        state = DmiParserState.GET_PROP_ITEM
                        continue

                # Next section for this handle
                if not self._indentLv(lines[i+1]):
                    state = DmiParserState.GET_SECT

            if DmiParserState.GET_PROP_ITEM == state:
                prop.append(l.strip())

                lv = self._indentLv(l) - self._indentLv(lines[i+1])

                if lv:
                    section.append(k, json.loads(str(prop)))
                    prop = None

                    if lv > 1:
                        state = DmiParserState.GET_SECT
                    else:
                        state = DmiParserState.GET_PROP


if '__main__' == __name__:
    # just print
    parser = DmiParser(bios)
    dmidata = json.loads(str(parser))
    print("dmidata is %s" %(type(dmidata)))
    print(dmidata)
