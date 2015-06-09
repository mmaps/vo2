import os
import threading
from time import sleep

def run(tsk):
    """

    :type tsk: jobs.task.Task
    """
    tsk.setup_vm()
    tsk.load(os.path.join(os.getcwd(), "remote"), "tmp")

    cmd = "start c:\\python27\\python.exe c:\\tmp\\rpcserver.py 0.0.0.0 %d vserver.EvalServer debug" % (tsk.vm.port+1)
    tsk.log("TOOL:"+cmd)
    tsk.vm.launch(cmd, working_dir=r"c:\\")
    sleep(3)

    def close_server():
        tsk.log("Closing agent")
        tsk.vm._guest.guest_eval("import os;os._exit(0)")

    thread = threading.Thread(target=close_server)
    thread.start()
    thread.join(timeout=5)

    tsk.log("Connecting to temporary agent")
    tsk.vm.port += 1
    tsk.vm.connect()

    cmd = "rmdir /S /Q c:\\remote"
    tsk.log("TOOL:"+cmd)
    tsk.vm.launch(cmd, working_dir=r"c:\\", verbose=True)
    sleep(5)

    cmd = "xcopy /I /E c:\\tmp c:\\remote"
    tsk.log("TOOL:"+cmd)
    tsk.vm.launch(cmd, working_dir=r"c:\\", verbose=True)
    sleep(5)

    cmd = "start c:\\python27\\python.exe c:\\remote\\rpcserver.py 0.0.0.0 %d vserver.EvalServer debug" % (tsk.vm.port-1)
    tsk.log("TOOL:"+cmd)
    tsk.vm.launch(cmd, working_dir=r"c:\\")
    sleep(5)

    thread = threading.Thread(target=close_server)
    thread.start()
    thread.join(timeout=5)

    tsk.log("Connecting to new, updated agent")
    tsk.vm.port -= 1
    tsk.vm.connect(tsk.vm.addr, tsk.vm.port)

    cmd = "rmdir /S /Q c:\\tmp"
    tsk.log("TOOL:"+cmd)
    tsk.vm.launch(cmd, working_dir=r"c:\\", verbose=True)
    sleep(5)

    tsk.log("Snapshot...")
    tsk.vm.take_snap("NewSnapshot")
    tsk.teardown_vm()
