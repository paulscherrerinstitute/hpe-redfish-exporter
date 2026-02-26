# Extras for the HPE Redfish Exporter for Prometheus Tool

## python-redfish RPM spec file

We maintain a RPM spec file to package the
[python-redfish](https://github.com/DMTF/python-redfish-library) project, on
which the HPE Redfish Exporter depends. This makes it easier to distribute the
package across systems that don't have permissions to use `pip` or Python
environments.

The RPM spec is excluded from this projects licensing, instead reverting to the
upstream projects BSD-3-clause license. The spec file can be used, modifyed,
and distributed per the license terms.

### Build

```bash
# ensure that you have rpm tools installed and have configured the rpmbuild
# directories correctly

# get the source and place in the rpmbuild hierarchy
...

# from this directory, build the RPM
rpmbuild -bb redfish.spec
```
