import logging
import os

from libs import magic


UMASK = 0777
FILE_EXISTS = 17
ERR = -1
EXE = 0
PDF = 1
DLL = 2
DOS = 3
NEW = 4
DAT = 5

log = logging.getLogger("vo2.%s" % __name__)


def get_filetype(path):
    ftypename = intern("Unknown")

    if not path:
        ftype = NEW
        return ftype, ftypename

    if not os.path.isfile(path):
        ftype = ERR
        return ftype, ftypename

    ftypename = magic.from_file(path)

    if 'PDF' in ftypename:
        ftype = PDF
    elif 'PE32' in ftypename:
        if 'DLL' in ftypename:
            ftype = DLL
        else:
            ftype = EXE
    elif 'MS-DOS' in ftypename:
        ftype = DOS
    elif 'data' in ftypename:
        ftype = DAT
    else:
        ftype = ERR

    return ftype, ftypename


def resolve_path(full_path):
    path = os.path.expanduser(full_path)
    path = os.path.expandvars(path)
    path = os.path.abspath(path)
    return path


def filename(path):
    return os.path.basename(path)


def make_log_dir(dir_):
    log.debug("Making log directory: %s" % dir_)
    rv = True
    old_mask = os.umask(0000)
    try:
        os.makedirs(dir_, UMASK)
    except OSError as e:
        if e.errno is FILE_EXISTS:
            pass
        else:
            log.error("Error making log dir: %s" % e)
            rv = False
    os.umask(old_mask)
    return rv


def make_log_dir_version(dir_, name, sfx, ver):
    made = False
    old_mask = os.umask(0000)
    while not made:
        n = name + sfx % ver
        logdir = os.path.join(dir_, n)
        try:
            os.makedirs(logdir, UMASK)
        except OSError as e:
            if e.errno is FILE_EXISTS:
                ver += 1
            else:
                n = ''
                log.error("Job error making log dir: %s" % e)
                break
        else:
            made = True
    os.umask(old_mask)
    return n