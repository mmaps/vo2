import os
import Queue
import signal
import sys
import logging as log
from subprocess import Popen, PIPE
from threading import Thread


class ProcessManager(object):
    
    def __init__(self):
        #self.devnull = open(os.devnull, 'w')
        self.procs = {}

    def exec_quiet(self, cmd, timeout=60):
        log.debug("exec_quiet: %s" % cmd)
        use_shell = True
        if isinstance(cmd, list):
            use_shell = False
        try:
            proc = Popen(cmd, shell=use_shell)
        except OSError as e:
            log.error('exec_null error: %s\n\tcmd: %s' % (e, cmd))
            return 1
        else:
            rc, out, err = self.cleanup_proc(proc, timeout)
            if err:
                log.error("exec_quiet error: %s = %s" % (cmd, err))
            return rc

    def execute(self, cmd, verbose=False, fatal=False):
        log.debug("execute: %s, %s, %s" % (cmd, verbose, fatal))
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
            log.error("execute error: %s = %s" % (cmd_str, err))
            if not fatal:
                return -1
            else:
                sys.exit(1)
        else:
            self.procs[proc.pid] = proc
            return proc.pid

    def get_output(self, pid, timeout=180):
        try:
            proc = self.procs.pop(pid)
        except KeyError:
            log.error("process mgr: get_output on unknown PID: %s" % pid)
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
            log.error("process mgr: end_process on unknown PID: %s" % pid)
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
            log.error("cleanup proc timeout on %s" % proc.pid)
            rc = 1
            out = ''
            err = self.end_proc(proc.pid)
        else:
            rc, out, err = results.get()
        return rc, out, err

    def _communicate(self, proc, result_qu):
        out, err = proc.communicate()
        result_qu.put((proc.poll(), out, err))

    def _join(self, proc, result_qu):
        proc.wait()
        result_qu.put((proc.poll(), '', ''))
