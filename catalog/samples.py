import os

from vlibs import magic


class Sample(object):

    ERR = -1
    EXE = 0
    PDF = 1
    DLL = 2
    DOS = 3
    NEW = 4

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.filetype = intern('Unknown')
        self.type = Sample.NEW
        if path:
            self.set_type(path)

    def set_type(self, path):
        if not os.path.isfile(path):
            self.type = Sample.ERR
            return
        self.filetype = magic.from_file(path)
        if 'PDF' in self.filetype:
            self.type = Sample.PDF
        elif 'PE32' in self.filetype:
            if 'DLL' in self.filetype:
                self.type = Sample.DLL
            else:
                self.type = Sample.EXE
        elif 'MS-DOS' in self.filetype:
            self.type = Sample.DOS
        else:
            self.type = Sample.ERR

    def __str__(self):
        return "Sample [%s] %s" % (self.filetype, self.path)

    def __repr__(self):
        if self.type is self.DLL:
            return self.name + '.dll'
        return self.name