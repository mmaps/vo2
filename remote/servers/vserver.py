import os
import logging as log
from multiprocessing import Process, Queue
from Queue import Empty
from subprocess import Popen, PIPE
from traceback import format_exc


class VServer(object):

    results = Queue()

    @staticmethod
    def ping():
        return True

    def vexec(self, cmd, use_shell, qout):
        try:
            child = Popen(cmd, shell=use_shell)
        except (OSError, ValueError) as error:
            log.error('%s' % error)
            qout.put([False, '', '%s\n%s' % (format_exc(), error)])
        else:
            child.wait()
            qout.put([True, '', ''])

    def vexec_output(self, cmd, use_shell, qout):
        log.info("exec_output shell: %s\tcmd: %s" % (use_shell, cmd))
        try:
            child = Popen(cmd, shell=use_shell, stdout=PIPE, stderr=PIPE)
        except (OSError, ValueError) as error:
            log.error('%s' % error)
            qout.put([False, '', '%s\n%s' % (format_exc(), error)])
        else:
            stdout, stderr = child.communicate()
            log.info("STDOUT: %s\nSTDERR: %s" % (stdout, stderr))
            qout.put([True, stdout, stderr])

    def execute(self, cmd, timeout=0, verbose=False, work_dir=None):
        shell = not isinstance(cmd, list)

        target = self.vexec
        if verbose:
            target = self.vexec_output

        cwd = os.getcwd()
        if work_dir and not self.to_work_dir(work_dir):
            return [False, '', 'Unable to change to working directory: %s' % work_dir]

        stdout = ''
        stderr = ''
        try:
            rv = True
            p = Process(target=target, args=(cmd, shell, self.results))
            p.start()
        except Exception as e:
            rv = False
            stderr = 'execute error: %s\n%s' % (format_exc(), e)
        else:
            log.debug("Waiting on process execution: %s sec" % timeout)
            p.join(timeout)
            if p.is_alive():
                log.debug("Child is alive. Terminating child process")
                p.terminate()

        log.debug("Gathering results")
        try:
            rv, stdout, stderr = self.results.get(True, 3)
            log.debug("[RV:\n%s\nSOut:\n%s\nSErr:\n%s]" % rv, stdout, stderr)
        except Empty:
            log.debug("[Empty Results]")

        os.chdir(cwd)

        return [rv, stdout, stderr]

    @staticmethod
    def to_work_dir(work_dir):
        try:
            os.chdir(work_dir)
        except OSError as err:
            log.error("Execute unable to change to working dir: %s\n%s" % (work_dir, err))
            return False
        else:
            return True


class EvalServer(VServer):

    def guest_eval(self, src):
        try:
            code_obj = compile(src, "<string>", "exec")
        except (SyntaxError, TypeError) as e:
            return [False, str(e)]
        else:
            rv, msg = self.run_arbitrary_code(code_obj)
            return [rv, msg]

    def run_arbitrary_code(self, code_obj):
        try:
            exec code_obj
        except Exception as e:
            return [False, str(e)]
        return [True, '']
