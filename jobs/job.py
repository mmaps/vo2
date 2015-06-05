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
        except ValueError:
            self.log.error("Empty sample input")
            rv = False
        except TypeError:
            vm_count = len(self.cfg.get("job", "vms").split(","))
            self.log.debug("No samples specified. Assigning 1 job to each VM: %s" % vm_count)
            rv = self.sample_set.add_blanks(vm_count)
        finally:
            return rv

    def get_task(self):
        self.log.debug("Get task")
        sample = self.get_sample()
        if not sample:
            return None
        return task.Task(self.cfg, sample)

    def get_sample(self):
        self.log.debug("Getting sample")
        try:
            sample = self.iterator.next()
        except StopIteration:
            return None
        else:
            spath = files.resolve_path(sample)
            sname = files.filename(spath)
            sample = samples.Sample(sname, spath)
        self.log.debug("Sample returned")
        return sample

    def size(self):
        return len(self.sample_set)

    def __iter__(self):
        return iter(self.sample_set)
