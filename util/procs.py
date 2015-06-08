import os
import Queue
import signal
import sys
from subprocess import Popen, PIPE
from threading import Thread


PROCERR = 1
PROCWARN = -1


class ProcessManager(object):
    
    def __init__(self):
        self.devnull = open(os.devnull, 'w')
        self.procs = {}
        self.log = None

    def log(self, msg):
        try:
            self.log(msg)
        except TypeError:
            sys.stderr.write("ProcessManager log function not set: %s" % msg)

    def exec_quiet(self, cmd, timeout=60):
        self.log("exec_quiet: %s" % cmd)
        use_shell = True
        if isinstance(cmd, list):
            use_shell = False
        try:
            proc = Popen(cmd, shell=use_shell, stdout=self.devnull, stderr=self.devnull)
        except OSError as e:
            self.log('exec_null error: %s\n\tcmd: %s' % (e, cmd))
            return PROCERR
        else:
            rc, out, err = self.cleanup_proc(proc, timeout)
            if err:
                self.log("exec_quiet error: %s = %s" % (cmd, err))
            return rc

    def execute(self, cmd, verbose=False, fatal=False):
        self.log("execute: %s, %s, %s" % (cmd, verbose, fatal))
        cmd_str = cmd
        use_shell = True
        if isinstance(cmd, list):
            cmd_str = ' '.join(cmd)
            use_shell = False
        if verbose:
            sys.stdout.write("%s\n" % cmd_str)
        try:
            proc = Popen(cmd, preexec_fn=os.setsid, shell=use_shell, stdout=PIPE, stderr=PIPE)
        except OSError as err:
            self.log("execute error: %s = %s" % (cmd_str, err))
            if not fatal:
                return PROCWARN
            else:
                sys.exit(PROCERR)
        else:
            self.procs[proc.pid] = proc
            return proc.pid

    def get_output(self, pid, timeout=180):
        try:
            proc = self.procs.pop(pid)
        except KeyError:
            self.log("process mgr: get_output on unknown PID: %s" % pid)
            out = ''
            err = 'UNKNOWN PID: %s' % pid
        else:
            rc, out, err = self.cleanup_proc(proc, timeout, True)
        return out, err

    def end_proc(self, pid):
        rv = 'SIGTERM'
        try:
            proc = self.procs.pop(pid)
        except KeyError:
            self.log("process mgr: end_process on unknown PID: %s" % pid)
            rv = 'UNKNOWN PID: %s' % pid
        else:
            os.killpg(pid, signal.SIGTERM)
            # Specific test for only None
            if proc.poll() is None:
                os.killpg(pid, signal.SIGKILL)
                rv = 'SIGKILL'
        return rv

    def cleanup_proc(self, proc, timeout, output=False):
        results = Queue.Queue()
        if output:
            target_handle = self._communicate
        else:
            target_handle = self._join
        t = Thread(target=target_handle, args=(proc, results))
        t.start()
        t.join(timeout)
        if t.is_alive():
            self.log("cleanup proc timeout on %s" % proc.pid)
            rc = PROCERR
            out = ''
            err = self.end_proc(proc.pid)
        else:
            rc, out, err = results.get()
        return rc, out, err

    @staticmethod
    def _communicate(proc, result_qu):
        out, err = proc.communicate()
        result_qu.put((proc.poll(), out, err))

    @staticmethod
    def _join(proc, result_qu):
        proc.wait()
        result_qu.put((proc.poll(), '', ''))
