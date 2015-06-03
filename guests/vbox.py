import sys
import logging
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

    def launch(self):
        pass

    def restart(self):
        pass

    def start(self):
        self.debug("Start %s [%s:%s]" % (self.name, self.addr, self.port))

        self.update_state()
        self.debug("current state: %s" % self.state_str)

        if self.is_running():
            self.debug("needs to be shut down")
            return False

        cmd = [CMD, 'startvm', self.name, '--type', 'headless']
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
        t.join(self.cfg.wait)
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
            sleep(1)

    def ping_agent(self):
        if self.connect():
            return self.guest_cmd("echo \r\n\r\nHost Connected\r\n\r\n", 1)

    def release(self):
        """
        :type self.msgs: multiprocessing.Queue
        """
        try:
            self.msgs.put(self.name, True, 60)
        except (AttributeError, Full):
            sys.stderr.write("%s: unable to signal completion to VM manager. Messages queue not set\n" % self.name)

    def guest_cmd(self, cmd, exec_time=30, verbose=False, working_dir=''):
        self.debug("guest_cmd: %s\n" % cmd)

        rv = False
        rpc_num_try = 0

        while not rv and rpc_num_try < self.rpc_max_try:
            try:
                rv, out, err = self.guest.execute(cmd, exec_time, verbose, working_dir)
            except Exception as e:
                if e.errno == 61:
                    """
                    Connection Refused, this is expected if the guest is loading
                    """
                    pass
                else: 
                    self.error("Error executing RPC on %s\n\t%s\n\t%s" % (self, cmd, e))
            else:
                if out:
                    self.debug(out)
                if err:
                    self.error(err)
            finally:
                if not rv:
                    rpc_num_try += 1
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
               '"open %s@%s -hostkey=* -privatekey=%s"' % (user, self.gateway, KEY),
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
               '"open %s@%s -hostkey=* -privatekey=%s"' % (user, self.gateway, KEY),
               '"put -nopreservetime -transfer=binary %s %s"' % (src, dst),
               '"exit"']
        cmd = ' '.join(cmd)
        return self.guest_cmd(cmd)

    def pscp_pull(self, user, src, dst):
        if not self.guest:
            return False
        cmd = 'echo y | "%s" -r -i "%s" %s@%s:"%s" "%s"' % (PSCP, KEY, user, self.gateway, src, dst)
        self.debug(cmd)
        return self.guest.execute(cmd)

    def pscp_push(self, user, src, dst):
        if not self.guest:
            return False
        cmd = 'echo y | "%s" -i "%s" "%s" %s@%s:"%s"' % (PSCP, KEY, src, user, self.gateway, dst)
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


