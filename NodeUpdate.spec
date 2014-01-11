%define name NodeUpdate
%define version 0.5
%define taglevel 10

%define release %{taglevel}%{?pldistro:.%{pldistro}}%{?date:.%{date}}

Vendor: PlanetLab
Packager: PlanetLab Central <support@planet-lab.org>
Distribution: PlanetLab %{plrelease}
URL: %{SCMURL}

Summary: PlanetLab service to periodically update node RPMS
Name: %{name}
Version: %{version}
Release: %{release}
Requires: python2 >= 2.2, yum >= 2.0.3-3_planetlab
License: GPL
Group: System Environment/Base
Source: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}root
Requires: cronie, logrotate

%description
PlanetLab service to periodically update node RPMS

%prep

%setup

%build


%install
echo "* Installing NodeUpdate node-side files"
install -D -m 755 NodeUpdate.py $RPM_BUILD_ROOT/usr/bin/NodeUpdate.py
install -D -m 644 logrotate/NodeUpdate $RPM_BUILD_ROOT/etc/logrotate.d/NodeUpdate

%clean
[ "$RPM_BUILD_ROOT" != "/" ] && rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%attr(0755,root,root) /usr/bin/NodeUpdate.py*
%attr(0644,root,root) /etc/logrotate.d/NodeUpdate

%post
/usr/bin/NodeUpdate.py updatecron

%preun
if [ "$1" = 0 ]; then
    /usr/bin/NodeUpdate.py removecron
fi

%changelog
* Mon May 06 2013 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - nodeupdate-0.5-10
- bugfix in nodeupdate.RemoveRPMS, NodeUpdate.py bails out if rpms can't be removed

* Fri Jul 01 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - nodeupdate-0.5-9
- support /etc/planetlab/NodeUpdate.packages and /etc/planetlab/crucial-rpm-list
- delete exceptions from delete-rpm-list individually

* Fri Feb 18 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - nodeupdate-0.5-8
- has a builtin list of packages to update individually (NodeManager for now)
- plus an optional set that is read from /etc/planetlab/NodeUpdate.packages

* Wed Jul 14 2010 Daniel Hokka Zakrisson <dhokka@cs.princeton.edu> - nodeupdate-0.5-7
- Use groupinstall to get new group members.

* Fri Jan 29 2010 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - NodeUpdate-0.5-6
- new module layout - no functional change

* Mon Sep 07 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - NodeUpdate-0.5-5
- searches the extensions file /etc/planetlab/extensions rather than the former /etc/planetlab/extra-node-groups

* Tue Apr 07 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - NodeUpdate-0.5-4
- invokes 'yum clean all' before updates
- as it is more reliable, although suboptimal

* Tue Jul 08 2008 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - NodeUpdate-0.5-3
- more verbose : invoke yum with --verbose, and print timestamps

* Fri Aug 10 2007 Faiyaz Ahmed <faiyaza@cs.princeton.edu>
- Rebuild RPM Database nightly to avoid corruption
- Move working directory from /usr/local to /usr/bin

* Tue Nov 16 2004 Mark Huang <mlhuang@cs.princeton.edu>
- cron job now dumps to /var/log/NodeUpdate instead of spewing mail
- cron job now runs once a day instead of once an hour

* Tue Jun 22 2004 Aaron K <alk@cs.princeton.edu>
- added better support for different groups
- added support for deleting rpms

* Mon Apr 12 2004 Aaron K <alk@cs.princeton.edu>
- updated for new build process

* Mon Feb  2 2004 Aaron K <alk@cs.princeton.edu>
- new yum option for ssl cert dir used
- added noreboot option which ignores the reboot flag
  (useful during install and/or boot time)

* Tue Oct 28 2003 Aaron K <Aaron.L.Klingaman@intel.com>
- Initial build.

