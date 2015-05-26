import argparse
import sys
from collections import namedtuple

from guests.factory import Factory
from jobs.job import Job
from jobs.scheduler import Scheduler
from conf.vcfg import Config
from util import logs

VCFG = "conf/vo2.cfg"
VCFG_VM_KEY = "g_"

log = None

Sample = namedtuple("Sample", "name path")


def parse_cli_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('job_cfg', help='File containing a list of files or a directory of files to be processed')
    parser.add_argument('-c', '--vo2_cfg', help='Configuration file for VO2 framework. Default: %s' % VCFG,
                        default=VCFG)
    parser.add_argument('-d', '--debug', action='store_true')
    args = parser.parse_args()
    return args


def load_config(cfg_file):
    log.debug("Getting config file: %s" % cfg_file)
    cfg = Config()
    if not cfg.load(cfg_file):
        log.error("Failed to parse: %s" % cfg_file)
        sys.exit(1)
    return cfg


if __name__ == "__main__":
    cli_args = parse_cli_args()
    log = logs.init_logging("vo2", cli_args.debug)
    log.info("VO2 Script Start")

    vo2_cfg = load_config(cli_args.vo2_cfg)
    vo2_cfg.set("general", "debug", cli_args.debug)

    job_cfg = load_config(cli_args.job_cfg)
    job_cfg.set("job", "debug", cli_args.debug)

    cfg = Config()
    cfg.add_settings(vo2_cfg)
    cfg.add_settings(job_cfg)

    job = Job(cfg)
    if not job.setup():
        log.error("Failed to create job. Exiting.")
        sys.exit(1)

    vm_factory = Factory(vo2_cfg.find_all(VCFG_VM_KEY))
    job_vms = job_cfg.get("job", "vms")
    if job_vms:
        vm_factory.use_vms(job_vms.split(","))

    scheduler = Scheduler(job, vm_factory)
    scheduler.start()

    log.info("VO2 Script End")
