# Python Modules
import signal
import logging
import multiprocessing as mp
import Queue

import control


MAXQUEUE = 1000


def sigint_handler(signum, frame):
    print "Interrupted..."


class Scheduler(object):

    def __init__(self, job, vm_fact):
        self.log = logging.getLogger("vo2.%s" % __name__)
        self.job = job
        self.vm_factory = vm_fact
        self.task_controllers = []
        self.task_queue = mp.Queue(MAXQUEUE)

    def init_controllers(self):
        vms = self.vm_factory.list()
        self.log.debug("Init controllers for: %s" % vms)
        for vm in vms:
            if vm in self.job.cfg.vms:
                vm = self.vm_factory.get(vm)
                if vm:
                    ctrl = control.TaskController(self.job.cfg, vm, self.task_queue)
                    self.task_controllers.append(ctrl)
                else:
                    self.log.error("Unable to instanciate VM: '%s'" % vm)

    def start(self):
        self.log.info("Initializing..")
        self.init_controllers()
        self.log.info("Starting controllers...")
        self.run_controllers()
        self.log.info("Starting scheduler...")
        self.schedule_samples()
        self.log.info("Cleaning up scheduler...")
        self.cleanup()

    def run_controllers(self):
        for controller in self.task_controllers:
            controller.start()

    def schedule_samples(self):
        while True:
            sample = self.job.get_sample()
            if not sample:
                self.add_poison()
                break
            else:
                self.add_sample(sample)

    def add_poison(self):
        for controller in range(len(self.task_controllers)):
            self.add_sample(None)

    def add_sample(self, sample):
        try:
            self.task_queue.put(sample, block=True, timeout=self.job.vo2_cfg.task_wait)
        except Queue.Full:
            self.log.error("Timed out waiting for free task slot. VM's may be frozen")
            self.kill_controllers()

    def cleanup(self):
        self.log.debug("Beginning scheduler cleanup...")
        self.join_children(self.task_controllers)
        self.close_queue(self.task_queue)

    def join_children(self, children):
        self.log.debug("Joining child processes...")
        for child in children:
            child.join()

    def close_queue(self, qu):
        self.log.debug("Closing queue...")
        if not qu.empty():
            qu.cancel_join_thread()

    def kill_controllers(self, controllers):
        self.log.debug("Terminating controller processes forcefully...")
        for controller in controllers:
            controller.terminate()

