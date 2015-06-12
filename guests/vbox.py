import re
import socket
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
WINSCP = r'c:\remote\bin\winscp.exe'


class VirtualMachine(VirtualDevice):

    hostif = dict()
    proc = ProcessManager()

    def start(self):
        self.debug("Start %s [%s:%s]" % (self.name, self.addr, self.port))

        self.update_info()
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
            self.debug("Timeout waiting for agent.")
            self.force_arp()
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
        return not t.is_alive()

    def _wait_agent(self):
        while not self.ping_agent():
            self.debug("Ping %s" % self.name)
            sleep(1)

    def ping_agent(self):
        rv = False
        if self.connect():
            try:
                rv = self._guest.ping()
            except socket.error as e:
                if e.errno is 60:
                    """
                    Timed out
                    """
                    self.error("Ping timed out")
                else:
                    self.error("Ping error: %s" % e)
        return rv

    def force_arp(self):
        try:
            macaddr = self.get_nic_mac(1)
        except IndexError:
            return False
        cmd = ["sudo", "arp", "-S", self.addr, macaddr, "temp"]
        self.debug("Setting ARP manually: %s" % macaddr)
        self.proc.execute(cmd, verbose=True)

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
        self.update_info()
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

    def reset_state(self):
        self.hostif = dict()
        self.state = self.UNKNOWN
        self.state_str = 'unknown'

    def update_info(self):
        self.reset_state()
        cmd = [CMD, 'showvminfo', self.name, '--machinereadable']
        self.debug("Update VM information")
        pid = self.proc.execute(cmd)
        out, err = self.proc.get_output(pid)
        vm_info = self.parse_vminfo(out)
        if vm_info:
            self.update_state(vm_info)
            self.update_network(vm_info)

    def parse_vminfo(self, stdout):
        vminfo = {}
        try:
            lines = stdout.split("\n")
            for line in lines:
                if line:
                    key, val = self.parse_infoline(line)
                    vminfo[key] = val
        except AttributeError as e:
            self.error("Unable to parse 'showvminfo': %s" % e)
            vminfo = {}
        return vminfo

    def parse_infoline(self, infoline):
        key, _, value = infoline.partition("=")
        if value.startswith('"'):
            value = value.strip('"')
        else:
            try:
                value = int(value)
            except (ValueError, TypeError):
                self.error("Unable to interpret VM info for %s" % infoline)
                value = ''
        return key, value

    def update_state(self, vminfo):
        st = vminfo.get("VMState")
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
            self.debug("Unknown VM state: %s" % st)
            self.state = self.UNKNOWN
            self.state_str = 'unknown'
            return self.state

    def update_network(self, vminfo):
        nics = self.find_nics(vminfo.keys())
        for nic in nics:
            self.update_nic(vminfo, nic)

    def find_nics(self, keylist):
        nicpattern = re.compile("nic\d\d?")
        nics = [key for key in keylist if nicpattern.match(key)]
        self.debug("VM NICs found: %s" % nics)
        return nics

    def update_nic(self, vminfo, nic_name):
        nic_num = self.parse_nicname(nic_name)
        if vminfo.get(nic_name) == "hostonly":
            self.update_hostif(vminfo, nic_num)

    def update_hostif(self, vminfo, num):
        self.debug("Found Host Only Interface: %s" % num)
        try:
            mac = vminfo["macaddress%d" % num]
        except (TypeError, KeyError):
            mac = "FF:FF:FF:FF:FF:FF"
        self.set_nic_mac(num, mac)

    def set_nic_mac(self, nic_num, mac):
        self.debug("Setting NIC MAC address: %s,%s" % (nic_num, mac))
        try:
            self.hostif[nic_num] = {"type": "hostonly", "num": nic_num, "mac": mac}
        except KeyError:
            self.error("Unknown NIC number: %s, %s" % (nic_num, mac))

    def get_nic_mac(self, nic_num):
        try:
            mac = self.hostif[nic_num]
        except KeyError:
            mac = "FF:FF:FF:FF:FF:FF"
        return mac

    def parse_nicname(self, nic_name=''):
        """

        :type nic_name: str
        :rtype: int
        """
        try:
            num = int(nic_name.replace("nic", ""))
        except (ValueError, TypeError):
            self.error("Unable to determine NIC number: %s" % nic_name)
            num = -1
        return num

    def parse_hostif(self, adapter_num):
        _, adapter, num = adapter_num.partition("hostonlyadapter")
        self.debug("Parsed %s: %s,%s" % (adapter_num, adapter, num))
        return adapter, num

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

        rv = False
        rpc_num_try = 0

        while not rv and rpc_num_try < self.rpc_attempts:
            self.debug("guest_cmd: %s, time=%s, verbose=%s, dir=%s, try=%s" % (cmd, exec_time, verbose, working_dir, rpc_num_try))
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
                self.error("Launch error: %s\n%s" % (cmd, e))
            else:
                if out:
                    self.debug(out)
                if err:
                    self.error(err)
            finally:
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
               '"option batch abort"',
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

