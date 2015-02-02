import os
import sys
from importlib import import_module


class Job(object):

    def __init__(self, job_scandir, job_cfg):
        self.jobs = job_scandir
        self.cfg = job_cfg
        self.tool = None

    def setup(self):
        if not self.import_tool():
            return False

        ver = 0
        suffix = "-vo2-%03d"
        self.cfg.name = self.make_log_dir(self.cfg.log, self.cfg.name, suffix, ver)
        if not self.cfg.name:
            sys.stderr.write("Failed to create logging directories in: %s\n" % self.cfg.log)
            return False

        return True

    def import_tool(self):
        try:
            self.tool = import_module(self.cfg.host_tool)
        except ImportError as e:
            sys.stderr.write("Job failed to import specified tool: %s\n\t%s\n" % (self.cfg.host_tool, e))
            return False
        else:
            return True

    def make_log_dir(self, dir_, name, sfx, ver):
        made = False
        old_mask = os.umask(0007)
        while not made:
            n = name + sfx % ver
            logdir = os.path.join(dir_, n)
            try:
                os.makedirs(logdir, 0770)
            except OSError as e:
                if e.errno is 17:
                    ver += 1
                else:
                    n = ''
                    sys.stderr.write("Job error making log dir: %s\n" % e)
                    break
            else:
                made = True
        os.umask(old_mask)
        return n
