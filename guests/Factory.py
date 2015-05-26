import logging
from importlib import import_module


CFG_VM_KEY = "g_"


class Factory(object):

    def __init__(self, guests):
        self.log = logging.getLogger("vo2.%s" % __name__)
        self.guest_cfgs = guests

    def use_vms(self, vms):
        self.log.debug("Use VMs: %s" % vms)
        job_guests = {}
        for vm in vms:
            if vm in self.guest_cfgs:
                job_guests[vm] = self.guest_cfgs.get(vm)
            else:
                self.log.debug("Unknown VM specified in job config: %s" % vm)
        if len(vms) > 0:
            self.guest_cfgs = job_guests
        self.log.debug("Set VMs to use: %s" % self.guest_cfgs.keys())

    def list(self):
        return self.guest_cfgs.keys()

    def get(self, name):
        guest = None
        cfg = self.guest_cfgs.get(name)
        try:
            gmodule = import_module('guests.%s' % cfg.get('type'))
        except ImportError as e:
            self.log.error("Unable to import virtual device module 'guests.%s': %s" % (cfg.get('type'), e))
        except AttributeError:
            self.log.error("Unknown VM: %s" % name)
        else:
            self.log.info("Register VM: %s @ %s:%s -> %s" % (name, cfg.get('address'),
                                                             cfg.get('port'), cfg.get('gateway')))
            guest = gmodule.VirtualMachine(name, cfg.get('address'), cfg.get('port'), cfg.get('gateway'))
        finally:
            return guest
