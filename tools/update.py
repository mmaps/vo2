import os
import random
import threading
from time import sleep
import sys


def run(tsk):
    """

    :type tsk: jobs.task.Task
    """
    tsk.setup_vm()
    tsk.load(os.path.join(os.getcwd(), "remote"), "tmp")
    sleep(3)

    tmp_port = random.randint(1025, 65000)

    cmd = "start c:\\python27\\python.exe c:\\tmp\\rpcserver.py 0.0.0.0 %d vserver.EvalServer debug" % (tmp_port)
    tsk.log("TOOL:"+cmd)
    tsk.vm.launch(cmd, working_dir=r"c:\\")
    sleep(3)

    def close_server():
        print 'Closing agent'
        tsk.log("Closing agent")
        tsk.vm._guest.guest_eval("import os;print 'EXITING!';os._exit(0)")

    thread = threading.Thread(target=close_server)
    thread.start()
    thread.join(timeout=5)
    sleep(5)

    tsk.log("Connecting to temporary agent")
    tsk.vm.connect(tsk.vm.addr, tmp_port)

    tsk.log("Waiting for agent to be online")
    if not tsk.vm._guest.ping():
        tsk.log("Update failed. Could not connect to temp agent")
        sys.exit()

    cmd = "rmdir /S /Q c:\\remote"
    tsk.log("TOOL:"+cmd)
    tsk.vm.launch(cmd, working_dir=r"c:\\")
    sleep(5)

    cmd = "xcopy /I /E c:\\tmp c:\\remote"
    tsk.log("TOOL:"+cmd)
    tsk.vm.launch(cmd, working_dir=r"c:\\", verbose=True)
    sleep(5)

    cmd = "start c:\\python27\\python.exe c:\\remote\\rpcserver.py debug"
    tsk.log("TOOL:"+cmd)
    tsk.vm.launch(cmd, working_dir=r"c:\\")
    sleep(5)

    thread = threading.Thread(target=close_server)
    thread.start()
    thread.join(timeout=5)

    tsk.log("Connecting to new, updated agent")
    tsk.vm.connect()
    tsk.vm._guest.ping()

    cmd = "rmdir /S /Q c:\\tmp"
    tsk.log("TOOL:"+cmd)
    tsk.vm.launch(cmd, working_dir=r"c:\\", verbose=True)
    sleep(5)

    tsk.log("Snapshot...")
    tsk.vm.take_snap("NewSnapshot")
    tsk.teardown_vm()
