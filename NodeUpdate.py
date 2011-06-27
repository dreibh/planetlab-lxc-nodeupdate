#!/usr/bin/python2

import sys, os
from random import Random
import string
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
CRUCIAL_PACKAGES_BUILTIN=[ 'NodeUpdate' , 'NodeManager' ]
# and operations can also try to push a list through a conf_file
# should use the second one for consistency, try the first one as well for legacy
CRUCIAL_PACKAGES_OPTIONAL_PATH1='/etc/planetlab/NodeUpdate.packages'
CRUCIAL_PACKAGES_OPTIONAL_PATH2='/etc/planetlab/crucial-rpm-list'


# print out a message only if we are displaying output
def Message(message):
    if displayOutput:
        if isinstance(message,StringTypes) and len(message) >=2 and message[0]=="\n":
            print "\n",
            message=message[1:]
        print strftime(TIMEFORMAT),
        print message

# always print errors
def Error(Str):
    print strftime(TIMEFORMAT),
    print Str


# create an entry in /etc/cron.d so we run periodically.
# we will be run once a day at a 0-59 minute random offset
# into a 0-23 random hour
def UpdateCronFile():
    try:
        
        randomMinute= Random().randrange( 0, 59, 1 );
        randomHour= Random().randrange( 0, 11, 1 );
        
        f = open( CRON_FILE, 'w' );
        f.write( "# %s\n" % (TARGET_DESC) );
        ### xxx is root aliased to the support mailing list ?
        f.write( "MAILTO=%s\n" % (TARGET_USER) );
        f.write( "SHELL=%s\n" % (TARGET_SHELL) );
        f.write( "%s %s,%s * * * %s %s\n\n" %
                 (randomMinute, randomHour, randomHour + 12, TARGET_USER, TARGET_SCRIPT) );
        f.close()
    
        print( "Created new cron.d entry." )
    except:
        print( "Unable to create cron.d entry." )


# simply remove the cron file we created
def RemoveCronFile():
    try:
        os.unlink( CRON_FILE )
        print( "Deleted cron.d entry." )
    except:
        print( "Unable to delete cron.d entry." )
        


class NodeUpdate:

    def __init__( self, doReboot ):
        if self.CheckProxy():
            os.environ['http_proxy']= self.HTTP_PROXY
            os.environ['HTTP_PROXY']= self.HTTP_PROXY
            
        self.doReboot= doReboot

    

    def CheckProxy( self ):
        Message( "Checking existence of proxy config file..." )
        
        if os.access(PROXY_FILE, os.R_OK) and os.path.isfile(PROXY_FILE):
            self.HTTP_PROXY= string.strip(file(PROXY_FILE,'r').readline())
            Message( "Using proxy %s." % self.HTTP_PROXY )
            return 1
        else:
            Message( "Not using any proxy." )
            return 0


    def InstallKeys( self ):
        Message( "\nRemoving any existing GPG signing keys from the RPM database" )
        os.system( "%s --allmatches -e gpg-pubkey" % RPM_PATH )

        Message( "\nInstalling all GPG signing keys in %s" % RPM_GPG_PATH )
        os.system( "%s --import %s/*" % (RPM_PATH, RPM_GPG_PATH) )


    def ClearRebootFlag( self ):
        os.system( "/bin/rm -rf %s" % REBOOT_FLAG )


    def CheckForUpdates( self ):

        Message( "\nRemoving any existing reboot flags" )
        self.ClearRebootFlag()

        if self.doReboot == 0:
            Message( "\nIgnoring any reboot flags set by RPMs" );

        Message( "\nChecking if yum supports SSL certificate checks" )
        if os.system( "%s --help | grep -q sslcertdir" % YUM_PATH ) == 0:
            Message( "It does, using --sslcertdir option" )
            sslcertdir = "--sslcertdir=" + SSL_CERT_DIR
        else:
            Message( "Unsupported, not using --sslcertdir option" )
            sslcertdir = ""
                    
        yum_options=""
        Message( "\nChecking if yum supports --verbose" )
        if os.system( "%s --help | grep -q verbose" % YUM_PATH ) == 0:
            Message( "It does, using --verbose option" )
            yum_options += " --verbose"
        else:
            Message( "Unsupported, not using --verbose option" )
        
        # a configurable list of packages to try and update independently
        # cautious..
        try:
            crucial_packages = []
            for package in CRUCIAL_PACKAGES_BUILTIN: crucial_packages.append(package)
            try: crucial_packages += file(CRUCIAL_PACKAGES_OPTIONAL_PATH1).read().split()
            except: pass
            try: crucial_packages += file(CRUCIAL_PACKAGES_OPTIONAL_PATH2).read().split()
            except: pass
            for package in crucial_packages:
                Message( "\nUpdating crucial package %s" % package)
                os.system( "%s %s -y update %s" %(YUM_PATH, yum_options, package))
        except:
            pass

        Message( "\nUpdating PlanetLab group" )
        os.system( "%s %s %s -y groupinstall \"PlanetLab\"" %
                   (YUM_PATH, yum_options, sslcertdir) )

        Message( "\nUpdating rest of system" )
        os.system( "%s %s %s -y update" % (YUM_PATH, yum_options, sslcertdir) )

        Message( "\nChecking for extra groups (extensions) to update" )
        if os.access(EXTENSIONS_FILE, os.R_OK) and \
           os.path.isfile(EXTENSIONS_FILE):
            extensions_contents= file(EXTENSIONS_FILE).read()
            extensions_contents= string.strip(extensions_contents)
            if extensions_contents == "":
                Message( "No extra groups found in file." )
            else:
                extensions_contents.strip()
                for extension in extensions_contents.split():
                    group = "extension%s" % extension
                    Message( "\nUpdating %s group" % group )
                    os.system( "%s %s %s -y groupinstall \"%s\"" %
                               (YUM_PATH, yum_options, sslcertdir, group) )
        else:
            Message( "No extensions file found" )
            
        if os.access(REBOOT_FLAG, os.R_OK) and os.path.isfile(REBOOT_FLAG) and self.doReboot:
            Message( "\nAt least one update requested the system be rebooted" )
            self.ClearRebootFlag()
            os.system( "/sbin/shutdown -r now" )

    def RebuildRPMdb( self ):
        Message( "\nRebuilding RPM Database." )
        try: os.system( "rm /var/lib/rpm/__db.*" )
        except Exception, err: print "RebuildRPMdb: %s" % err
        try: os.system( "%s --rebuilddb" % RPM_PATH )
        except Exception, err: print "RebuildRPMdb: %s" % err

    def YumCleanAll ( self ):
        Message ("\nCleaning all yum cache (yum clean all)")
        try:
            os.system( "yum clean all")
        except:
            pass

    def RemoveRPMS( self ):

        Message( "\nLooking for RPMs to be deleted." )
        if os.access(DELETE_RPM_LIST_FILE, os.R_OK) and \
           os.path.isfile(DELETE_RPM_LIST_FILE):
            rpm_list_contents= file(DELETE_RPM_LIST_FILE).read().strip()

            if rpm_list_contents == "":
                Message( "No RPMs listed in file to delete." )
                return

            rpm_list= string.split(rpm_list_contents)
            
            Message( "Deleting RPMs from %s: %s" %(DELETE_RPM_LIST_FILE," ".join(rpm_list)))

            # invoke them separately as otherwise one faulty (e.g. already uninstalled)
            # would prevent the other ones from uninstalling
            for rpm in rpm_list:
                # is it installed
                is_installed = os.system ("%s -q %s"%(RPM_PATH,rpm))==0
                if not is_installed:
                    Message ("Ignoring rpm %s marked to delete, already uninstalled"%rpm)
                    continue
                uninstalled = os.system( "%s -ev %s" % (RPM_PATH, rpm) )==0
                if uninstalled:
                    Message ("Successfully removed RPM %s"%rpm)
                    continue
                else:
                    Error( "Unable to delete RPM %s, continuing. rc=%d" % (rpm,rc ))
            
        else:
            Message( "No RPMs list file found." )



if __name__ == "__main__":

    # if we are invoked with 'start', display the output. 
    # this is useful for running something silently 
    # under cron and as a service (at startup), 
    # so the cron only outputs errors and doesn't
    # generate mail when it works correctly

    displayOutput= 0

    # if we hit an rpm that requests a reboot, do it if this is
    # set to 1. can be turned off by adding noreboot to command line
    # option
    
    doReboot= 1

    if "start" in sys.argv or "display" in sys.argv:
        displayOutput= 1
        Message ("\nTurning on messages")

    if "noreboot" in sys.argv:
        doReboot= 0

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
            if os.system("/bin/kill -0 %s > /dev/null 2>&1" % pid) == 0:
                Message( "It appears we are already running, exiting." )
                sys.exit(1)
                    
    # write out our process id
    pidfile= file( NODEUPDATE_PID_FILE, 'w' )
    pidfile.write( "%d\n" % os.getpid() )
    pidfile.close()

    
    nodeupdate= NodeUpdate(doReboot)
    if not nodeupdate:
        Error( "Unable to initialize." )
    else:
        nodeupdate.RebuildRPMdb()
        nodeupdate.RemoveRPMS()
        nodeupdate.InstallKeys()
        nodeupdate.YumCleanAll()
        nodeupdate.CheckForUpdates()
        Message( "\nUpdate complete." )

    # remove the PID file
    os.unlink( NODEUPDATE_PID_FILE )

