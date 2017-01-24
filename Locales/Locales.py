import fnmatch
import json
import logging
import os
import sys

logger = logging.getLogger(__name__)


class Locales:

    def __init__(self):
        self.__locale = dict()
        self.default_lang = 'en'
        self.__default_avail = False

        # Read lang files
        path_to_local = self.__get_default_dir()

        for file in os.listdir(path_to_local):
            if fnmatch.fnmatch(file, 'lang.*.json'):
                self.__read_locale(file.split('.')[1])
                if file.split('.')[1] == self.default_lang:
                    self.__default_avail = True

        if not self.__default_avail:
            lan = list(self.__locale.keys())
            if len(lan) == 1:
                self.default_lang = lan[0]
                self.__default_avail = True
            else:
                lan = lan.sort()
                self.default_lang = lan[0]
                self.__default_avail = True

    def __read_locale(self, loc):
        logger.info('Reading locale. <%s>' % loc)
        config_path = os.path.join(self.__get_default_dir(), "lang." + loc + ".json")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.__locale[loc] = json.loads(f.read())
        except Exception as e:
            logger.error('%s' % (repr(e)))
            # Pass to ignore if some files missing.
            pass

    def __get_lan(self, loc, id_in):
        if id_in == 0:
            lan = list(self.__locale.keys())
            if loc not in lan:
                loc = self.default_lang
            return self.__locale[loc]

    def get_string(self, loc, id_in):
        lang = self.__get_lan(loc, 0)
        try:
            r = lang[str(id_in)]
        except:
            lang = self.__get_lan(self.default_lang, 0)
            r = lang[str(id_in)]
        return r

    @property
    def locales(self):
        # return list(self.__locale.keys()) # THIS IS TO BE USED WHEN TRANSLATION IS COMPLETE
        return list(self.__locale.keys())

    def __get_default_dir(self):
        directory = os.path.join(
            os.path.dirname(sys.argv[0]), "Locales")
        return directory
