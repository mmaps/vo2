import os
import threading
import time
from util import files


def remote_run(tsk, cmd, execution_time, verbose, working_dir, retval):
    tsk.log("remote run: %s" % cmd)
    retval = tsk.vm.launch(cmd, exec_time=execution_time, verbose=verbose, working_dir=working_dir)


def analyze(tsk, pincmd, bincmd, execution_time, suffix='pe32'):
    """

    :type tsk: jobs.task.Task
    """
    if not tsk.setup_vm():
        tsk.log("VM setup failed")
        return False

    if not tsk.load_sample():
        tsk.log("Could not load sample on VM")
        return False

    if tsk.cfg.get_bool("job", "pcap"):
        tsk.log("Starting PCAP for %s" % suffix)
        tsk.start_pcap(name_suffix=".%s" % suffix)

    interactive = False
    if tsk.cfg.get_bool("job", "interactive"):
        tsk.log("Running in interactive mode")
        tsk.load(os.path.join(os.getcwd(), "remote/bin/clicks.exe"), "clicks.exe")
        tsk.load(os.path.join(os.getcwd(), "remote/bin/clicker.exe"), "clicker.exe")
        interactive = True
    else:
        tsk.log("NON-interactive mode")

    guest_dir = tsk.cfg.get("job", "guestworkingdir")

    bincmd += '"%s"' % tsk.sample.name
    cmd = ' -- '.join([pincmd, bincmd])
    tsk.log("CMD: %s" % cmd)

    analysis_rv = True
    analysis_thread = threading.Thread(target=remote_run, args=(tsk, cmd, execution_time, True,
                                                                tsk.cfg.get("job", "guestworkingdir"), analysis_rv))
    analysis_thread.start()

    if interactive:
        """
        Pause for sample to start
        """
        time.sleep(5)

        """
        Simulate 3 clicks
        """
        tsk.log("Running clicks")
        cmd = guest_dir + "clicks.exe"
        clicks_rv = True
        clicks_thread = threading.Thread(target=remote_run, args=(tsk, cmd, execution_time, True,
                                                                  tsk.cfg.get("job", "guestworkingdir"), clicks_rv))
        clicks_thread.start()
        clicks_thread.join()

        """
        Walk through install dialogs
        """
        tsk.log("Running clicker")
        cmd = guest_dir + "clicker.exe " + guest_dir + r"\\clicker-log.txt"
        clicker_rv = True
        clicker_thread = threading.Thread(target=remote_run, args=(tsk, cmd, execution_time, True,
                                                                   tsk.cfg.get("job", "guestworkingdir"), clicker_rv))
        clicker_thread.start()

    analysis_thread.join()
    if analysis_rv:
        rv = analysis_rv
        src = tsk.cfg.get("job", "pinlog")
        dst = os.path.join(tsk.logdir, '%s.%s.txt' % (tsk.sample.name, suffix))
        tsk.log("Getting results: %s, %s" % (src, dst))
        tsk.vm.pull(tsk.cfg.get("job", "user"), src, dst, guest_dir)
        if not os.path.isfile(dst):
            src = tsk.cfg.get("job", "pinerror")
            dst = dst.replace(".txt", ".error.txt")
            tsk.log("Getting errors: %s, %s" % (src, dst))
            tsk.vm.pull(tsk.cfg.get("job", "user"), src, dst, guest_dir)
            rv = False

    if tsk.cfg.get_bool("job", "pcap"):
        tsk.stop_pcap()

    tsk.teardown_vm()
    return rv


def run(tsk):
    """

    :type tsk: jobs.task.Task
    """
    pinbat = tsk.cfg.get("job", "pinbat")
    pintool = tsk.cfg.get("job", "pintool")
    pincmd = tsk.cfg.get("job", "pincmd")
    spoofs = tsk.cfg.get("job", "spoofs")
    exec_time = tsk.cfg.get_float("job", "exectime")
    guest_dir = tsk.cfg.get("job", "guestworkingdir")
    pdfreader = tsk.cfg.get("job", "pdfreader")

    pincmd = pincmd.format(pinbat=pinbat, pintool=pintool)
    spoofs = spoofs.split(',')

    if tsk.sample.filetype is files.PDF:
        tsk.log("Analyzing PDF")
        exec_time *= 2
        bincmd = '"%s" ' % pdfreader
        rv = analyze(tsk, pincmd, bincmd, exec_time, 'pdf')

    elif tsk.sample.filetype is files.DLL:
        for s in spoofs:
            tsk.log("Analyzing DLL with %s" % s)
            bincmd = '"%s\\spoofs\\%s" ' % (guest_dir, s)
            rv = analyze(tsk, pincmd, bincmd, exec_time, s)

    elif tsk.sample.filetype is files.EXE:
        tsk.log("Analyzing EXE")
        rv = analyze(tsk, pincmd, '', exec_time)

    else:
        tsk.log("Tool error: unknown file type: %s, %s" % (tsk.sample.name, tsk.sample.filetype))
        rv = False

    return rv
