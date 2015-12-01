#!/usr/bin/python2

from __future__ import print_function

import sys
import os
import os.path
import string
from random import Random
from types import StringTypes

from time import strftime
TIMEFORMAT="%Y-%m-%d %H:%M:%S"

NODEUPDATE_PID_FILE= "/var/run/NodeUpdate.pid"

# variables for cron file creation
TARGET_SCRIPT = '(echo && date && echo && /usr/bin/NodeUpdate.py start) >>/var/log/NodeUpdate.log 2>&1'
TARGET_DESC = 'Update node RPMs periodically'
TARGET_USER = 'root'
TARGET_SHELL = '/bin/bash'
CRON_FILE = '/etc/cron.d/NodeUpdate.cron'

YUM_PATH = "/usr/bin/yum"
DNF_PATH = "/usr/bin/dnf"
HAS_DNF = os.path.exists(DNF_PATH)

RPM_PATH = "/bin/rpm"

RPM_GPG_PATH = "/etc/pki/rpm-gpg"

# location of file containing http/https proxy info, if needed
PROXY_FILE = '/etc/planetlab/http_proxy'

# this is the flag that indicates an update needs to restart
# the system to take effect. it is created by the rpm that requested
# the reboot
REBOOT_FLAG = '/etc/planetlab/update-reboot'

# location of directory containing boot server ssl certs
SSL_CERT_DIR='/mnt/cdrom/bootme/cacert/'

# file containing the list of extensions this node has, each
# correspond to a package group in yum repository.
# this is expected to be updated from the 'extensions tag' 
# through the 'extensions.php' nodeconfig script
EXTENSIONS_FILE='/etc/planetlab/extensions'

# file containing a list of rpms that we should attempt to delete
# before updating everything else. This list is not removed with 
# 'yum remove', because that could accidently remove dependency rpms
# that were not intended to be deleted.
DELETE_RPM_LIST_FILE= '/etc/planetlab/delete-rpm-list'

# ok, so the logic should be simple, just yum update the world
# however there are many cases in the real life where this 
# just does not work, because of a glitch somewhere
# so, we force the update of crucial pkgs independently, as 
# the whole group is sometimes too much to swallow 
# this one is builtin
CRUCIAL_PACKAGES_BUILTIN=[
    'NodeUpdate',
    'nodemanager-lib',
    'nodemanager-lxc',
    'nodemanager-vs',
]
# and operations can also try to push a list through a conf_file
# should use the second one for consistency, try the first one as well for legacy
CRUCIAL_PACKAGES_OPTIONAL_PATHS = [
    # this is a legacy name, please avoid using this one
    '/etc/planetlab/NodeUpdate.packages',
    # file to use with a hand-written conf_file
    '/etc/planetlab/crucial-rpm-list',
    # this one could some day be maintained by a predefined config_file
    '/etc/planetlab/sliceimage-rpm-list',
]

# print out a message only if we are displaying output
def Message(*messages):
    if displayOutput:
        print(5*'*', strftime(TIMEFORMAT), *messages)

# always print errors
def Error(*messages):
    print(10*'!', strftime(TIMEFORMAT),*messages)

class YumDnf:
    def __init__(self):
        command = DNF_PATH if HAS_DNF else YUM_PATH
        self.command = command

        options = ""
        # --verbose option
        Message("Checking if {} supports --verbose".format(command))
        if os.system("{} --help | grep -q verbose".format(command)) == 0:
            Message("It does, using --verbose option")
            options += " --verbose"
        else:
            Message("Unsupported, not using --verbose option")
        # --sslcertdir option
        Message("Checking if {} supports SSL certificate checks"
                .format(command))
        if os.system("{} --help | grep -q sslcertdir".format(command)) == 0:
            Message("It does, using --sslcertdir option")
            sslcertdir = "--sslcertdir=" + SSL_CERT_DIR
        else:
            Message("Unsupported, not using --sslcertdir option")
            sslcertdir = ""
        self.options = options

    ########## one individual package
    def handle_package(self, package):
        if not self.is_packaged_installed(package):
            return self.do_package(package, "install")
        else:
            return self.do_package(package, "update")

    def is_packaged_installed(self, package):
        cmd = "rpm -q {} > /dev/null".format(package)
        return os.system(cmd) == 0

    def do_package(self, package, subcommand):
        cmd = \
            "{} {} -y {} {}".format(self.command, self.options,
                                    subcommand, package)
        Message("Invoking {}".format(cmd))
        return os.system(cmd) == 0

    ########## update one group
    def update_group(self, group):
        # it is important to invoke dnf group *upgrade* and not *update*
        # because the semantics of groups has changed within dnf
        if HAS_DNF:
            cmd = \
                "{} {} -y group upgrade {}".format(self.command, self.options, group)
        else:
            cmd = \
                "{} {} -y groupinstall {}".format(self.command, self.options, group)
        Message("Invoking {}".format(cmd))
        return os.system(cmd) == 0

    ########## update the whole system
    def update_system(self):
        cmd = "{} {} -y update".format(self.command, self.options)
        Message("Invoking {}".format(cmd))
        return os.system(cmd) == 0

    def clean_all(self):
        cmd = "{} clean all".format(self.command)
        Message("Invoking {}".format(cmd))
        return os.system(cmd) == 0

# create an entry in /etc/cron.d so we run periodically.
# we will be run once a day at a 0-59 minute random offset
# into a 0-23 random hour
def UpdateCronFile():
    try:
        
        randomMinute= Random().randrange(0, 59, 1);
        randomHour= Random().randrange(0, 11, 1);
        
        f = open(CRON_FILE, 'w');
        f.write("# {}\n".format(TARGET_DESC));
        ### xxx is root aliased to the support mailing list ?
        f.write("MAILTO={}\n".format(TARGET_USER));
        f.write("SHELL={}\n".format(TARGET_SHELL));
        f.write("{} {},{} * * * {} {}\n\n"
                .format (randomMinute, randomHour,
                         randomHour + 12, TARGET_USER, TARGET_SCRIPT));
        f.close()
    
        print("Created new cron.d entry.")
    except:
        print("Unable to create cron.d entry.")


# simply remove the cron file we created
def RemoveCronFile():
    try:
        os.unlink(CRON_FILE)
        print("Deleted cron.d entry.")
    except:
        print("Unable to delete cron.d entry.")
        


class NodeUpdate:

    def __init__(self, doReboot):
        if self.CheckProxy():
            os.environ['http_proxy']= self.HTTP_PROXY
            os.environ['HTTP_PROXY']= self.HTTP_PROXY
        self.doReboot= doReboot

    def CheckProxy(self):
        Message("Checking existence of proxy config file...")
        if os.access(PROXY_FILE, os.R_OK) and os.path.isfile(PROXY_FILE):
            self.HTTP_PROXY= string.strip(file(PROXY_FILE,'r').readline())
            Message("Using proxy {}".format(self.HTTP_PROXY))
            return 1
        else:
            Message("Not using any proxy.")
            return 0

    def InstallKeys(self):
        Message("Removing any existing GPG signing keys from the RPM database")
        os.system("{} --allmatches -e gpg-pubkey".format(RPM_PATH))
        Message("Installing all GPG signing keys in {}".format(RPM_GPG_PATH))
        os.system("{} --import {}/*".format(RPM_PATH, RPM_GPG_PATH))

    def ClearRebootFlag(self):
        os.system("/bin/rm -rf {}".format(REBOOT_FLAG))

    def CheckForUpdates(self):
        Message("Removing any existing reboot flags")
        self.ClearRebootFlag()
        if self.doReboot == 0:
            Message("Ignoring any reboot flags set by RPMs");
                    
        yum_dnf = YumDnf()

        # this of course is quite suboptimal, but proved to be safer
        yum_dnf.clean_all()

        # a configurable list of packages to try and update independently
        # cautious..
        try:
            crucial_packages = []
            for package in CRUCIAL_PACKAGES_BUILTIN:
                crucial_packages.append(package)
            for path in CRUCIAL_PACKAGES_OPTIONAL_PATHS:
                try:
                    crucial_packages += file(path).read().split()
                except:
                    pass
            Message("List of crucial packages: {}".format(crucial_packages))
            for package in crucial_packages:
                yum_dnf.handle_package(package)
        except:
            
            pass

        Message("Updating PlanetLab group")
        yum_dnf.update_group("PlanetLab")

        Message("Updating rest of system")
        yum_dnf.update_system()

        Message("Checking for extra groups (extensions) to update")
        if os.access(EXTENSIONS_FILE, os.R_OK) and \
           os.path.isfile(EXTENSIONS_FILE):
            extensions_contents= file(EXTENSIONS_FILE).read()
            extensions_contents= string.strip(extensions_contents)
            if extensions_contents == "":
                Message("No extra groups found in file.")
            else:
                extensions_contents.strip()
                for extension in extensions_contents.split():
                    group = "extension{}".format(extension)
                    yum_dnf.update_group(group)
        else:
            Message("No extensions file found")
            
        if os.access(REBOOT_FLAG, os.R_OK) and os.path.isfile(REBOOT_FLAG) and self.doReboot:
            Message("At least one update requested the system be rebooted")
            self.ClearRebootFlag()
            os.system("/sbin/shutdown -r now")

    def RebuildRPMdb(self):
        Message("Rebuilding RPM Database.")
        try:
            os.system("rm /var/lib/rpm/__db.*")
        except Exception as err:
            print("RebuildRPMdb: exception {}".format(err))
        try:
            os.system("{} --rebuilddb".format(RPM_PATH))
        except Exception as err:
            print("RebuildRPMdb: exception {}".format(err))

    def RemoveRPMS(self):
        Message("Looking for RPMs to be deleted.")
        if os.access(DELETE_RPM_LIST_FILE, os.R_OK) and \
           os.path.isfile(DELETE_RPM_LIST_FILE):
            rpm_list_contents= file(DELETE_RPM_LIST_FILE).read().strip()

            if rpm_list_contents == "":
                Message("No RPMs listed in file to delete.")
                return

            rpm_list= string.split(rpm_list_contents)
            
            Message("Deleting RPMs from {}: {}".format(DELETE_RPM_LIST_FILE," ".join(rpm_list)))

            # invoke them separately as otherwise one faulty (e.g. already uninstalled)
            # would prevent the other ones from uninstalling
            for rpm in rpm_list:
                # is it installed
                is_installed = os.system ("{} -q {}".format(RPM_PATH, rpm)) == 0
                if not is_installed:
                    Message ("Ignoring rpm {} marked to delete, already uninstalled".format(rpm))
                    continue
                uninstalled = os.system("{} -ev {}".format(RPM_PATH, rpm)) == 0
                if uninstalled:
                    Message ("Successfully removed RPM {}".format(rpm))
                    continue
                else:
                    Error("Unable to delete RPM {}, continuing. rc={}".format(rpm, uninstalled))
            
        else:
            Message("No RPMs list file found.")

##############################
if __name__ == "__main__":

    # if we are invoked with 'start', display the output. 
    # this is useful for running something silently 
    # under cron and as a service (at startup), 
    # so the cron only outputs errors and doesn't
    # generate mail when it works correctly

    displayOutput = 0

    # if we hit an rpm that requests a reboot, do it if this is
    # set to 1. can be turned off by adding noreboot to command line
    # option
    
    doReboot = 1

    if "start" in sys.argv or "display" in sys.argv:
        displayOutput = 1
        Message ("\nTurning on messages")

    if "noreboot" in sys.argv:
        doReboot = 0

    if "updatecron" in sys.argv:
        # simply update the /etc/cron.d file for us, and exit
        UpdateCronFile()
        sys.exit(0)

    if "removecron" in sys.argv:
        RemoveCronFile()
        sys.exit(0)     

            
    # see if we are already running by checking the existance
    # of a PID file, and if it exists, attempting a test kill
    # to see if the process really does exist. If both of these
    # tests pass, exit.
    
    if os.access(NODEUPDATE_PID_FILE, os.R_OK):
        pid= string.strip(file(NODEUPDATE_PID_FILE).readline())
        if pid <> "":
            if os.system("/bin/kill -0 {} > /dev/null 2>&1".format(pid)) == 0:
                Message("It appears we are already running, exiting.")
                sys.exit(1)
                    
    # write out our process id
    pidfile = file(NODEUPDATE_PID_FILE, 'w')
    pidfile.write("{}\n".format(os.getpid()))
    pidfile.close()

    
    nodeupdate = NodeUpdate(doReboot)
    if not nodeupdate:
        Error("Unable to initialize.")
    else:
        nodeupdate.RebuildRPMdb()
        nodeupdate.RemoveRPMS()
        nodeupdate.InstallKeys()
        nodeupdate.CheckForUpdates()
        Message("Update complete.")

    # remove the PID file
    os.unlink(NODEUPDATE_PID_FILE)
