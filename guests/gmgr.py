import sys
import logging

from threading import Thread, Event
from multiprocessing import Manager
from Queue import Empty

import gpool


class GuestManager(object):

    def __init__(self, vm_list):
        self.log = logging.getLogger("vo2.%s" % __name__)
        self.machines = vm_list
        self.vm_map = {}
        self.pool = None
        self.mgr = Manager()
        self.msgs = self.mgr.Queue()
        self.reader = Thread(target=self.check_msgs)
        self.reader.daemon = True
        self.stop = Event()

    def populate_map(self, settings):
        factory = VmFactory()
        for vm in self.machines:
            vm_obj = factory.make(vm, settings.get(vm))
            if vm_obj:
                self.vm_map[vm] = vm_obj

    def fill_pool(self, vm_map):
        self.pool = gpool.GuestPool(vm_map)

    def find_vm(self, names, queue):
        while True:
            for name in names:
                vm = self.pool.acquire(name)
                if vm:
                    vm.msgs = self.msgs
                    queue.put(vm)

    def release_vm(self, name):
        self.pool.release(name)

    def checking(self, start=True):
        if start:
            self.reader.start()
        else:
            self.stop.set()

    def check_msgs(self):
        while not self.stop.is_set():
            msg = self.msgs.get()
            self.release_vm(msg)

    def reset_vms(self):
        for name in self.machines:
            vm = self.vm_map.get(name)
            if vm and not vm.busy:
                self.msgs.put(vm)


