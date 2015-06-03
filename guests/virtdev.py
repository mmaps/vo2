import abc


class VirtualDevice(object):

    __metaclass__ = abc.ABCMeta

    UNKNOWN = -1
    POWEROFF = 0
    SAVED = 1
    RUNNING = 2
    ABORTED = 3

    def __init__(self, name, addr, port, gateway):
        self.msgs = None
        self.guest = None
        self.sniff = False
        self.state = -1
        self.state_str = ''
        self.busy = False

        self.name = name
        self.addr = addr
        self.gateway = gateway
        self.port = port

    @abc.abstractmethod
    def start(self):
        pass

    @abc.abstractmethod
    def poweroff(self):
        pass

    @abc.abstractmethod
    def restart(self):
        pass

    @abc.abstractmethod
    def restore(self):
        pass

    @abc.abstractmethod
    def wait_agent(self):
        pass

    @abc.abstractmethod
    def update_state(self):
        pass

    @abc.abstractmethod
    def start_sniff(self):
        pass

    @abc.abstractmethod
    def stop_sniff(self):
        pass

    @abc.abstractmethod
    def push(self):
        pass

    @abc.abstractmethod
    def pull(self):
        pass

    @abc.abstractmethod
    def launch(self):
        pass

    def get_state(self):
        return self.state_str

    def is_running(self):
        return self.state == self.RUNNING

    def is_saved(self):
        return self.state == self.SAVED

    def is_off(self):
        return self.state == self.POWEROFF

    def is_aborted(self):
        return self.state == self.ABORTED

    def is_busy(self):
        return self.busy

    def set_busy(self):
        self.busy = True

    def __str__(self):
        return "%s@%s:%s,%s,gw@%s" % (self.name, self.addr, self.port, self.state_str, self.gateway)

