import asyncio
import msal
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry, ProtocolError
from concurrent.futures import ThreadPoolExecutor  # Import ThreadPoolExecutor for parallel execution
from django.shortcuts import render
import iutils
import time
import ipaddress
import concurrent.futures
import jwt
from .api_client import ApiClient


class MSGraphClient(ApiClient):
    def __init__(self, tenant_id, client_id, client_secret, baseline="1.0"):
        super().__init__(tenant_id, client_id, client_secret)
        self.baseline = baseline
        self.token = None
        self.token_expiration = 0  # Timestamp of token expiration in seconds

        self.session = requests.Session()
        retries = Retry(total=5, 
                        backoff_factor=1, 
                        status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        # Acquire the first token when initializing
        self.access_token = self.get_access_token()


    def query_sign_ins(self, email=None, start_date=None, end_date=None, app_display_name="Windows Sign In", ip_range=None, top=None, max_retries=5):
        """
        Query the sign-ins from Microsoft Graph API within the specified date range, filtering by appDisplayName.
        Handles OData paging to retrieve all results if necessary and retries on rate limiting.
        
        :param start_date: The start date for the query (ISO 8601 format).
        :param end_date: The end date for the query (ISO 8601 format).
        :param app_display_name: The display name of the app to filter by. Default is "Windows Sign In".
        :param ip_range: A tuple containing the start and end of the IP range to check.
        :param top: Optional. The maximum number of results to return per page.
        :param max_retries: Optional. The maximum number of retries if a rate limit is hit.
        
        :return: A list containing all the results of the query that match the IP range, with goc_building property.
        """
        params = {}

        # Build the $filter parameter based on email (userPrincipalName), appDisplayName, and date range
        filter_clauses = []

        if email:
            filter_clauses.append(f"userPrincipalName eq '{email}'")
        
        if app_display_name:
            filter_clauses.append(f"(appDisplayName eq '{app_display_name}' or appDisplayName eq 'Microsoft Teams')")
        
        if start_date and end_date:
            filter_clauses.append(f"status/errorCode eq 0 and (appDisplayName eq 'Windows Sign In' or appDisplayName eq 'Microsoft Teams') and (createdDateTime ge {start_date} and createdDateTime le {end_date})")

        # Combine filter clauses
        if filter_clauses:
            params["$filter"] = " and ".join(filter_clauses)
             # Select only the specific properties we want to retrieve
        
        params["$select"] = 'id, createdDateTime, userPrincipalName, userDisplayName, appDisplayName, userId, ipAddress, deviceDetail, location, clientAppUsed, deviceDetail'

        # Order by createdDateTime in descending order to get the most recent record first
        params["$orderby"] = "createdDateTime desc"

        # Limit to only the top result (the most recent one)
        if top:
            params["$top"] = top    

        base_url = "https://graph.microsoft.com/v1.0/auditLogs/signIns"

        # Call the Microsoft Graph API
        sign_in_data = self.query_msgraph(base_url, params=params, max_retries=max_retries)

        # Initialize an empty list to store results with the goc_building property
        results_with_goc_building = []

        # Check if sign_in_data is a list or dictionary and iterate accordingly
        records = sign_in_data.get('value', []) if isinstance(sign_in_data, dict) else sign_in_data

        # Process each sign-in record
        if records and ip_range:
            
            for record in records:
                ip_address = record.get("ipAddress")
                is_in_range = iutils.is_ip_in_range(ip_address, ip_range)

                record['goc_building'] = is_in_range
                #record['goc_building_text'] = iutils.get_building_by_ip(ip_address)
                record['baseline'] = self.baseline
                
                
                # Append the modified record to the results list
                results_with_goc_building.append(record)

        return results_with_goc_building

    def query_logs(self, start_date=None, end_date=None, category=None, app_displayName = None,  ip_range=None, top=None, max_retries=5):
        """
        Query the sign-ins from Microsoft Graph API within the specified date range, filtering by appDisplayName.
        Handles OData paging to retrieve all results if necessary and retries on rate limiting.
        
        :param start_date: The start date for the query (ISO 8601 format).
        :param end_date: The end date for the query (ISO 8601 format).
        :param app_display_name: The display name of the app to filter by. Default is "Windows Sign In".
        :param ip_range: A tuple containing the start and end of the IP range to check.
        :param top: Optional. The maximum number of results to return per page.
        :param max_retries: Optional. The maximum number of retries if a rate limit is hit.
        
        :return: A list containing all the results of the query that match the IP range, with goc_building property.
        """
        params = {}

        # Build the $filter parameter based on email (userPrincipalName), appDisplayName, and date range
        filter_clauses = []

        
        if category:
            filter_clauses.append(f"category eq '{category}'")        

        if app_displayName:
            filter_clauses.append(f"initiatedBy/app/displayName eq '{app_displayName}'")
            #filter_clauses.append(f"initiatedBy_app_displayName eq '{app_displayName}'")  
            
        #if start_date and end_date:
        #    filter_clauses.append(f"activityDateTime ge {start_date}")
            #filter_clauses.append(f"activityDateTime ge {start_date} and activityDateTime le {end_date}")

        # Combine filter clauses
        if filter_clauses:
            params["$filter"] = " and ".join(filter_clauses)
             # Select only the specific properties we want to retrieve
        
        #params["$select"] = 'id, createdDateTime, userPrincipalName, userDisplayName, userId, ipAddress, deviceDetail, location'


        # Order by createdDateTime in descending order to get the most recent record first
        #params["$orderby"] = "activityDateTime desc"

        # Limit to only the top result (the most recent one)
        if top:
            params["$top"] = top    

        base_url = "https://graph.microsoft.com/v1.0/auditLogs/directoryAudits"

        # Call the Microsoft Graph API
        log_data = self.query_msgraph(base_url, params=params, max_retries=max_retries)


        # Check if sign_in_data is a list or dictionary and iterate accordingly
        if log_data:
            records = log_data.get('value', []) if isinstance(log_data, dict) else log_data
            return records
        
        return
    
    def get_user_presence(self, email=None, top=None, max_retries=5):
        """
        Get the presence status of a user from Microsoft Graph API.
        """
        base_url = f"https://graph.microsoft.com/v1.0/users/{email}/presence"
        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json"
        }

        try:
            response = self.query_msgraph(base_url, headers=headers, max_retries=max_retries)
            if response.get('status_code') == 200:
                return response
            else:
                raise Exception(f"Error fetching presence: {response.get('status_code')} - {response.get('error', '')}")
        except Exception as e:
            print(f"Failed to fetch presence for {email}: {e}")
            return None


    def query_users(self, email=None, start_date=None, end_date=None, page_size=None, top=None, max_retries=5, orbit=False, presence=False, accountType=None):
        """
        Query all users from Microsoft Graph API.
        Handles OData paging to retrieve all results if necessary and retries on rate limiting.
        """
        params = {}

        # Build the $filter parameter based on email (userPrincipalName), start_date, and end_date
        filter_clauses = []

        if email:
            filter_clauses.append(f"userPrincipalName eq '{email}'")

        if accountType:
            filter_clauses.append(f"userType eq '{accountType}'")

        # Combine filter clauses
        if filter_clauses:
            params["$filter"] = " and ".join(filter_clauses)

        params["$select"] = 'id, businessPhones, city, createdDateTime, companyName, country, department, displayName, givenName, jobTitle, onPremisesSamAccountName, onPremisesUserPrincipalName, postalCode, state, streetAddress, surname, usageLocation, userPrincipalName, userType, onPremisesExtensionAttributes'

        if top:
            params["$top"] = top

        base_url = "https://graph.microsoft.com/beta/users"

        # Await the query_msgraph method
        user_data =  self.query_msgraph(base_url, params=params, max_retries=max_retries)

        # Initialize an empty list to store results with baseline property
        results_with_baseline = []

        # Check if user_data is a list or dictionary and iterate accordingly
        records = user_data.get('value', []) if isinstance(user_data, dict) else user_data

        # Process each user record
        for record in records:
            # Extract sign-in activity details
            #sign_in_activity = record.get("signInActivity", {})
            #record["lastSignInDateTime"] = sign_in_activity.get("lastSignInDateTime")

            # Append additional details
            #record['baseline'] = self.baseline
            if isinstance(record, list):
                # If record is a list, iterate over the list and process each item
                for item in record:
                    if isinstance(item, dict):
                        if orbit:
                            item['orbit'] = self.query_user_people(item['userPrincipalName'], page_size=None, top=5, max_retries=max_retries)
                        if presence:
                            item['presence'] = self.get_user_presence(item['userPrincipalName'], top=top, max_retries=max_retries)
                        results_with_baseline.append(item)
            else:
                # If record is a dictionary
                if orbit:
                    record['orbit'] = self.query_user_people(record['userPrincipalName'], page_size=None, top=5, max_retries=max_retries)
                if presence:
                    record['presence'] = self.get_user_presence(record['userPrincipalName'], top=top, max_retries=max_retries)
                results_with_baseline.append(record)

            results_with_baseline.append(record)
            print(results_with_baseline)
        return results_with_baseline


    def get_users(self):
        print("Fetching users data...")

        # Step 1: Get access token for MS Graph
        #access_token = get_access_token(client_id, client_secret, tenant_id)

        # Initialize params as an empty dictionary before adding the filter or select parameters
        params = {}
        filter_clauses = []

        filter_clauses.append(f"accountEnabled eq true")

        # Combine filter clauses
        if filter_clauses:
            params["$filter"] = " and ".join(filter_clauses)
                # Select only the specific properties we want to retrieve

        params["$select"] = 'id, lastSignInDateTime, businessPhones, city, createdDateTime, companyName, country, department, displayName, givenName, jobTitle, onPremisesSamAccountName, onPremisesUserPrincipalName, postalCode, state, streetAddress, surname, usageLocation, userPrincipalName, userType, onPremisesExtensionAttributes'

        #user_data = fetch_data_with_pagination(users_endpoint, access_token, params)
        base_url = "https://graph.microsoft.com/beta/users"

        user_data= self.query_msgraph(base_url, params, max_retries=5)
        # Check if the data returned is a list or dictionary
        if isinstance(user_data, dict):
            records = user_data.get('value', [])
        elif isinstance(user_data, list):
            records = user_data
        else:
            print(f"Unexpected data format: {type(user_data)}")
            return []

        results = []
        if records:
            for record in records:
                results.append(record)
        return results
        
    def query_devices(self, start_date, end_date, email=None, device_name=None, top=None, max_retries=5):
        """
        Query all managed devices from the Intune endpoint in Microsoft Graph API.
        Handles OData paging to retrieve all results if necessary and retries on rate limiting.
        
        :param start_date: The start date for filtering devices.
        :param end_date: The end date for filtering devices.
        :param email: Optional. The userPrincipalName to filter by.
        :param device_name: Optional. The name of the device to filter by.
        :param top: Optional. The maximum number of results to return per page.
        :param max_retries: Optional. The maximum number of retries if a rate limit is hit.
        
        :return: A list containing all the managed devices, each appended with the baseline property from the class.
        """
        params = {}

        # Build the $filter parameter based on email, device_name, start_date, and end_date
        filter_clauses = []

        if email:
            filter_clauses.append(f"userPrincipalName eq '{email}'")
        
        if device_name:
            filter_clauses.append(f"deviceName eq '{device_name}'")
        
        if start_date and end_date:
            filter_clauses.append(f"lastSyncDateTime ge {start_date} and lastSyncDateTime le {end_date}")

        # Combine filter clauses
        if filter_clauses:
            params["$filter"] = " and ".join(filter_clauses)

        if top:
            params["$top"] = top
            
        # Order by lastSyncDateTime in descending order to get the most recent record first
        #params["$orderby"] = "lastSyncDateTime desc"

        # Limit to only the top result (the most recent one)
        if top:
            params["$top"] = top

        base_url = "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices"

        # Call the Microsoft Graph API
        device_data = self.query_msgraph(base_url, params=params, max_retries=max_retries)
        '''
        # Initialize an empty list to store results with baseline property
        results_with_baseline = []
        
        # Check if device_data is a list or dictionary and iterate accordingly
        records = device_data.get('value', []) if isinstance(device_data, dict) else device_data

        # Process each device record and append baseline from the class member
        for record in records:
            record['baseline'] = self.baseline
            results_with_baseline.append(record)
        '''
        return device_data
    

    def query_devices_extended(
        self,
        start_date,
        end_date,
        email=None,
        device_name=None,
        top=None,
        group_by_properties=None,
        max_retries=5
    ):
        """
        Query all managed devices from the Intune endpoint in Microsoft Graph API.
        Handles OData paging to retrieve all results if necessary and retries on rate limiting.
        
        Additionally, if a list of properties is provided via the group_by_properties parameter,
        the results are grouped (nested) by these properties. Each group will include a count and 
        percentage relative to the parent grouping.
        
        :param start_date: The start date for filtering devices.
        :param end_date: The end date for filtering devices.
        :param email: Optional. The userPrincipalName to filter by.
        :param device_name: Optional. The name of the device to filter by.
        :param top: Optional. The maximum number of results to return per page.
        :param group_by_properties: Optional. A list of 1 to 10 property names (from the API) to group by,
                                    or a comma-separated string.
        :param max_retries: Optional. The maximum number of retries if a rate limit is hit.
        
        :return: If group_by_properties is provided, a nested list of dictionaries representing the groups,
                each with keys "group_by" (the property name), "value" (the property's value), "count", 
                "percentage", and "sub_groups". Otherwise, the raw device data from the API.
        """
        params = {}

        # Build the $filter parameter based on email, device_name, start_date, and end_date
        filter_clauses = []
        if email:
            filter_clauses.append(f"userPrincipalName eq '{email}'")
        if device_name:
            filter_clauses.append(f"deviceName eq '{device_name}'")
        if start_date and end_date:
            filter_clauses.append(f"lastSyncDateTime ge {start_date} and lastSyncDateTime le {end_date}")

        if filter_clauses:
            params["$filter"] = " and ".join(filter_clauses)

        if group_by_properties:
            params["$select"] = group_by_properties

        # Order by lastSyncDateTime in descending order to get the most recent record first
        #params["$orderby"] = "lastSyncDateTime desc"

        # Limit to only the top result (if specified)
        if top:
            params["$top"] = top

        base_url = "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices"
        device_data = self.query_msgraph(base_url, params=params, max_retries=max_retries)

        # Extract device records from the response.
        records = device_data.get("value", []) if isinstance(device_data, dict) else device_data

        # If group_by_properties is provided as a string, automatically split it by commas if needed.
        if group_by_properties:
            if isinstance(group_by_properties, str):
                if ',' in group_by_properties:
                    group_by_properties = [prop.strip() for prop in group_by_properties.split(',')]
                else:
                    group_by_properties = [group_by_properties]

        def group_records(records, group_by_properties):
            grouped_data = []

            for record in records:
                # Check if the record is a list; if it is, loop through its elements
                if isinstance(record, list):
                    for sub_record in record:
                        if isinstance(sub_record, dict):
                            # Process each sub_record as a dictionary
                            group_data = process_record(sub_record, group_by_properties)
                            grouped_data.append(group_data)
                elif isinstance(record, dict):
                    # Process the record if it's a dictionary
                    group_data = process_record(record, group_by_properties)
                    grouped_data.append(group_data)

            return grouped_data

        def process_record(record, group_by_properties):
            group_data = {}
            
            # Ensure group_by_properties is treated as a list
            if isinstance(group_by_properties, str):
                # If it's a string, split it by commas
                group_by_properties = [key.strip() for key in group_by_properties.split(",")]
            
            # Process each key in the group_by_properties list
            for key in group_by_properties:
                current_key = key.strip()
                key_val = record.get(current_key, "Unknown")  # Access the key if it's a dict
                group_data[current_key] = key_val

            return group_data


        # If grouping properties were provided, limit them to 10 levels and return the grouped view.
        if group_by_properties:
            group_by_properties = group_by_properties[:10]
            grouped_view = group_records(records, group_by_properties)
            return grouped_view
        else:
            return device_data


    def fetch_group_members(self, group_id, group_name):
        """
        Fetches members of a specific Azure AD group from Microsoft Graph API.
        
        :param group_id: The ID of the group to fetch members for.
        :param group_name: The name of the group.
        :return: A tuple containing the group name and a dictionary with group members and appended baseline.
        """
        params = {}

        # Build the $filter parameter based on email, device_name, start_date, and end_date
        filter_clauses = []
        
        #filter_clauses.append(f"@odata.type eq '#microsoft.graph.user'")
        params["$select"] ='id,userPrincipalName'

        if filter_clauses:
            params["$filter"] = " and ".join(filter_clauses)
 
        results_with_baseline = []
        #members_data = {'id': group_id, 'members': []}
        members = self.query_msgraph(f'https://graph.microsoft.com/v1.0/groups/{group_id}/members', params=params)
        #records = members.get('value', []) if isinstance(members, dict) else members

        if members:
        # Process each user record and append baseline from the class member
            for record in members:
                record['baseline'] = self.baseline
                record['group_id'] = group_id
                record['group_name'] = group_name
                results_with_baseline.append(record)
            return results_with_baseline
        return members
 
    def build_aad_tree(self, group_id=None, group_name=None):

        params = {}

        # Build the $filter parameter based on email, device_name, start_date, and end_date
        filter_clauses = []

        if group_id:
            filter_clauses.append(f"id eq '{group_id}'")

        if group_name:
            filter_clauses.append(f"display_name eq '{group_name}'")
         # Combine filter clauses
 
        params["$select"] ='id,createdDateTime,description,displayName,mailNickname,renewedDateTime,securityEnabled,securityIdentifier,visibility'
 
        if filter_clauses:
            params["$filter"] = " and ".join(filter_clauses)



        # Call the Microsoft Graph API
        device_data = self.query_msgraph('https://graph.microsoft.com/v1.0/groups', params=params)


        # Get the list of group records
        #records = groups_response.get('value', []) if isinstance(groups_response, dict) else groups_response


        # Return the full groups response if no filter is applied
        return device_data


    def build_aad_members(self, groups=None):
        import concurrent.futures
        from concurrent.futures import ThreadPoolExecutor

        group_data = []

        if groups:
            # Use ThreadPoolExecutor to fetch members in parallel
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_group = {
                    executor.submit(
                        self.fetch_group_members, group['id'], group['displayName']
                    ): group
                    for group in groups if isinstance(group, dict)
                }

                for future in concurrent.futures.as_completed(future_to_group):
                    group = future_to_group[future]
                    try:
                        # Fetch the members for each group
                        result = future.result()
                        group_data.extend(result)
                        # Only extend group_data with the result from the API call
                        #if isinstance(result, dict) in result:
                        #    group_data.extend(result)  # If result is dict, extend with 'value'
                        #elif isinstance(result, list):
                        #    group_data.extend(result)  # If result is a list, extend directly

                    except concurrent.futures.TimeoutError:
                        print(f"Timeout fetching members for group {group['displayName']}")
                    except Exception as exc:
                        print(f"Error fetching members for group {group['displayName']}: {exc}")

            # Return only the group data collected from API calls
            return group_data
        
    def query_user_people(self, email,page_size=None, top=5, max_retries=5):
        """
        Query relevant people for a specific user from Microsoft Graph People API.
        Handles OData paging to retrieve all results if necessary and retries on rate limiting.

        :param email: The userPrincipalName (email) of the targeted user.
        :param top: Optional. The maximum number of results to return in total.
        :param max_retries: Optional. The maximum number of retries if a rate limit is hit.
        
        :return: A list of relevant people, each appended with the baseline property from the class.
        """
        params = {}
        params["$select"] = 'scoredEmailAddresses'

        # Limit to only the top results if specified
        if top:
            params["$top"] = top    

        # API endpoint to get people related to a user
        base_url = f"https://graph.microsoft.com/v1.0/users/{email}/people"
        members = self.query_msgraph(base_url, params=params, page_size=page_size, top=top)

        return members

