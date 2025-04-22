import asyncio
import configparser
from ms_graph_toolkit import MSGraphClient 
import iutils
import maria_db
from datetime import datetime

'''
# Import Azure Key Vault libraries
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Function to retrieve secrets from Azure Key Vault
def get_secret(secret_name):
    key_vault_name = "your-key-vault-name"  # Replace with your Key Vault name
    KVUri = f"https://{key_vault_name}.vault.azure.net"
    
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=KVUri, credential=credential)
    
    retrieved_secret = client.get_secret(secret_name)
    return retrieved_secret.value

# Retrieve secrets
client_id = get_secret("client-id")         # Replace with your secret names
client_secret = get_secret("client-secret")
tenant_id = get_secret("tenant-id")


'''

def load_config():
    """
    Load configuration from config.ini file.
    """
    config = configparser.ConfigParser()
    config.read('config.ini')

    ms_graph_config = {
        "tenant_id": config["MSGraph"]["tenant_id"],
        "client_id": config["MSGraph"]["client_id"],
        "client_secret": config["MSGraph"]["client_secret"]

    }

    settings_config = {
        "baseline": config["Settings"]["baseline"],
        "start_date": config["Settings"]["start_date"],
        "end_date": config["Settings"]["end_date"],
        "email": None, #config["Settings"].get("email", None),
        "app_display_name": config["Settings"]["app_display_name"],
        "device_name": config["Settings"].get("device_name", None),
        "ip_range": (config["Settings"]["ip_range_start"], config["Settings"]["ip_range_end"]),
        "delta_link": config["Settings"].get("delta_link", None)
    }

    return ms_graph_config, settings_config

def save_single_config(section, key, value, config_file='config.ini'):
    """
    Save or update a single configuration element in the config.ini file.

    :param section: The section where the key-value pair should be added or updated (e.g., "MSGraph" or "Settings").
    :param key: The key to be added or updated (e.g., "client_id", "baseline").
    :param value: The value corresponding to the key.
    :param config_file: Path to the config file (default: config.ini).
    """
    config = configparser.ConfigParser()

    # Read existing configuration
    config.read(config_file)

    # Ensure the section exists
    if not config.has_section(section):
        config.add_section(section)

    # Add or update the key-value pair
    config.set(section, key, value)

    # Write the updated configuration back to the file
    with open(config_file, 'w') as configfile:
        config.write(configfile)
    
    print(f"Configuration updated: [{section}] {key} = {value}")

async def main():


    company_name = 'Shared Services Canada'
    ip_range = iutils.get_company_ranges(company_name)
    if ip_range:
        iutils.save_to_file(ip_range, 'data/ip_ranges')

    # Load configuration
    ms_graph_config, settings_config = load_config()

    tenant_id = ms_graph_config["tenant_id"]
    client_id = ms_graph_config["client_id"]
    client_secret = ms_graph_config["client_secret"]


    start_date = settings_config["start_date"] + 'T00:00:00Z'
    end_date = settings_config["end_date"] + 'T23:59:59Z'
    email = None #settings_config["email"]  # You can replace None with a specific email if needed
    app_display_name = settings_config["app_display_name"]
    device_name = None, #settings_config["device_name"]
    #ip_range = settings_config["ip_range"]
    top = None
    max_retries = 25
    baseline = settings_config["start_date"]
    delta_link = settings_config["delta_link"]
    # Dictionary of ASNs associated with Shared Services Canada (SSC)
    

    # Initialize the MSGraphClient with the loaded configuration
    graph_client = MSGraphClient(tenant_id, client_id, client_secret, baseline)
    
    # Connect to the database and create tables if required
    manager = maria_db.db_connection(database="velo_db_prod")




    if manager:
        '''
        #Query copilot logs
        logins =  graph_client.query_logs(start_date=start_date, end_date=end_date, category=None, app_displayName = "Office 365 SharePoint Online", ip_range=ip_range, top=top, max_retries=max_retries)
        if logins:
            iutils.save_to_file(logins, 'data/logins')
            #manager.create_and_insert_from_graph_api('copilot_logs', logins, datetime.now())
        
        # Delta users
        
        delta =graph_client.delta_users(top=None, max_retries=max_retries,delta_link=delta_link)
        if delta:
            manager.process_data_list('delta', delta['users'], baseline)
            iutils.save_to_file(delta['users'], 'data/delta')
            save_single_config("Settings", "delta_link", delta['delta_link'])
        
        '''
        # Query users
        users =graph_client.query_users(email=email, start_date=start_date, end_date=end_date, top=None, max_retries=max_retries, accountType='Member')
        if users:
            manager.process_data_list('users', users, baseline)
            iutils.save_to_file(users, 'data/users')
        
        
        # Query sign-ins
        #signins =graph_client.query_sign_ins(email, start_date=start_date, end_date=end_date, app_display_name=app_display_name, ip_range=ip_range, top=top, max_retries=max_retries)
        #if signins:
        #   manager.process_data_list('signins', signins, baseline)
        #   iutils.save_to_file(signins, 'data/signins')

        
        # Query devices
        devices =graph_client.query_devices(None, None, None, device_name=None, top=top)
        if devices:
           manager.process_data_list('devices', devices, baseline)
           iutils.save_to_file(devices, 'data/devices')

        '''
        # Build Azure AD tree
        #single record to test build_aad_tree: group_id = '0000c6bc-4445-4acd-bba9-0dba4e670579'
        az_add = graph_client.build_aad_tree()
        if az_add:
            manager.process_data_list('az_add', az_add, baseline)
            iutils.save_to_file(az_add, 'data/az_add')

        # Build Azure AD members tree
        az_members = graph_client.build_aad_members(az_add)
        #az_members = graph_client.fetch_group_members(group_id='05cf67f8-f45d-4a10-97cd-6602bcbbfde9', group_name='Data Analytics and Reporting | Analyse et de rapport sur les données')

        if az_members:
            manager.process_data_list('az_members', az_members, baseline)
            iutils.save_to_file(az_members, 'data/az_member')
        '''
        


        # Close the database connection
        manager.close()

if __name__ == "__main__":
    asyncio.run(main())
