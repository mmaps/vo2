import ConfigParser
import logging

LOG = logging.getLogger('vo2.%s' % __name__)

class Config(object):
    def __init__(self):
        self.parsed_cfgs = []
        self.sections = {}

    def load(self, cfg_path):
        LOG.debug("Loading %s" % cfg_path)
        config = ConfigParser.SafeConfigParser(allow_no_value=True)
        self.parsed_cfgs.extend(self.parse(config, cfg_path))
        if not self.parsed_cfgs:
            LOG.warn("Bad or empty config file: %s" % cfg_path)
            return False
        return True

    def add_settings(self, cfg):
        for section, settings in cfg.sections.items():
            self.sections[section] = settings

    def parse(self, parser, cfg_path):
        rv = None
        try:
            rv = parser.read(cfg_path)
        except ConfigParser.MissingSectionHeaderError as e:
            LOG.error("Missing section headers in %s" % cfg_path)
        else:
            self.make_settings_dict(parser)
        finally:
            return rv

    def make_settings_dict(self, parser):
        for section in parser.sections():
            self.sections[section] = dict(parser.items(section))
            LOG.debug("%s: %s" % (section, self.sections[section]))

    def get(self, section, key):
        try:
            value = self.sections[section].get(key)
        except (AttributeError, KeyError):
            LOG.debug("Unknown section: %s" % section)
            return None
        else:
            return value

    def get_section(self, section):
        return self.sections.get(section)

    def get_bool(self, section, key):
        value = self.get(section, key)
        return value is not None and (value == "1" or value.lower() == "yes"
                                      or value.lower() == "true" or value.lower() == "on")

    def get_float(self, section, key):
        value = self.get(section, key)
        try:
            value = float(value)
        except ValueError:
            LOG.error("Could not coerce [%s]%s to float" % (section, key))
            return None
        else:
            return value

    def set(self, section, key, value):
        LOG.debug("Setting [%s][%s]: %s" % (section, key, value))
        self.sections[section][key] = value

    def find_all(self, match):
        LOG.debug("Searching config for: %s" % match)
        sections = {}
        for section, settings in self.sections.items():
            LOG.debug("\tChecking: %s" % section)
            if section.startswith(match):
                k = section.replace(match, '')
                sections[k] = settings
        LOG.debug("Found: %s" % sections.keys())
        return sections

    def __str__(self):
        rv = []
        for s in self.sections:
            rv.append("%s" % s)
            rv.append("%s" % self.sections[s])
        return '\n'.join(rv)
