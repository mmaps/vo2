import argparse
import sys
from collections import namedtuple

from guests.factory import Factory
from jobs.job import Job
from jobs.scheduler import Scheduler
from conf.vcfg import Config
from util import logs

VCFG = "conf/vo2.cfg"

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
    log.info("VO2 Start")

    vo2_cfg = load_config(cli_args.vo2_cfg)
    job_cfg = load_config(cli_args.job_cfg)
    job_cfg.set("job", "debug", cli_args.debug)

    job = Job(vo2_cfg.get_namespace("general"), job_cfg.get_namespace("job"))
    if not job.setup():
        log.error("Failed to create job")
        sys.exit(1)

    vm_factory = Factory(vo2_cfg)

    scheduler = Scheduler(job, vm_factory)
    scheduler.start()

    log.info("VO2 Exiting")
