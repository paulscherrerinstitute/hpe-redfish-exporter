# Using HPE Redfish REST API Manually

The HPE Redfish REST API can be accessed using `curl` (or similar tools). A
username/password is needed to request a session auth token.

## Examples

### Generate the Auth Token

The username/password for the session auth token are found at the project root
in `.hpe_redfish_auth` in JSON format: `{ "username": <USERNAME>, "password":
<PASSWORD> }`. The `<...>` should be substituted into the following commands.

```console
 $ curl -D - -X POST -H "Content-Type: application/json" -d '{"UserName": "<USERNAME>", "Password": "<PASSWORD>"}' -k https://localhost:8081/redfish/v1/SessionService/Sessions | grep 'x-auth-token'
x-auth-token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJVc2VyTmFtZSI6InJlZGZpc2hleHBvcnRlciIsIlNlc3Npb25JZCI6IlZVS0IyOFZzQlBwclU1SkR5NG9TbU0iLCJNYXBDbGFpbXMiOm51bGx9.goBw0nvw7P9h3RBT0n-U6M431CPYMozixD7Q3G7N0Wk
```

The value of `x-auth-token` should be stored in an environment variable called
`$HPE_RF_AUTH`, which all query commands use.

### Using the HPE Redfish Exporter Package

With the new package structure, you can also use the exporter programmatically:

```python
from hpe_redfish_exporter import HPERedfishExporter, Config

# Create configuration
config = Config(
    redfish_host="https://localhost:8081",
    exporter_addr="127.0.0.1", 
    exporter_port=9223,
    auth_file=".hpe_redfish_auth"
)

# Load credentials
if config.load_credentials():
    # Create and run exporter
    exporter = HPERedfishExporter(config)
    exporter.run()
```

### CLI Usage

The package provides a convenient CLI:

```console
# Show help
hpe-redfish-exporter --help

# Show version
hpe-redfish-exporter --version

# Run with custom configuration
hpe-redfish-exporter \
  --redfish-host "https://your-clusterstor:8081" \
  --listen-addr "0.0.0.0" \
  --listen-port 9223 \
  --auth-file "/path/to/auth.json"
```

### Get StorageSystems object

```console
$ curl -Lk -H "X-Auth-Token: $HPE_RF_AUTH" https://localhost:8081/redfish/v1/StorageSystems/
{
	"@odata.context": "StorageSystemCollection.StorageSystemCollection",
	"@odata.id": "/redfish/v1/StorageSystems",
	"@odata.type": "StorageSystemCollection.v1_0_0.StorageSystemCollection",
	"Description": "Collection of references to storage based ComputerSystem resources.",
	"Members": [
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R1C1-35U-A"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R1C1-35U-B"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R1C1-33U-A"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R1C1-33U-B"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R1C1-27U-A"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R1C1-27U-B"
		},
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R1C1-25U-A"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R1C1-25U-B"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R1C1-31U-A"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R1C1-31U-B"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R1C1-29U-A"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R1C1-29U-B"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R2C2-37U-A"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R2C2-37U-B"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R2C2-35U-A"
		},
		{
			"@odata.id": "/redfish/v1/StorageSystems/psistorn:Node-R2C2-35U-B"
		}
	],
	"Members@odata.count": 16,
	"Name": "psistorn",
	"Oem": {
		"Cluster Mode": "Deployed",
		"Cluster Name": "psistorn",
		"Data Network Type": "Slingshot",
		"Filesystem Name": "psistor",
		"Filesystem Type": "Lustre",
		"Full Software Release": "7.2-021.70",
		"Full System Update": "021.70",
		"Hardware Platform": "CS-E1000",
		"OEM System Serial Number": "CSSX0VS08D",
		"Possible Previous SSN": "N/A",
		"Process Stage Id": "CustomerWizardComplete",
		"Software Release": "7.2",
		"System Identifier": "N/A",
		"System Serial Number": "5UF231JLR0",
		"UUID": "d6b75681-be0d-11f0-8372-b42e99bfba87"
	}
}
```

