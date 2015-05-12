import argparse
import os
import sys
import logging as log
from collections import namedtuple
from time import sleep

from vcfg import Config
from guests import gman
from vlibs.scandir import scandir
from work.scheduler import Scheduler
from work.job import Job

VCFG = 'conf/myfirstconf.cfg'
Sample = namedtuple('Sample', 'name path')


def get_file_samples(fpath):
    rv = []
    try:
        fin = open(fpath, 'r')
    except IOError as e:
        log.error("IOError reading samples in job file: %s" % e)
        sys.exit(1)
    else:
        for line in fin:
            if line.startswith("#"):
                continue
            path = line.rstrip()
            name = os.path.basename(path)
            rv.append(Sample(name, path))
        fin.close()
    finally:
        return rv


parser = argparse.ArgumentParser()
parser.add_argument('job', help='File containing a list of files or a '\
        'directory of files to be processed')
parser.add_argument('-c', '--config',
        help='Configuration file for VO2 framework. Default: %s' % VCFG,
        default=VCFG)
parser.add_argument('-d', '--debug', action='store_true')

args = parser.parse_args()

if args.debug:
    log.basicConfig(level=log.DEBUG)


if not os.path.exists(args.job):
    log.error("Unable to locate config file: %s" % args.job)
    sys.exit(1)

if not os.path.exists(args.config):
    log.error("Unable to locate config file: %s" % args.config)
    sys.exit(1)


job_cfg = Config(args.job)
if not job_cfg.parsed:
    log.error("Bad job_cfg file failed to parse: %s" % args.job)
    sys.exit(1)

vo2_cfg = Config(args.config)
if not vo2_cfg.parsed:
    log.error("Bad vcfg file failed to parse: %s" % args.config)
    sys.exit(1)


if job_cfg.jobdir: 
    if not os.path.isdir(job_cfg.jobdir):
        log.error("Argument 'jobdir' is not a directory: %s" % job_cfg.jobdir)
        sys.exit(1)
    samples = scandir(job_cfg.jobdir)
elif job_cfg.jobfile:
    if not os.path.isfile(job_cfg.jobfile):
        log.error("Argument 'jobfile' is not a file: %s" % job_cfg.jobfile)
        sys.exit(1)
    samples = get_file_samples(job_cfg.jobfile)
else:
    log.error("Invalid config file. Missing jobfile or jobdir arguments")
    samples = None

if not samples:
    log.error("No samples found")
    sys.exit(1)


log.info("VO2 Config: %s\tJob Config: %s" % (vo2_cfg, job_cfg))
job_cfg_ns = job_cfg.namespace()
vcfg_ns = vo2_cfg.namespace()


job = Job(samples, job_cfg_ns)
if not job.setup():
    log.error("Job setup failed")
    sys.exit(1)


host_vms = sorted([vm.rstrip() for vm in vcfg_ns.vms.split(',')])
vm_settings = dict(zip(host_vms, [getattr(vcfg_ns, vm) for vm in host_vms]))


gmgr = gman.GuestManager(host_vms, vm_settings)
gmgr.populate_map(vm_settings)
gmgr.fill_pool(gmgr.vm_map)
gmgr.checking(start=True)


scheduler = Scheduler(job, gmgr)
scheduler.start()
