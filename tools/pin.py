import os

from util import files


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

    guest_dir = tsk.cfg.get("job", "guestworkingdir")

    bincmd += '"%s"' % tsk.sample.name
    cmd = ' -- '.join([pincmd, bincmd])
    tsk.log("CMD: %s" % cmd)

    rv = tsk.vm.launch(cmd, exec_time=execution_time, verbose=True, working_dir=tsk.cfg.get("job", "guestworkingdir"))
    tsk.log("Launch RV: %s" % rv)

    if rv:
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
        tsk.log("Tool error: unknown file type: %s, %s\n" % (tsk.sample.name, tsk.sample.filetype))
        rv = False

    return rv
