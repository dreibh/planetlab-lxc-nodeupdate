#!/usr/bin/python2

# Copyright (c) 2003 Intel Corporation
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:

#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.

#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.

#     * Neither the name of the Intel Corporation nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE INTEL OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# EXPORT LAWS: THIS LICENSE ADDS NO RESTRICTIONS TO THE EXPORT LAWS OF
# YOUR JURISDICTION. It is licensee's responsibility to comply with any
# export regulations applicable in licensee's jurisdiction. Under
# CURRENT (May 2000) U.S. export regulations this software is eligible
# for export from the U.S. and can be downloaded by or otherwise
# exported or reexported worldwide EXCEPT to U.S. embargoed destinations
# which include Cuba, Iraq, Libya, North Korea, Iran, Syria, Sudan,
# Afghanistan and any other country to which the U.S. has embargoed
# goods and services.


import sys, os
from random import Random
import string

# not needed now
#PLANETLAB_BIN = "/usr/local/planetlab/bin/"
#sys.path.append(PLANETLAB_BIN)
#import BootServerRequest


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

# file containing list of extra groups to attempt to update,
# if necessary.
EXTRA_GROUPS_FILE= '/etc/planetlab/extra-node-groups'

# file containing a list of rpms that we should attempt to delete
# before we updating everything else. this list is not
# removed with 'yum remove', because that could accidently remove
# dependency rpms that were not intended to be deleted.
DELETE_RPM_LIST_FILE= '/etc/planetlab/delete-rpm-list'


# print out a message only if we are displaying output
def Message(Str):
    if displayOutput:
        print Str


# print out a message only if we are displaying output
def Error(Str):
    print Str


# create an entry in /etc/cron.d so we run periodically.
# we will be run once a day at a 0-59 minute random offset
# into a 0-23 random hour
def UpdateCronFile():
    try:
        
        randomMinute= Random().randrange( 0, 59, 1 );
        randomHour= Random().randrange( 0, 23, 1 );
        
        f = open( CRON_FILE, 'w' );
        f.write( "# %s\n" % (TARGET_DESC) );
        f.write( "MAILTO=%s\n" % (TARGET_USER) );
        f.write( "SHELL=%s\n" % (TARGET_SHELL) );
        f.write( "%s %s * * * %s %s\n\n" %
                 (randomMinute, randomHour, TARGET_USER, TARGET_SCRIPT) );
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
        Message( "Checking existance of proxy config file..." )
        
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
            Message( "Yes, using --sslcertdir option" )
            sslcertdir = "--sslcertdir=" + SSL_CERT_DIR
        else:
            Message( "No, not using --sslcertdir option" )
            sslcertdir = ""
                    
        Message( "\nUpdating PlanetLab group" )
        os.system( "%s %s -y groupupdate \"PlanetLab\"" %
                   (YUM_PATH, sslcertdir) )

        Message( "\nUpdating rest of system" )
        os.system( "%s %s -y update" %
                   (YUM_PATH, sslcertdir) )

        Message( "\nChecking for extra groups to update" )
        if os.access(EXTRA_GROUPS_FILE, os.R_OK) and \
           os.path.isfile(EXTRA_GROUPS_FILE):
            extra_groups_contents= file(EXTRA_GROUPS_FILE).read()
            extra_groups_contents= string.strip(extra_groups_contents)
            if extra_groups_contents == "":
                Message( "No extra groups found in file." )
            else:
                for group in string.split(extra_groups_contents,"\n"):
                    Message( "\nUpdating %s group" % group )
                    os.system( "%s %s -y groupupdate \"%s\"" %
                               (YUM_PATH, sslcertdir, group) )
        else:
            Message( "No extra groups file found" )
            
        if os.access(REBOOT_FLAG, os.R_OK) and os.path.isfile(REBOOT_FLAG) and self.doReboot:
            Message( "\nAt least one update requested the system be rebooted" )
            self.ClearRebootFlag()
            os.system( "/sbin/shutdown -r now" )

            
    def RemoveRPMS( self ):

        Message( "\nLooking for RPMs to be deleted." )
        if os.access(DELETE_RPM_LIST_FILE, os.R_OK) and \
           os.path.isfile(DELETE_RPM_LIST_FILE):
            rpm_list_contents= file(DELETE_RPM_LIST_FILE).read()
            rpm_list_contents= string.strip(rpm_list_contents)

            if rpm_list_contents == "":
                Message( "No RPMs listed in file to delete." )
                return

            rpm_list= string.join(string.split(rpm_list_contents))
            
            Message( "Deleting these RPMs:" )
            Message( rpm_list_contents )
            
            rc= os.system( "%s -ev %s" % (RPM_PATH, rpm_list) )

            if rc != 0:
                Error( "Unable to delete RPMs, continuing. rc=%d" % rc )
            else:
                Message( "RPMs deleted successfully." )
            
        else:
            Message( "No RPMs list file found." )



if __name__ == "__main__":

    # if we are invoked with 'start', display the output. this
    # is usefull for running something under cron and as a service
    # (at startup), so the cron only outputs errors and doesn't
    # generate mail when it works correctly

    displayOutput= 0

    # if we hit an rpm that requests a reboot, do it if this is
    # set to 1. can be turned off by adding noreboot to command line
    # option
    
    doReboot= 1

    if "start" in sys.argv:
        displayOutput= 1

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
        nodeupdate.RemoveRPMS()
        nodeupdate.InstallKeys()
        nodeupdate.CheckForUpdates()
        Message( "\nUpdate complete." )

    # remove the PID file
    os.unlink( NODEUPDATE_PID_FILE )

