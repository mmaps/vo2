import os
import sys
import logging as log
from time import sleep
from vcfg import Config
from guests import gman
from vlibs.scandir import scandir
from work.scheduler import Scheduler
from work.job import Job


VCFG = 'conf/myfirstconf.cfg'

samples = []

if 'debug' in sys.argv:
    log.basicConfig(level=log.DEBUG)

try:
    job_cfg = Config(sys.argv[1])
    vo2_cfg = Config(VCFG)
except IndexError:
    log.error("Job job_cfg file not found: %s" % os.path.join('conf', sys.argv[1]))
    sys.exit(0)

if not job_cfg.parsed:
    log.error("Bad job_cfg file failed to parse: %s\n" % sys.argv[1])
    sys.exit(0)

if not vo2_cfg.parsed:
    log.error("Bad vcfg file failed to parse: %s\n" % VCFG)
    sys.exit(0)

if job_cfg.jobdir:
    if not os.path.isdir(job_cfg.jobdir):
        log.error("Argument 'jobdir' is not a directory: %s\n" % job_cfg.jobdir)
        sys.exit(0)
    samples = scandir(job_cfg.jobdir)

log.info('V CFG:\n%s\nJob Cfg:\n%s' % (vo2_cfg, job_cfg))

job_cfg_ns = job_cfg.namespace()
vcfg_ns = vo2_cfg.namespace()

job = Job(samples, job_cfg_ns)
if not job.setup():
    log.error("Job setup failed. Exiting")
    sys.exit(1)

host_vms = sorted([vm.rstrip() for vm in vcfg_ns.vms.split(',')])
vm_settings = dict(zip(host_vms, [getattr(vcfg_ns, vm) for vm in host_vms]))
gmgr = gman.GuestManager(host_vms, vm_settings)
gmgr.populate_map(vm_settings)
gmgr.fill_pool(gmgr.vm_map)
gmgr.checking(start=True)

scheduler = Scheduler(job, gmgr)
scheduler.start()
