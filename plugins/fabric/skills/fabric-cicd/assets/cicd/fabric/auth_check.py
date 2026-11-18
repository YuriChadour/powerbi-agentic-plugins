"""Non-deploying Fabric authentication and workspace metadata check."""
import argparse
import os
import urllib.request

from azure.identity import ClientSecretCredential


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", action="append", required=True)
    args = parser.parse_args()
    tenant = os.getenv("FABRIC_TENANT_ID") or os.getenv("AZURE_TENANT_ID")
    client = os.getenv("FABRIC_APP_ID") or os.getenv("AZURE_CLIENT_ID")
    secret = os.getenv("FABRIC_APP_SECRET") or os.getenv("AZURE_CLIENT_SECRET")
    if not all((tenant, client, secret)):
        raise SystemExit("protected Fabric identity variables are not available")
    token = ClientSecretCredential(tenant, client, secret).get_token("https://api.fabric.microsoft.com/.default").token
    for workspace in args.workspace:
        request = urllib.request.Request(
            f"https://api.fabric.microsoft.com/v1/workspaces/{workspace}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise SystemExit(f"metadata check failed for workspace {workspace}: HTTP {response.status}")
        print(f"Authenticated metadata check succeeded for workspace {workspace}")


if __name__ == "__main__":
    main()
