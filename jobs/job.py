import logging

from catalog import samples
from jobs import task
from util import files


class Job(object):

    def __init__(self, cfg):
        self.log = logging.getLogger("vo2.%s" % __name__)
        self.cfg = cfg
        self.tool = None
        self.sample_set = samples.SampleSet()
        self.iterator = iter(self)

    def setup(self):
        self.log.debug("Setting up job")
        root_logdir = self.cfg.get("general", "log_root")
        if not files.make_log_dir(root_logdir):
            self.log.error("Failed to create logging directories in: %s" % root_logdir)
            return False
        return self.load_samples(self.cfg.get("job", "input"))

    def load_samples(self, sample_input):
        rv = False
        try:
            rv = self.sample_set.add_samples(sample_input)
        except TypeError:
            self.log.error("No samples specified: %s" % sample_input)
            self.sample_set = xrange(len(self.cfg.get("job", "vms")))
            rv = True
        finally:
            return rv

    def get_task(self):
        sample = self.get_sample()
        return task.Task(self.cfg, sample)

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

    def size(self):
        return self.sample_set.size

    def __iter__(self):
        return iter(self.sample_set)
