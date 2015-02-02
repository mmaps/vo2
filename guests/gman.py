import sys
import logging
from importlib import import_module
from threading import Thread, Event
from multiprocessing import Manager
from Queue import Empty

import gpool


class GuestManager(object):

    def __init__(self, vm_list, vm_settings):
        self.machines = vm_list
        self.settings = vm_settings
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


class VmFactory(object):

    def make(self, vmname, settings):
        if not settings:
            return None
        type_, os, addr, port, host_addr = settings.split(',')
        vm = self.instanciate(vmname, type_, os, addr, port, host_addr)
        return vm

    def instanciate(self, name, type_, os, addr, port, host_addr):
        try:
            gmodule = import_module('guests.%s' % type_)
        except ImportError as e:
            sys.stderr.write("%s\n\n" % e)
            sys.stderr.write("Unable to import virtual device module: %s\n" % type_)
            return None
        else:
            sys.stdout.write("Register VM: %s @ %s:%s -> %s\n" % (name, addr, port, host_addr))
            return gmodule.VirtualMachine(name, addr, port, host_addr)
