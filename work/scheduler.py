# Python Modules
import signal
import threading
import logging as log
from multiprocessing import Pool
from Queue import Queue, Empty

from task import Task


POOL = None


def sigint_handler(signum, frame):
    print 'Shutting down'
    POOL.terminate()
    POOL.close()


class Scheduler(object):

    def __init__(self, job, vm_mgr):
        global POOL
        POOL = Pool(len(job.cfg.vms.split(',')), maxtasksperchild=1)
        self.job = job
        self.vms = job.cfg.vms.split(',')
        self.vm_mgr = vm_mgr
        self.vm_queue = Queue()
        self.vm_mgr_thread = threading.Thread(target=self.vm_mgr.find_vm, args=(self.vms, self.vm_queue))
        self.vm_mgr_thread.daemon = True
        if job.cfg.type.lower() == 'analysis':
            self.engine_thread = threading.Thread(target=self.engine)
        elif job.cfg.type.lower() == 'maintenance':
            self.engine_thread = threading.Thread(target=self.maintain)
        self.engine_thread.daemon = True
        self.stop_flag = threading.Event()

    def start(self):
        signal.signal(signal.SIGINT, sigint_handler)
        self.stop_flag.clear()
        self.vm_mgr_thread.start()
        self.engine_thread.start()
        self.engine_thread.join()

    def stop(self):
        POOL.terminate()
        self.cleanup()

    def get_vm(self):
        vm = None
        while not vm:
            try:
                vm = self.vm_queue.get(True, 300)
            except Empty:
                self.vm_mgr.reset_vms()
        return vm

    def engine(self):
        for job in self.job.jobs:
            vm = self.get_vm()
            task = Task(self.job.cfg, vm, job.name, job.path)
            print "%s" % task
            POOL.apply_async(self.job.tool.run, (task,), callback=self.job.tool.callback)
        log.debug("All jobs assigned in scheduler engine")
        self.cleanup()

    def maintain(self):
        vms = []
        while not self.vm_queue.empty():
            try:
                vms.append(self.vm_queue.get(block=True, timeout=5))
            except Empty:
                break
        tasks = [Task(self.job.cfg, vm) for vm in vms]
        rv = POOL.map_async(self.job.tool.run, tasks)
        for task in tasks:
            log.debug("%s" % task)
        rv.wait()
        log.debug(rv.get())
        self.cleanup()

    @staticmethod
    def cleanup():
        log.debug("Cleaning up")
        POOL.close()
        POOL.join()
        log.debug("Pool closed")
