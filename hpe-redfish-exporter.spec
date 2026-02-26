%{?!python_module:%define python_module() python-%{**} python3-%{**} python311-%{**}}

Name: hpe-redfish-exporter
Version: 2.3.0
Release: 1%{?dist}
Summary: Prometheus exporter for HPE ClusterStor systems using Redfish API
License: GPL-3.0
URL: https://github.com/paulscherrerinstitute/hpe-redfish-exporter
BuildArch: noarch

BuildRequires:  %{python_module setuptools}
Requires: ${python_module requests}
Requires: ${python_module redfish}
Requires: python3-requests-toolbelt
Requires: python3-requests-unixsocket

%description
A Prometheus exporter for HPE ClusterStor systems that collects metrics via the HPE Redfish REST API. This exporter queries HPE Redfish API endpoints to gather comprehensive system metrics including storage system health, node power states, Lustre filesystem statistics, Linux system metrics, and event history.

%prep
%autosetup

%build
python3 setup.py build

%install
python3 setup.py install --root=%{buildroot} --optimize=1

%files
%{python3_sitelib}/*
%{_bindir}/hpe-redfish-exporter
%{python3_sitelib}/hpe_redfish_exporter-*.dist-info/
%{python3_sitelib}/hpe_redfish_exporter-*.egg-info/

%doc README.md CHANGELOG.md
%license LICENSE

%changelog
* Thu Feb 26 2026 HPE Redfish Exporter Team - 2.3.0-1
- Initial RPM package for HPE Redfish Exporter v2.3.0
- Migrated from Flask to Python http.server for reduced dependencies
- Prometheus exporter for HPE ClusterStor systems
- Collects metrics via HPE Redfish REST API
- Provides /metrics and /health endpoints
- GPL-3.0 licensed open source software
