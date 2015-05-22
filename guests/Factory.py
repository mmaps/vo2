import logging
from importlib import import_module


CFG_VM_KEY = "g_"


class Factory(object):

    def __init__(self, cfg):
        self.log = logging.getLogger("vo2.%s" % __name__)
        self.guest_cfgs = cfg.find_all(CFG_VM_KEY)
        self.log.debug("VM Factory configs: %s" % self.guest_cfgs)

    def list(self):
        return self.guest_cfgs.keys()

    def get(self, name):
        guest = None
        cfg = self.guest_cfgs.get(name)
        try:
            gmodule = import_module('guests.%s' % cfg.type)
        except ImportError as e:
            self.log.error("Unable to import virtual device module 'guests.%s': %s" % (cfg.type, e))
        else:
            self.log.info("Register VM: %s @ %s:%s -> %s" % (name, cfg.address, cfg.port, cfg.gateway))
            guest = gmodule.VirtualMachine(name, cfg.address, cfg.port, cfg.gateway)
        finally:
            return guest
