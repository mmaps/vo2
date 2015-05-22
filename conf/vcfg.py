import logging
from ConfigParser import SafeConfigParser, MissingSectionHeaderError


class Namespace(object):

    def __str__(self):
        attrs = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, Namespace):
                attrs.append("[%s]\n%s" % (attr_name, attr))
            elif not attr_name.startswith("__"):
                attrs.append("\t%s" % attr_name)
        return "\n".join(attrs)

    def __getattr__(self, item):
        return None


class Config(object):

    def __init__(self):
        self.sections = {}
        self.log = logging.getLogger('vo2.%s' % __name__)

    def load(self, cfg_path):
        self.log.debug("Loading %s" % cfg_path)
        parser = SafeConfigParser(allow_no_value=True)
        parsed = self.parse(parser, cfg_path)
        if not parsed:
            self.log.warn("Bad or empty config file: %s" % cfg_path)
        else:
            self.make_namespaces(parser)
        return parsed

    def parse(self, parser, cfg_path):
        try:
            parsed = parser.read(cfg_path)
        except MissingSectionHeaderError as e:
            self.log.error("Missing section headers in %s" % cfg_path)
            return None
        else:
            return parsed

    def make_namespaces(self, parser):
        for section in parser.sections():
            sect_ns = Namespace()
            self.sections[section] = sect_ns
            for name, value in parser.items(section):
                value = value.rstrip(r'\/')
                self.log.debug("Cfg Namespace [%s][%s]: '%s'" % (section, name, value))
                setattr(sect_ns, name, value)

    def set(self, section, key, value):
        self.log.debug("Setting [%s][%s]: %s" % (section, key, value))
        setattr(self.sections[section], key, value)

    def get_namespace(self, name):
        return self.sections.get(name)

    def find_all(self, match):
        self.log.debug("Searching config for: %s" % match)
        sections = {}
        for section, settings in self.sections.items():
            self.log.debug("\tChecking: %s" % section)
            if section.startswith(match):
                k = section.replace(match, '')
                sections[k] = settings
        self.log.debug("Found: %s" % sections.keys())
        return sections

    def __str__(self):
        rv = []
        for s in self.sections:
            rv.append("%s" % s)
            rv.append("%s" % self.sections[s])
        return '\n'.join(rv)
