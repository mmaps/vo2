import sys
import logging
from time import sleep, time
from xmlrpclib import ServerProxy
from threading import Thread
from Queue import Full

from vlibs.proc_mgmt import ProcMgr

CMD = r'/usr/bin/VBoxManage'
EXEDIR = r'c:\remote\bin'
USER = 'logger'
KEY = r'c:\remote\keys\voo_priv.ppk'
PSCP = r'c:\remote\bin\pscp.exe'
WINSCP = r'c:\remote\bin\winscp.exe'

UNKNOWN = -1
POWEROFF = 0
SAVED = 1
RUNNING = 2
ABORTED = 3


class VirtualMachine(object):

    def __init__(self, name, addr, port, host_addr):
        """
        :type self.msgs: multiprocessing.Queue
        :type self.guest: vo2.net.guest.EvalServer
        :return:
        """
        self.name = name
        self.addr = addr
        self.host_addr = host_addr
        self.port = port
        self.proc = ProcMgr()
        self.msgs = None
        self.guest = None
        self.sniff = False
        self.state = -1
        self.state_str = ''
        self.busy = False

    def start(self):
        self.debug("Start %s [%s:%s]" % (self.name, self.addr, self.port))

        self.update_state()
        self.debug("current state: %s" % self.state_str)

        if self.state is RUNNING:
            self.debug("needs to be shut down")
            return False

        cmd = [CMD, 'startvm', self.name]
        self.debug("starting: %s" % cmd)
        if self.proc.exec_quiet(cmd) != 0:
            self.error('start failure: %s' % cmd)
            return False
        sleep(.5)

        if not self.wait_agent():
            return False

        self.debug("agent online")
        return True

    def wait_agent(self):
        self.debug("waiting for agent to come online")
        t = Thread(target=self._wait_agent)
        t.daemon = True
        t.start()
        t.join(30)
        if t.is_alive():
            self.debug("timeout waiting for agent")
            self.poweroff()
            return False
        return True

    def poweroff(self):
        self.debug("powering off")
        rv = True
        cmd = [CMD, 'controlvm', self.name, 'poweroff']
        if self.proc.exec_quiet(cmd) != 0:
            self.error('poweroff error: %s' % cmd)
            rv = False
        sleep(1)
        self.guest = None
        return rv

    def restore(self, name=''):
        self.debug("Checking state for restore")
        self.update_state()
        if self.state is POWEROFF or self.state is ABORTED:
            self.debug("Attempting restore")
            cmd = [CMD, 'snapshot', self.name]
            if name:
                cmd.extend(['restore', name])
            else:
                cmd.append('restorecurrent')
            self.debug("%s" % cmd)
            if self.proc.exec_quiet(cmd) != 0:
                return False
        return True

    def take_snap(self, name=''):
        if not name:
            name = str(time())
        cmd = [CMD, 'snapshot', self.name, 'take', name]
        if self.proc.exec_quiet(cmd) != 0:
            self.error('take_snap error: %s' % cmd)
            sys.exit(1)

    def del_snap(self, name):
        cmd = [CMD, 'snapshot', self.name, 'delete', name]
        if self.proc.exec_quiet(cmd) != 0:
            self.error('del_snap error: %s' % cmd)
            sys.exit(1)

    def update_state(self):
        cmd = [CMD, 'showvminfo', self.name, '--machinereadable']
        self.debug("update state: %s" % cmd)
        pid = self.proc.execute(cmd)
        out, err = self.proc.get_output(pid)
        if not out:
            self.state = UNKNOWN
            self.state_str = 'unknown'
            return self.state
        for line in out.split('\n'):
            if line.startswith('VMState='):
                st = line.partition('=')[2].strip('"')
                if st == 'running':
                    self.state = RUNNING
                    self.state_str = 'running'
                elif st == 'saved':
                    self.state = SAVED
                    self.state_str = 'saved'
                elif st == 'poweroff':
                    self.state = POWEROFF
                    self.state_str = 'poweroff'
                elif st == 'aborted':
                    self.state = ABORTED
                    self.state_str = 'aborted'
                return self.state

    def start_sniff(self):
        cmd = [CMD, 'controlvm', self.name, 'nictrace1', 'on']
        self.debug("start pcap: %s" % cmd)
        if self.proc.exec_quiet(cmd) != 0:
            self.error('start_sniff error: %s' % cmd)
            return False
        self.sniff = True
        return True

    def stop_sniff(self):
        cmd = [CMD, 'controlvm', self.name, 'nictrace1', 'off']
        self.debug("stop pcap: %s" % cmd)
        if self.proc.exec_quiet(cmd) != 0:
            self.error('stop_sniff error: %s' % cmd)
            return False
        self.sniff = False
        return True

    def set_pcap(self, filepath):
        cmd = [CMD, 'controlvm', self.name, 'nictracefile1', filepath]
        self.debug("set_pcap: %s" % cmd)
        if self.proc.exec_quiet(cmd) != 0:
            self.error('set_pcap error: %s' % cmd)
            return False
        return True

    def reset(self):
        self.poweroff()
        self.restore()
        self.start()

    def connect(self):
        try:
            self.guest = ServerProxy("http://%s:%s" % (self.addr, self.port), verbose=False)
        except Exception as e:
            self.error("connect error: %s" % e)
            return False
        else:
            return True

    def _wait_agent(self):
        while not self.ping_agent():
            self.ping_agent()
            sleep(.5)

    def ping_agent(self):
        if self.connect():
            return self.guest.ping()

    def release(self):
        """
        :type self.msgs: multiprocessing.Queue
        """
        try:
            self.msgs.put(self.name, True, 60)
        except (AttributeError, Full):
            sys.stderr.write("%s: unable to signal completion to VM manager. Messages queue not set\n" % self.name)

    def guest_cmd(self, cmd):
        self.debug("guest_cmd: %s\n" % cmd)
        rv, out, err = self.guest.execute(cmd)
        if out:
            self.debug(out)
        if err:
            self.error(err)
        return rv

    def push(self, type_, user, src, dst):
        if type_ == "winscp":
            rv = self.winscp_push(user, src, dst)
        elif type_ == "pscp":
            rv = self.pscp_push(user, src, dst)
        else:
            sys.stderr.write("Unknown push method: %s\n" % type_)
            rv = False
        return rv
    
    def pull(self, type_, user, src, dst):
        if type_ == "winscp":
            rv = self.winscp_pull(user, src, dst)
        elif type_ == "pscp":
            rv = self.pscp_pull(user, src, dst)
        else:
            sys.stderr.write("Unknown pull method: %s\n" % type_)
            rv = False
        return rv

    def winscp_push(self, user, src, dst):
        self.debug("winscp_push: %s -> %s\n" % (src, dst))
        cmd = [EXEDIR + '\\winscp.exe',
               '/console', '/command',
               '"option confirm off"',
               '"option batch abort"',
               '"open %s@%s -hostkey=* -privatekey=%s"' % (user, self.host_addr, KEY),
               '"get %s %s"' % (src, dst),
               '"exit"']
        cmd = ' '.join(cmd)
        return self.guest_cmd(cmd)

    def winscp_pull(self, user, src, dst):
        self.debug("winscp_pull: %s -> %s\n" % (src, dst))
        cmd = [EXEDIR + '\\winscp.exe',
               '/console', '/command',
               '"option confirm off"',
               '"option batch abort"',
               '"open %s@%s -hostkey=* -privatekey=%s"' % (user, self.host_addr, KEY),
               '"put -nopreservetime -transfer=binary %s %s"' % (src, dst),
               '"exit"']
        cmd = ' '.join(cmd)
        return self.guest_cmd(cmd)

    def pscp_pull(self, user, src, dst):
        if not self.guest:
            return False
        cmd = 'echo y | "%s" -r -i "%s" %s@%s:"%s" "%s"' % (PSCP, KEY, user, self.host_addr, src, dst)
        self.debug(cmd)
        return self.guest.execute(cmd)

    def pscp_push(self, user, src, dst):
        if not self.guest:
            return False
        cmd = 'echo y | "%s" -i "%s" "%s" %s@%s:"%s"' % (PSCP, KEY, src, user, self.host_addr, dst)
        self.debug(cmd)
        return self.guest.execute(cmd)

    def terminate_pid(self, pid):
        if not self.guest:
            return False
        cmd = 'taskkill /f /t /pid %s' % pid
        self.debug(cmd)
        return self.guest.execute(cmd)

    def terminate_name(self, p_name):
        if not self.guest:
            return False
        cmd = 'taskkill /f /t /IM %s' % p_name
        self.debug(cmd)
        return self.guest.execute(cmd)

    def error(self, msg):
        logging.error('%s(%s:%s),%s: %s' % (self.name, self.addr, self.port, self.state_str, msg))

    def debug(self, msg):
        logging.debug('%s(%s:%s),%s: %s' % (self.name, self.addr, self.port, self.state_str, msg))

    def __str__(self):
        self.update_state()
        return "%s[%s:%s], %s => Host: %s" % (self.name, self.addr, self.port, self.state_str, self.host_addr)
