%define name NodeUpdate
%define version 0.2
%define release 3

Summary: PlanetLab service to periodically update node RPMS
Name: %{name}
Version: %{version}
Release: %{release}
Requires: python2 >= 2.2, yum >= 2.0.3-3_planetlab
Copyright: GPL
URL: http://www.planet-lab.org
Group: System Environment/Base
Source: %{name}-%{version}.tar.gz
BuildRoot: /tmp/%{name}-%{version}-root

%description
PlanetLab service to periodically update node RPMS

%prep

%setup

%build


%install
mkdir -p $RPM_BUILD_ROOT/usr/local/planetlab/bin
cp NodeUpdate.py $RPM_BUILD_ROOT/usr/local/planetlab/bin/

%clean

%files
%defattr(-,root,root)
%attr(0755,root,root) /usr/local/planetlab/bin/NodeUpdate.py

%pre

%post
if [ "$1" = 1 ]; then
	/usr/local/planetlab/bin/NodeUpdate.py updatecron
fi


%preun
if [ "$1" = 0 ]; then
	/usr/local/planetlab/bin/NodeUpdate.py removecron
fi


%postun


%changelog
* Mon Apr 12 2004 Aaron K <alk@cs.princeton.edu>
- updated for new build process

* Mon Feb  2 2004 Aaron K <alk@cs.princeton.edu>
- new yum option for ssl cert dir used
- added noreboot option which ignores the reboot flag
  (useful during install and/or boot time)

* Tue Oct 28 2003 Aaron K <Aaron.L.Klingaman@intel.com>
- Initial build.

