import multiprocessing
import os
import signal
import sys
import threading
from Queue import Empty
from importlib import import_module

from util import logs, files


class TaskController(multiprocessing.Process):

    def __init__(self, cfg, vm, work_queue):
        """
        :type cfg: conf.vcfg.Config
        :type vm: guests.vbox.VirtualMachine
        :type sample_queue: Queue.Queue
        """
        super(TaskController, self).__init__()
        self.cfg = cfg
        self.vm = vm
        self.tool = None
        self.work_queue = work_queue
        self.stop = False
        self.log = logs.init_logging("%s" % self, self.cfg.get("general", "debug"))

    def init_sig_handler(self, sig, lock):
        self.log.info("Installing SIGINT handler in TaskController")

        def sigint_handler(signal_, frame):
            if not lock.acquire(False):
                """
                Already interrupted
                """
                self.log.debug("Resuming")
                lock.release()
            else:
                """
                Not interrupted
                """
                self.log.debug("Paused by SIGTERM")
                signal.pause()

        def sigterm_handler(signal_, frame):
            self.log.debug("Exiting...")
            sys.exit(1)

        if sig == signal.SIGINT:
            sig_handler = sigint_handler
        elif sig == signal.SIGTERM:
            sig_handler = sigterm_handler
        else:
            sig_handler = None

        return sig_handler

    def run(self):
        self.log.info("%s - %s task controller running" % (self, self.pid))
        signal.signal(signal.SIGINT, self.init_sig_handler(signal.SIGINT, multiprocessing.Lock()))
        signal.signal(signal.SIGTERM, self.init_sig_handler(signal.SIGTERM, multiprocessing.Lock()))
        self.import_tool(self.cfg.get("job", "tool"))
        while not self.stop:
            try:
                tsk = self.process_input(
                    self.work_queue.get(block=True, timeout=self.cfg.get_float("timeouts", "task_wait")))
            except Empty:
                self.log.error("%s timed out waiting for work input" % self)
                self.stop = True
            else:
                self.handle_task(tsk)

    def import_tool(self, name):
        self.log.debug("%s importing tool: %s" % (self, name))
        try:
            self.tool = import_module(name)
        except ImportError as e:
            self.log.error("Unable to import specified tool %s: %s" % (name, e))
            self.cleanup()

    def process_input(self, tsk):
        self.log.debug("%s processing: %s" % (self, tsk))
        if not tsk:
            self.cleanup()
        return tsk

    def handle_task(self, tsk):
        self.log.debug("Handling: %s" % tsk)
        logdir, logfile = self.get_task_log(tsk)
        if self.setup_task(tsk, logdir, logfile) and self.setup_vm(tsk):
            self.run_task(tsk)
        self.cleanup_task(tsk)
        self.cleanup_vm()

    def setup_task(self, tsk, logdir, logfile):
        tsk.set_vm(self.vm)
        tsk.set_log(logdir, logfile)
        return tsk.vm and tsk.logdir and tsk.logfile

    def setup_vm(self, tsk):
        try:
            self.vm.set_log(tsk.log)
        except AttributeError as e:
            sys.stderr.write("Error setting up VM: %s\n" % e)
            return False
        else:
            return True

    def get_task_log(self, tsk):
        if tsk.sample:
            logdir = self.init_logdir(tsk.sample.logdir)
        else:
            logdir = self.init_logdir(self.cfg.get("job", "name"))
        if not logdir:
            return False
        logfile = self.open_task_log(logdir, tsk.sample.name, self.vm.name)
        if not logfile:
            return False
        return logdir, logfile

    def init_logdir(self, sub_path):
        self.log.debug("Init logdir: %s" % sub_path)
        root_path = self.cfg.get("general", "log_root")
        path = os.path.join(root_path, sub_path)
        if files.make_log_dir(path):
            return path
        else:
            return None

    def open_task_log(self, path, sample, vm):
        if sample:
            logpath = os.path.join(path, "%s.%s.txt" % (sample, vm))
        else:
            logpath = os.path.join(path, "%s.%s.txt" % (self.cfg.get("job", "name"), vm))
        try:
            logfile = open(logpath, "w")
        except IOError as e:
            self.log("TASK: Error creating task log: %s" % e)
            logfile = None
        return logfile

    def run_task(self, tsk):
        self.log.debug("Running task %s" % tsk)
        timeout = self.cfg.get_float("timeouts", "task_wait")
        watchdog = threading.Thread(target=self._run_task, args=(tsk,))
        watchdog.start()
        watchdog.join(timeout=timeout)
        if watchdog.is_alive():
            self.log.error("%s timed out waiting on tool to run for %s" % (self, timeout))

    def _run_task(self, tsk):
        self.tool.run(tsk)

    def cleanup_task(self, tsk):
        self.log.debug("Cleaning up task: %s" % tsk)
        tsk.logfile.flush()
        tsk.logfile.close()

    def cleanup_vm(self):
        self.vm.set_log(None)

    def cleanup(self):
        self.log.info("%s cleaning up" % self)
        sys.exit(0)

    def __str__(self):
        return "%s-CTRL" % self.vm.name
