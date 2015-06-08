import logging


def init_logging(name, debug=False):
    log = logging.getLogger(name)
    console_hdlr = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s.%(msecs)d - %(levelname)s - %(name)s.%(funcName)s: %(message)s",
                                  datefmt="%H:%M:%S")
    console_hdlr.setFormatter(formatter)
    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.WARN)
    log.addHandler(console_hdlr)
    log.propagate = False
    log.debug("Debugging on")
    return log

