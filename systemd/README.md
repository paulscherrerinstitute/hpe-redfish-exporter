# Systemd Service for HPE Redfish Exporter

The service file and sysconfig file should be installed in the appropriate
directories on your system.

A `/etc/hpe-redfish-exporter` directory should also be generated, with a
credentials file placed into it: `../auth`, **make sure** to set the
permissions to `600` to prevent normal users from reading the credentials. Note
that the systemd service uses the `LoadCredential` option, which specially
copies this file into a restricted sandbox where the `hpe_redfish_exporter` is
running.
