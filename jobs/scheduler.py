import logging
import multiprocessing as mp
import os
import signal
import sys
import traceback
import Queue

import control


MAXQUEUE = 1000


class Scheduler(object):

    def __init__(self, job, vm_fact):
        self.log = logging.getLogger("vo2.%s" % __name__)
        self.job = job
        self.vm_factory = vm_fact
        self.task_cnt = 0
        self.task_max = 0
        self.task_controllers = []
        self.task_queue = mp.Queue(MAXQUEUE)

    def init_sig_handler(self, sig):
        self.log.info("Installing SIGINT handler")

        def sigint_handler(signal_, frame):
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            sys.stdout.write("Signal caught in PID: %s...\nWaiting tasks enqueued: %d / %d\n" % (os.getpid(), self.task_cnt, self.task_max))
            proceed = ""
            while proceed != "y" and proceed != "n":
                proceed = raw_input("Continue? y/n\n").lower()
            if proceed == "y":
                self.kill_controllers(signal.SIGINT, self.task_controllers)
            elif proceed == "n":
                self.kill_controllers(signal.SIGTERM, self.task_controllers)
            signal.signal(signal.SIGINT, sigint_handler)

        if sig == signal.SIGINT:
            sig_handler = sigint_handler
        else:
            sig_handler = None

        return sig_handler

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
        signal.signal(signal.SIGINT, self.init_sig_handler(signal.SIGINT))
        try:
            self.run()
        except AssertionError:
            self.log.error("Error running scheduler: %s" % traceback.format_exc())
            self.kill_controllers(signal.SIGTERM, self.task_controllers)
        finally:
            self.log.info("Cleaning up scheduler...")
            self.cleanup()

    def run_controllers(self):
        for controller in self.task_controllers:
            controller.start()

    def run(self):
        assert(len(self.task_controllers) > 0)
        self.task_cnt = 0
        self.task_max = self.job.size()
        self.log.debug("tasks %d / %d" % (self.task_cnt, self.task_max))
        while self.task_cnt < self.task_max:
            task = self.job.get_task()
            if not task:
                self.log.debug("got empty task: %s" % task)
                break
            else:
                self.task_cnt += 1
                self.log.debug("got task: %s" % task)
                self.add_task(task)
        self.add_poison()

    def add_poison(self):
        for controller in range(len(self.task_controllers)):
            self.add_task(None)

    def add_task(self, task):
        self.log.debug("Adding task: %s" % task)
        try:
            self.task_queue.put(task, block=True, timeout=self.job.cfg.get_float("timeouts", "task_wait"))
        except Queue.Full:
            self.log.error("Timed out waiting for free task slot. VM's may be frozen")
            self.kill_controllers(signal.SIGTERM, self.task_controllers)

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

    def kill_controllers(self, sig, controllers):
        self.log.debug("Signaling kill to controllers")
        for controller in controllers:
            if sig is signal.SIGINT:
                self.log.debug("Sending SIGINT to %s" % controller)
                os.kill(controller.pid, signal.SIGINT)
            else:
                self.log.debug("Sending SIGTERM to %s" % controller)
                controller.terminate()
