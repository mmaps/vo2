import sys
from time import sleep, time
from xmlrpclib import ServerProxy
from threading import Thread
from Queue import Full

from util.procs import ProcessManager
from virtdev import VirtualDevice


CMD = r'/usr/bin/VBoxManage'
EXEDIR = r'c:\remote\bin'
USER = 'logger'
KEY = r'c:\remote\keys\voo_priv.ppk'
PSCP = r'c:\remote\bin\pscp.exe'
WINSCP = r'c:\remote\bin\winscp.exe'


class VirtualMachine(VirtualDevice):

    proc = ProcessManager()

    def start(self):
        self.debug("Start %s [%s:%s]" % (self.name, self.addr, self.port))

        self.update_state()
        self.debug("current state: %s" % self.state_str)

        if self.is_running():
            self.debug("needs to be shut down")
            return False

        cmd = [CMD, "startvm", self.name]
        if self.headless:
            if not self.is_off():
                self.error("vm is not powered off. Headless VMs must be saved in an off state")
                return False
            cmd.extend(["--type", "headless"])

        self.debug("starting: %s" % cmd)
        if self.proc.exec_quiet(cmd) != 0:
            self.debug('start failure: %s' % cmd)
            return False
        sleep(.5)

        if not self.wait_agent():
            return False

        self.debug("Agent online")
        return True

    def wait_agent(self):
        self.debug("Waiting for agent to come online")
        t = Thread(target=self._wait_agent)
        t.daemon = True
        t.start()
        t.join(self.timeout_vm)
        if t.is_alive():
            self.debug("Timeout waiting for agent")
            self.poweroff()
            return False
        return True

    def _wait_agent(self):
        while not self.ping_agent():
            self.debug("Ping %s" % self.name)
            self.ping_agent()
            sleep(1)

    def ping_agent(self):
        if self.connect():
            self.debug("pinged agent")
            return self.launch("echo Host Connected", 1, working_dir="C:\\malware")
        else:
            self.debug("agent did not respond")
        return False

    def connect(self, addr=None, port=None):
        if not addr:
            addr = self.addr
        if not port:
            port = self.port
        try:
            http_addr = "http://%s:%s" % (addr, port)
            self.debug("Connecting to %s" % http_addr)
            self._guest = ServerProxy(http_addr, verbose=False)
        except Exception as e:
            self.debug("connect error: %s" % e)
            return False
        else:
            return True

    def poweroff(self):
        self.debug("powering off")
        rv = True
        cmd = [CMD, 'controlvm', self.name, 'poweroff']
        if self.proc.exec_quiet(cmd) != 0:
            self.debug('poweroff error: %s' % cmd)
            rv = False
        sleep(1)
        self._guest = None
        return rv

    def restore(self, name=''):
        self.debug("Checking state for restore")
        self.update_state()
        if self.is_off() or self.is_aborted():
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
            self.debug('take_snap error: %s' % cmd)
            return False

    def del_snap(self, name):
        cmd = [CMD, 'snapshot', self.name, 'delete', name]
        if self.proc.exec_quiet(cmd) != 0:
            self.debug('del_snap error: %s' % cmd)
            return False

    def update_state(self):
        cmd = [CMD, 'showvminfo', self.name, '--machinereadable']
        self.debug("update state: %s" % cmd)
        pid = self.proc.execute(cmd)
        out, err = self.proc.get_output(pid)
        if not out:
            self.state = self.UNKNOWN
            self.state_str = 'unknown'
            return self.state
        for line in out.split('\n'):
            if line.startswith('VMState='):
                st = line.partition('=')[2].strip('"')
                if st == 'running':
                    self.state = self.RUNNING
                    self.state_str = 'running'
                elif st == 'saved':
                    self.state = self.SAVED
                    self.state_str = 'saved'
                elif st == 'poweroff':
                    self.state = self.POWEROFF
                    self.state_str = 'poweroff'
                elif st == 'aborted':
                    self.state = self.ABORTED
                    self.state_str = 'aborted'
                else:
                    self.state = self.UNKNOWN
                    self.state_str = 'unknown'
                return self.state

    def start_sniff(self):
        cmd = [CMD, 'controlvm', self.name, 'nictrace1', 'on']
        self.debug("start pcap: %s" % cmd)
        if self.proc.exec_quiet(cmd) != 0:
            self.debug('start_sniff error: %s' % cmd)
            return False
        self.wait_agent()
        return True

    def stop_sniff(self):
        cmd = [CMD, 'controlvm', self.name, 'nictrace1', 'off']
        self.debug("stop pcap: %s" % cmd)
        if self.proc.exec_quiet(cmd) != 0:
            self.debug('stop_sniff error: %s' % cmd)
            return False
        self.wait_agent()
        return True

    def set_pcap(self, filepath):
        cmd = [CMD, 'controlvm', self.name, 'nictracefile1', filepath]
        self.debug("set_pcap: %s" % cmd)
        if self.proc.exec_quiet(cmd) != 0:
            self.debug('set_pcap error: %s' % cmd)
            return False
        return True

    def reset(self):
        self.poweroff()
        self.restore()
        self.start()

    def release(self):
        """
        :type self.msgs: multiprocessing.Queue
        """
        try:
            self.msgs.put(self.name, True, 60)
        except (AttributeError, Full):
            sys.stderr.write("%s: unable to signal completion to VM manager. Messages queue not set\n" % self.name)

    def launch(self, cmd, exec_time=30, verbose=False, working_dir=''):
        self.debug("guest_cmd: %s, time=%s, verbose=%s, dir=%s\n" % (cmd, exec_time, verbose, working_dir))

        rv = False
        rpc_num_try = 0

        while not rv and rpc_num_try < self.rpc_attempts:
            try:
                rv, out, err = self._guest.execute(cmd, exec_time, verbose, working_dir)
            except TypeError:
                self.error("Launch error, guest object does not exist")
                return False
            except Exception as e:
                """
                if e.errno == 61:
                    Connection Refused, this is expected if the guest is loading
                    pass
                else:
                """
                self.debug("Launch error: %s\n%s" % (cmd, e))
            else:
                if out:
                    self.debug(out)
                if err:
                    self.error(err)
            finally:
                if not rv:
                    rpc_num_try += 1
        return rv

    def push(self,user, src, dst, dir_):
        rv = self.winscp_push(user, src, dst, dir_)
        return rv
    
    def pull(self, user, src, dst, dir_):
        rv = self.winscp_pull(user, src, dst, dir_)
        return rv

    def winscp_push(self, user, src, dst, dir_):
        self.debug("winscp_push: %s -> %s\n" % (src, dst))
        cmd = [EXEDIR + '\\winscp.exe',
               '/console', '/command',
               '"option confirm off"',
               #'"option batch abort"',
               '"open %s@%s -hostkey=* -privatekey=%s"' % (user, self.gateway, KEY),
               '"get %s %s"' % (src, dst),
               '"exit"']
        cmd = ' '.join(cmd)
        return self.launch(cmd, exec_time=300, working_dir=dir_)

    def winscp_pull(self, user, src, dst, dir_):
        self.debug("winscp_pull: %s -> %s\n" % (src, dst))
        cmd = [EXEDIR + '\\winscp.exe',
               '/console', '/command',
               '"option confirm off"',
               '"option batch abort"',
               '"open %s@%s -hostkey=* -privatekey=%s"' % (user, self.gateway, KEY),
               '"put -nopreservetime -transfer=binary %s %s"' % (src, dst),
               '"exit"']
        cmd = ' '.join(cmd)
        return self.launch(cmd, exec_time=300, working_dir=dir_)

    def terminate_pid(self, pid):
        if not self._guest:
            return False
        cmd = 'taskkill /f /t /pid %s' % pid
        self.debug(cmd)
        return self._guest.execute(cmd)

    def terminate_name(self, p_name):
        if not self._guest:
            return False
        cmd = 'taskkill /f /t /IM %s' % p_name
        self.debug(cmd)
        return self._guest.execute(cmd)

    def set_log(self, log):
        self.log = log
        self.proc.log = log

    def error(self, msg):
        try:
            self.log('vm - error - %s(%s:%s): %s' % (self.name, self.addr, self.port, msg))
        except TypeError:
            sys.stderr.write('vm - error - %s(%s:%s): %s' % (self.name, self.addr, self.port, msg))

    def debug(self, msg):
        try:
            self.log('vm - debug - %s(%s:%s): %s' % (self.name, self.addr, self.port, msg))
        except TypeError:
            sys.stderr.write('vm - debug - %s(%s:%s): %s' % (self.name, self.addr, self.port, msg))

