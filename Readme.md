# VO2 lightweight analysis engine
<hr>

[TOC]

<hr>
## Dependencies
- Python 2.7
- VirtualBox

<hr>
## Installation


### Host Installation
- Clone this repo.
- Configure the VirtualBox guests
- Record the configuration in a conformant config file in `"conf/"`. The default is `"conf/myfirstconfig.cfg"`.
- Conformant config files follow Python's `ConfigParser` api: [^ConfigParser]

### Guest Installation
- Copy the folder `remote/` and its contents to the guest
- Setup any folders that you will want to reference in your script
- The default pin.cfg job requires the following directories in addition to `remote\`:
> `c:\malware\` Is the `"guestworkingdir"` where samples are pushed to.
> `c:\malware\spoofs\` Is the `"spoofdir"` where rundll32.exe and its spoofed alternatives are kept.

<hr>
## Running
- The guest agent(s) must be started first or the engine will not be able to communicate with them
- Save the running agents and the configured guest to a screenshot.
- The default setup and teardown actions will restore to the current (most recent in the change tree) screen shot.

### Guest Execution
Start the agent in a cmd prompt with:
: ```python rpcserver.py [address port type] [debug]``` 
: If you don't specify address, port, and type then the server will default to all interfaces (0.0.0.0), port 4828, and the RPC server.
: If you specify debug then there will be some useful messages output. This isn't really useful in bulk analysis.

### Host Execution
Start the engine with:
: ```python vo2.py </path/to/job-config-file>```
: The job config file contains all the information about your job
: The VO2 config file contains all settings related to VO2 and your guests. To change it you may alter the variable `VCFG` in `vo2.py`.

[ConfigParser](https://docs.python.org/2/library/configparser.html)
