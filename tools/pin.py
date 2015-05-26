from util import files


def analyze(task, pincmd, bincmd, execution_time, suffix='pe32'):
    task.reset_vm()
    task.setup_pcap(name_suffix=".%s" % suffix)

    bincmd += '"%s\\%s"' % (task.cfg.guestworkingdir, task.sample.name)
    cmd = ' -- '.join([pincmd, bincmd])
    rv = task.run_sample(cmd, execution_time, task.cfg.guestworkingdir)
    if not rv:
        task.teardown_vm()
        return

    src = '\\'.join([task.cfg.get("job", "guestworkingdir"), task.cfg.get("job", "pinlog")])
    dst = '%s.%s.txt' % (task.sample.name, suffix)
    task.retval = task.get_results(src, dst)
    if not task.retval:
        src = '\\'.join([task.cfg.guestworkingdir, 'pin.log'])
        dst = dst.replace(".txt", ".error.txt")
        task.get_results(src, dst)

    task.teardown_vm()

def run(task):
    print 'Run'

'''
def run(task):
    """

    :type task: jobs.task.Task
    """
    task.reset_vm()

    pinbat = task.cfg.get("job", "pinbat")
    pintool = task.cfg.get("job", "pintool")
    pincmd = task.cfg.get("job", "pincmd")
    spoofs = task.cfg.get("job", "spoofs")
    exec_time = task.cfg.get("job", "exec_time")
    guest_dir = task.cfg.get("job", "guestworkingdir")
    pdfreader = task.cfg.get("job", "pdfreader")

    pincmd = pincmd.format(pinbat=pinbat, pintool=pintool)
    spoofs = spoofs.split(',')

    if task.sample.type is files.PDF:
        exec_time *= 2
        bincmd = '"%s" ' % pdfreader
        analyze(task, pincmd, bincmd, exec_time, 'pdf')

    elif task.sample.type is files.DLL:
        for s in spoofs:
            bincmd = '"%s\\spoofs\\%s" ' % (guest_dir, s)
            analyze(task, pincmd, bincmd, exec_time, s)

    elif task.sample.type is files.EXE:
        analyze(task, pincmd, '', exec_time)

    else:
        task.log("RUN fail on unknown file type: %s, %s\n" % (task.sample.name, task.sample.filetype))

'''
