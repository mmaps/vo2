import os
import sys
import logging as log
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
        if not os.path.isdir(self.cfg.log):
            #self.cfg.name = self.make_log_dir_version(self.cfg.log, self.cfg.name, suffix, ver)
            self.cfg.name = self.make_log_dir(self.cfg.log)
            if not self.cfg.name:
                log.error("Failed to create logging directories in: %s" % self.cfg.log)
                return False

        return True

    def import_tool(self):
        try:
            self.tool = import_module(self.cfg.host_tool)
        except ImportError as e:
            log.error("Job failed to import specified tool: %s\n\t%s" % (self.cfg.host_tool, e))
            return False
        else:
            return True

    def make_log_dir(self, dir_):
        made = False
        old_mask = os.umask(0007)
        log.debug("Making log directory: %s" % dir_)
        try:
            os.makedirs(log_path, 0770)
        except OSError as e:
            if e.errno is 17:
                pass
            else:
                n = ''
                log.error("Job: error making log dir: %s" % e)
        else:
            made = True
        os.umask(old_mask)
        return made

    def make_log_dir_version(self, dir_, name, sfx, ver):
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
                    log.error("Job error making log dir: %s" % e)
                    break
            else:
                made = True
        os.umask(old_mask)
        return n
