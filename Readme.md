# VO2 lightweight analysis engine (alpha product)

## Dependencies
- Python 2.7
- VirtualBox

## Installation

### Host Installation
- Clone this repo.

- Configure the VirtualBox guests.
  - For effective isolation they should be configured with a "Host Only" interface. 
  - For effective pcaps they should all be assigned to a separate "Host Only" interface. This is done with the VirtualBox main network preferences. Please refer to [their documentation](https://www.virtualbox.org/manual/ch06.html#network_hostonly)

- Record the configuration in a conformant config file in `"conf/"`. The default is `"conf/myfirstconfig.cfg"`.

  - Conformant config files follow Python's `ConfigParser` api: [ConfigParser](https://docs.python.org/2/library/configparser.html)

- Ensure that any folders needed for execution are created. eg Logging or output directories. These should be configured with access for the guests to write. 
  - vo2 will by default attempt to write as the user `logger` using public key authentication.
  - This depends on your tools and job configurations
  - eg The default `pin.cfg` job file will expect `/Volumes/Macintosh_HD_2/voodo_log` for the `log` variable and `/Volumes/Macintosh_HD_2/voodo_log` for the `jobdir` variable

- Create a set of keys for the user `logger` to authenticate with. These should be kept in the `remote/keys` folder, and are included when copying this folder to the guest for installation.
  - Add the public key to your `authorized_keys` file in order for the agents to be able to log things to the host over the network.

### Guest Installation
- Copy the folder `remote/` and its contents to the guest root folder `c:\`
  - If `c:\` is not the root you should update the variables at the top of `vo2\guests\vbox.py`

- Setup any folders that you will want to reference in your script
  - This depends on your job tool specification
  - The default pin.cfg job requires the following directories in addition to `remote\`:
    - `c:\malware\` Is the `"guestworkingdir"` where samples are pushed to.
    - `c:\malware\spoofs\` Is the `"spoofdir"` where rundll32.exe and its spoofed alternatives are kept.

## Running
1. Create a job config file if you're not using the default pin config, or alter an existing config if necessary.
  - You can also create custom tools. They require an entry in your config file, and a `run(task)` method.
    - Refer to the source for `work/task.py` API. Documentation forthcoming.
  - The following are strongly advised if you want this to work:
    - The `host_tool` field in your config file is required to follow the Python dot format.
      - eg The default pin config file points to `tools/pin.py` which is `tools.pin`
    - The `vms` variable is a CSV list of the names of VirtualBox guests. Completely arbitrary.
    - The `type` variable is not yet implemented
    - The `name` variable will define directories and output labeling
    - The `jobdir` defines the directory where samples to be analyzed are. This program uses the `vlib/scandir.py` module to effectively iterate flat structures with enormous amounts of files without slowing down execution. Refer to the module for more information, license, etc.
  - The `log` variable defines where `vo2` will output the logs!
2. The guest agent(s) must be started first or the engine will not be able to communicate with them
3. Save the running agents and the configured guest to a screenshot.
  - The default setup and teardown actions will restore to the current (most recent in the change tree) screen shot.

### Guest Execution
Start the agent in a cmd prompt with:
- ```python rpcserver.py [address port type] [debug]``` 
  - If you don't specify address, port, and type then the server will default to all interfaces (0.0.0.0), port 4828, and the RPC server.
  - If you specify debug then there will be some useful messages output. This isn't really useful in bulk analysis.

### Host Execution
Start the engine with:
- ```python vo2.py </path/to/job-config-file>```
- The job config file contains all the information about your job
- The VO2 config file contains all settings related to VO2 and your guests. To change it you may alter the variable `VCFG` in `vo2.py`.
Wait patiently.
