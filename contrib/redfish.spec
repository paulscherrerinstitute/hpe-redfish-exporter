%{?!python_module:%define python_module() python-%{**} python3-%{**}}
%define python3_version %(python3 --version | cut -f2 -d' ' | cut -f1,2 -d'.')

Name: python3-redfish
Version: 3.3.4
Release: 1%{?dist}
Summary: Python3 library for interacting with devices that support a Redfish service 
License: BSD-3-Clause
URL: https://github.com/DMTF/python-redfish-library
Source: https://files.pythonhosted.org/packages/df/b9/e0441673427e982c7cc705dfe4ecb4746ecdf70e9c9eb343a33d86789197/redfish-%{version}.tar.gz
BuildArch: noarch

BuildRequires: %{python_module setuptools}
Requires: python3 >= 3.6
Requires: python3-jsonpatch
Requires: python3-jsonpointer
Requires: python3-requests
Requires: python3-requests-toolbelt

%description
The Python Redfish library is the platform on which the Redfish tool was built on. It's main purpose is to simplify the communication to any RESTful API.

%prep
%autosetup -n redfish-%{version}

%build
python3 setup.py build

%install
python3 setup.py install --root=%{buildroot} --optimize=1

%files
%{_libdir}/python%{python3_version}/site-packages/*

%doc README.rst AUTHORS.md
%license LICENSE.md

%changelog
* Thu Feb 26 2026 HPE Redfish Exporter Team - 3.3.4-1
- Initial RPM package for DMTF's Redfish Python library
