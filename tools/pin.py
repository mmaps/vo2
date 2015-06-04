import os

from util import files


def analyze(tsk, pincmd, bincmd, execution_time, suffix='pe32'):
    """

    :type tsk: jobs.task.Task
    """
    tsk.setup_vm()

    if tsk.cfg.get_bool("job", "pcap"):
        tsk.start_pcap(name_suffix=".%s" % suffix)

    bincmd += '"%s"' % tsk.sample.name
    cmd = ' -- '.join([pincmd, bincmd])
    rv = tsk.vm.launch(cmd, exec_time=execution_time, verbose=True, working_dir=tsk.cfg.get("job", "guestworkingdir"))

    if rv:
        src = tsk.cfg.get("job", "pinlog")
        dst = os.path.join(tsk.logdir, '%s.%s.txt' % (tsk.sample.name, suffix))
        tsk.vm.pull(tsk.cfg.get("job", "user"), src, dst)
        if not os.path.isfile(dst):
            src = tsk.cfg.get("job", "pinerror")
            dst = dst.replace(".txt", ".error.txt")
            tsk.vm.pull(tsk.cfg.get("job", "user"), src, dst)
            rv = False

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
    exec_time = tsk.cfg.get("job", "exec_time")
    guest_dir = tsk.cfg.get("job", "guestworkingdir")
    pdfreader = tsk.cfg.get("job", "pdfreader")

    pincmd = pincmd.format(pinbat=pinbat, pintool=pintool)
    spoofs = spoofs.split(',')

    if tsk.sample.type is files.PDF:
        exec_time *= 2
        bincmd = '"%s" ' % pdfreader
        rv = analyze(tsk, pincmd, bincmd, exec_time, 'pdf')

    elif tsk.sample.type is files.DLL:
        for s in spoofs:
            bincmd = '"%s\\spoofs\\%s" ' % (guest_dir, s)
            rv = analyze(tsk, pincmd, bincmd, exec_time, s)

    elif tsk.sample.type is files.EXE:
        rv = analyze(tsk, pincmd, '', exec_time)

    else:
        tsk.log("Tool error: unknown file type: %s, %s\n" % (tsk.sample.name, tsk.sample.filetype))
        rv = False

    return rv
