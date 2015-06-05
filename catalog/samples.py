import logging
import os
import sys

from libs.scandir import scandir
from util import files


class SampleSet(object):

    def __init__(self):
        self.log = logging.getLogger("vo2.%s" % __name__)
        self.samples = set()
        self.size = len(self.samples)
        self.get_sample = lambda: None
        self.iterator = self

    def add_samples(self, samples):
        self.log.debug("Adding samples: %s" % samples)
        rv = self.from_disk(samples)
        if self.size <= 0:
            raise ValueError
        return rv

    def add_blanks(self, blanks_count):
        self.log.debug("Adding %s blanks" % blanks_count)
        rv = True
        try:
            self.samples = set(["" for x in xrange(blanks_count)])
        except TypeError:
            self.log.error("Invalid sample count: %s == %s" % (blanks_count, type(blanks_count)))
            rv = False
        finally:
            self.iterator = iter(self.samples)
            self.size = len(self.samples)
            return rv

    def from_disk(self, samples):
        rv = True
        if os.path.isdir(samples):
            self.add_dir(samples)
        elif os.path.isfile(samples):
            self.add_file(samples)
        else:
            self.log.error("Could not find file or directory: %s" % samples)
            rv = False
        return rv

    def add_file(self, fpath):
        self.log.debug("Samples in file, opening")
        try:
            fin = open(fpath, "r")
        except IOError as e:
            self.log.error("Error opening sample file: %s" % e)
        else:
            self.iterator = iter(fin)
            self.count()
            fin.seek(0)

    def add_dir(self, dpath):
        self.log.debug("Samples in directory, using scandir")
        self.iterator = scandir(dpath)
        self.count()
        self.iterator = scandir(dpath)

    def count(self):
        self.log.debug("Generating sample count")
        cnt = 0
        for sample in iter(self):
            self.log.debug("Counting: %s" % sample)
            cnt += 1
        self.log.info("Sample set contains %d samples" % cnt)
        self.size = cnt

    def is_empty(self):
        return self.size == 0

    def next(self):
        if self.iterator is self:
            self.log.warning("Iterating empty sample set")
            raise StopIteration

        while True:
            sample = self.iterator.next()
            try:
                sample = sample.rstrip()
            except AttributeError:
                sample = sample.path
            if sample.startswith("#"):
                continue
            break
        return sample

    def __iter__(self):
        return self

    def __len__(self):
        return len(self.samples)

class Sample(object):

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.filetype, self.ftype_str = files.get_filetype(path)
        self.logdir = os.path.join(name[0:2], name[0:4], name)

    def __str__(self):
        return "%s %s" % (self.path, self.ftype_str)

    def __repr__(self):
        if self.filetype is files.DLL:
            return self.name + '.dll'
        return self.name
