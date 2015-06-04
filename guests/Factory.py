import logging
from importlib import import_module


class Factory(object):

    def __init__(self, cfg):
        self.log = logging.getLogger("vo2.%s" % __name__)
        self.cfg = cfg

    def list_vms(self):
        try:
            vms = self.cfg.get("job", "vms").split(",")
        except AttributeError:
            self.log.warn("'vms' not set in job config")
            vms = []
        finally:
            self.log.debug("'vms' = %s" % vms)
            return vms

    def get(self, name):
        guest = None
        vm_section = "%s%s" % (self.cfg.get("general", "guest_name_prefix"), name)
        try:
            gmodule = import_module('guests.%s' % self.cfg.get(vm_section, "type"))
        except ImportError as e:
            self.log.error("Unable to import virtual device module 'guests.%s': %s" % (self.cfg.get(vm_section, "type"), e))
        except AttributeError:
            self.log.error("Unknown VM: %s" % name)
        else:
            guest = gmodule.VirtualMachine(name)
            self.configure_guest(guest)
        finally:
            self.log.debug("Factory made: %s" % guest)
            return guest

    def configure_guest(self, guest):
        section = "%s%s" % (self.cfg.get("general", "guest_name_prefix"), guest.name)
        guest.addr = self.cfg.get(section, "address")
        guest.port = self.cfg.get(section, "port")
        guest.gateway = self.cfg.get(section, "gateway")
        section = "timeouts"
        guest.rpc_attempts = self.cfg.get_float(section, "rpc_attmpts")
        guest.timeout_vm = self.cfg.get_float(section, "vm")
        guest.timeout_job = self.cfg.get_float(section, "rpc")
