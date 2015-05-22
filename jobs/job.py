import logging
from importlib import import_module

from catalog import samples
from util import files


class Job(object):

    def __init__(self, vo2_cfg, job_cfg):
        self.log = logging.getLogger("vo2.%s" % __name__)
        self.vo2_cfg = vo2_cfg
        self.cfg = job_cfg
        self.tool = None
        self.sample_set = samples.SampleSet()
        self.iterator = iter(self)

    def setup(self):
        self.log.debug("Setting up job")
        if not self.import_tool():
            return False
        if not self.init_log_dir(self.vo2_cfg.log_root):
            self.log.error("Failed to create logging directories in: %s" % self.cfg.log)
            return False
        if not self.load_samples(self.cfg.input):
            return False
        return True

    def init_log_dir(self, path):
        return files.make_log_dir(path)

    def load_samples(self, sample_input):
        try:
            self.sample_set.add_samples(sample_input)
        except TypeError as e:
            self.log.error("Incorrect type of input: %s" % sample_input)
            return False
        else:
            return True

    def import_tool(self):
        self.log.debug("Importing: %s" % self.cfg.tool)
        try:
            self.tool = import_module(self.cfg.tool)
        except ImportError as e:
            self.log.error("Job failed to import specified tool: %s\n\t%s" % (self.cfg.tool, e))
            return False
        else:
            return True

    def get_sample(self):
        try:
            sample = self.iterator.next()
        except StopIteration:
            return None
        else:
            spath = files.resolve_path(sample)
            sname = files.filename(spath)
            sample = samples.Sample(sname, spath)
        return sample

    def get_task(self):


    def size(self):
        return self.sample_set.size

    def __iter__(self):
        return iter(self.sample_set)
