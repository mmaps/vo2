from ConfigParser import SafeConfigParser


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


class Config(object):

    def __init__(self, path):
        self.path = path
        self.sections = {}
    
    def parse(self): 
        parser = SafeConfigParser(allow_no_value=True)
        parsed = parser.read(self.path)
        self.parse_sections(parser)
        return parsed

    def parse_sections(self, parser):
        for section in parser.sections():
            sect_ns = Namespace()
            self.sections[section] = sect_ns
            for name, value in parser.items(section):
                value = value.rstrip(r'\/')
                setattr(sect_ns, name, value)

    def get_namespace(self, name):
        return self.sections.get(name)

    def __str__(self):
        rv = []
        for s in self.sections:
            rv.append("%s" % s)
            rv.append("%s" % self.sections[s])
        return '\n'.join(rv)
