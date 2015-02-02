# VO2 lightweight analysis engine

<hr>
## Dependencies
- Python 2.7
- VirtualBox

<hr>
## Installation

### Host Installation
- Clone this repo.
- Configure the VirtualBox guests.
  - For effective isolation they should be configured with a "Host Only" interface. 
  - For effective pcaps they should all be assigned to a separate "Host Only" interface. This is done with the VirtualBox main network preferences. Please refer to [their documentation](https://www.virtualbox.org/manual/ch06.html#network_hostonly)
- Record the configuration in a conformant config file in `"conf/"`. The default is `"conf/myfirstconfig.cfg"`.
- Conformant config files follow Python's `ConfigParser` api: [ConfigParser](https://docs.python.org/2/library/configparser.html)
- Ensure that any folders needed for execution are created. eg Logging or output directories. These should be configured with access for the guests to write. The guests will by default attempt to write as the user `logger` using public key authentication.
- Create a set of keys for the user `logger` to authenticate with. These should be kept in the `remote/keys` folder, and are included when copying this folder to the guest for installation.
  - Add the public key to your `authorized_keys` file in order for the agents to be able to log things to the host over the network.

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

