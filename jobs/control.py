import sys
from importlib import import_module
from multiprocessing import Process

import task
from util import logs, files


class TaskController(Process):

    def __init__(self, cfg, vm, sample_queue):
        """
        :param cfg:
        :type cfg: conf.vcfg.Config
        :param vm:
        :type vm: guests.vbox.VirtualMachine
        :param sample_queue:
        :type sample_queue: Queue.Queue
        :return:
        :rtype:
        """
        super(TaskController, self).__init__()
        self.log = logs.init_logging("%s" % self, cfg.debug)
        self.cfg = cfg
        self.vm = vm
        self.sample_queue = sample_queue
        self.stop = False

    def run(self):
        self.log.info("%s task controller running" % self)
        tool = self.import_tool(self.cfg.tool)
        while not self.stop:
            sample = self.process_sample(self.sample_queue.get(block=True))
            curr_task = task.Task(self.cfg, sample)
            if not self.setup_task(curr_task):
                continue
            self.run_task(tool, curr_task)

    def import_tool(self, name):
        self.log.debug("%s importing tool: %s" % (self, name))
        try:
            tool = import_module(name)
        except ImportError as e:
            self.log.error("Unable to import specified tool %s: %s" % (name, e))
            self.cleanup()
        else:
            return tool

    def process_sample(self, sample):
        self.log.info("%s processing: %s" % (self, sample))
        if not sample:
            self.cleanup()
        return sample

    def setup_task(self, task):
        if not files.make_log_dir(task.logdir):
            self.log.error("Could not create log directory")
            return False
        task.logfile = open()

    def setup_guest(self):
        pass

    def reset_guest(self):
        pass

    def run_task(self, task):
        pass

    def cleanup(self):
        self.log.info("%s cleaning up" % self)
        sys.exit(0)

    def __str__(self):
        return "%s-CTRL" % self.vm.name


