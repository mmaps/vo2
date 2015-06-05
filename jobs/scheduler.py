import logging
import multiprocessing as mp
import traceback
import Queue
from cPickle import PicklingError
import time
import control


MAXQUEUE = 1000


class Scheduler(object):

    def __init__(self, job, vm_fact):
        self.log = logging.getLogger("vo2.%s" % __name__)
        self.job = job
        self.vm_factory = vm_fact
        self.task_controllers = []
        self.task_queue = mp.Queue(MAXQUEUE)

    def init_controllers(self):
        vms = self.vm_factory.list_vms()
        self.log.debug("Init controllers for: %s" % vms)
        for vm in vms:
            self.make_controller(vm)

    def make_controller(self, vm):
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
        try:
            self.run()
        except AssertionError:
            self.log.error("Error running scheduler: %s" % traceback.format_exc())
            self.kill_controllers(self.task_controllers)
        finally:
            self.log.info("Cleaning up scheduler...")
            self.cleanup()

    def run_controllers(self):
        for controller in self.task_controllers:
            controller.start()

    def run(self):
        assert(len(self.task_controllers) > 0)
        while True:
            task = self.job.get_task()
            if not task:
                self.log.debug("Tasks empty")
                self.add_poison()
                break
            else:
                self.log.debug("Got task: %s" % task)
                self.add_task(task)

    def add_poison(self):
        for controller in range(len(self.task_controllers)):
            self.add_task(None)

    def add_task(self, task):
        self.log.debug("Adding task: %s" % task)
        try:
            self.task_queue.put(task, block=True, timeout=self.job.cfg.get_float("timeouts", "task_wait"))
        except PicklingError:
            self.log.error("Task object cannot be added to work queue. Cannot be pickled")
            self.kill_controllers(self.task_controllers)
        except Queue.Full:
            self.log.error("Timed out waiting for free task slot. VM's may be frozen")
            self.kill_controllers(self.task_controllers)

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

