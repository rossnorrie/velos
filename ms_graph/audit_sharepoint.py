import asyncio
from msgraph import GraphServiceClient

class SharePointUsageFetcher:
    def __init__(self, client_id, client_secret, tenant_id):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.graph_client = None

    async def initialize_graph_client(self):
        """Initializes the GraphServiceClient using MSAL authentication."""
        from msal import ConfidentialClientApplication

        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        app = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=authority
        )

        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        
        if "access_token" in result:
            self.graph_client = GraphServiceClient(
                auth=lambda: result["access_token"]
            )
        else:
            raise Exception("Failed to acquire token: " + str(result))

    async def get_sharepoint_usage_details(self, period):
        """Fetches SharePoint site usage details for the specified period."""
        if not self.graph_client:
            raise Exception("Graph client is not initialized. Call initialize_graph_client first.")

        try:
            response = await self.graph_client.reports.get_share_point_site_usage_detail_with_period(period).get()
            return response
        except Exception as e:
            raise Exception(f"Error fetching SharePoint usage details: {e}")

async def main():
    tenant_id = '42fd9015-de4d-4223-a368-baeacab48927'
    client_id = '2bc1c9b9-d0ad-4ff1-ac90-f5f54f942efb'
    client_secret = 'o5B8Q~XnkYM_BFpZ3anY~5lzrSiVqqGW3P_60br1'
    period = "D30"  # Example: "D30" for the last 30 days

    fetcher = SharePointUsageFetcher(client_id, client_secret, tenant_id)

    await fetcher.initialize_graph_client()
    usage_details = await fetcher.get_sharepoint_usage_details(period)

    print("SharePoint Usage Details:")
    print(usage_details)

if __name__ == "__main__":
    asyncio.run(main())
