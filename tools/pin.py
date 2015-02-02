import logging as log
import os
import sys
from time import sleep
from catalog.samples import Sample


def analyze(task, pincmd, bincmd, execution_time, suffix='pe32'):
    task.log("LYZER BEGIN\n\tLYZER Execution time: %s s\n" % execution_time)
    task.log("LYZER setting up VM: %s\n" % task.vm.name)
    if not task.setup_vm(suffix=".%s" % suffix):
        task.log("LYZER error setting up VM, ending analysis run\n")
        log.error("LYZER error setting up VM, ending analysis run\n")
        return
    task.log("LYZER VM running\n")

    bincmd += '"%s\\%s"' % (task.cfg.guestworkingdir, task.sample.name)
    cmd = ' -- '.join([pincmd, bincmd])
    rv = task.run_sample(cmd, execution_time, task.cfg.guestworkingdir)
    if not rv:
        task.log("LYZER execution on guest failure\n\tLYZER Tear Down VM: %s\n" % task.vm)
        task.teardown_vm()
        return

    src = '\\'.join([task.cfg.guestworkingdir, task.cfg.pinlog])
    dst = '%s.%s.txt' % (task.sample.name, suffix)
    task.log("LYZER pulls from: %s\n\tLYZER pulls to: %s\n" % (src, dst))
    task.retval = task.get_results(src, dst)
    if not task.retval:
        log.error("Failed to pull pin log from guest: %s -> %s\n" % (src, dst))
        src = '\\'.join([task.cfg.guestworkingdir, 'pin.log'])
        dst = dst.replace(".txt", ".error.txt")
        task.log("LYZER error in pulling log file. Trying pin.txt error file\n")
        task.log("LYZER pulls from: %s\n\tLYZER pulls to: %s\n" % (src, dst))
        task.get_results(src, dst)

    task.log("LYZER Tear Down VM:%s\n" % task.vm.name)
    task.teardown_vm()
    task.log("LYZER END\n\n")


def run(task):
    task.log("RUN Sample: %s\nRUN Sample Type: %s = %s\n" % (task.sample.name, task.sample.filetype, task.sample.type))

    if not task.init():
        log.error("RUN init failed\n")
        return task

    pincmd = task.cfg.pincmd.format(pinbat=task.cfg.pinbat, pintool=task.cfg.pintool)
    spoofs = task.cfg.spoofs.split(',')
    try:
        execution_time = int(task.cfg.exectime)
    except ValueError:
        task.log("RUN 'exectime' not set in cfg. Exiting.\n")
        log.error("Run 'exectime' not set in cfg. Exiting.")
        sys.exit(0)

    if task.sample.type is Sample.PDF:
        task.log("RUN PDF: %s" % task.sample.name)
        execution_time *= 2
        bincmd = '"%s" ' % task.cfg.pdfreader
        analyze(task, pincmd, bincmd, execution_time, 'pdf')

    elif task.sample.type is Sample.DLL:
        task.log("RUN DLL: %s\n RUN DLL Spoofs: %s\n" % (task.sample.name, spoofs))
        for s in spoofs:
            task.log("RUN SPOOF: %s %s" % (s, task.sample.name))
            bincmd = '"%s\\spoofs\\%s" ' % (task.cfg.guestworkingdir, s)
            analyze(task, pincmd, bincmd, execution_time, s)

    elif task.sample.type is Sample.EXE:
        analyze(task, pincmd, '', execution_time)

    elif task.sample.type is Sample.DOS:
        task.log("RUN FAIL: %s, %s\n" % (task.sample.name, task.sample.filetype))
    else:
        task.log("RUN FAIL: %s, %s\n" % (task.sample.name, task.sample.filetype))

    task.log("RUN ENDS\n")
    task.close_log()
    return task


def callback(task):
    print("CALLBACK")
    log.debug("TASK Callback VM: %s\tSample: %s\tType: %s" % (task.vm.name, task.sample.name, task.sample.type))
    task.complete()
