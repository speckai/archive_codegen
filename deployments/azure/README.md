# API Deployment

`tofu apply`

## In Azure,

Go to the deployment center for the app service, and set it to github.

When making a PAT for GitHub, select `write:packages` which automatically gives you `repo` permissions.

## Certificates

[Documentation](https://learn.microsoft.com/en-us/azure/app-service/configure-ssl-certificate?tabs=apex%2CRBAC#create-a-free-managed-certificate-preview)

Create a CAA certificate for the domain:

```
0 issue "digicert.com"
```

This allows us to use api.speck.sh and sites.speck.sh
