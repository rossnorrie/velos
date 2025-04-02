import ipaddress
import json
import pytz
from datetime import datetime
import pandas as pd
import csv
import io
import requests
from bs4 import BeautifulSoup


def get_asns_for_company(company_name_orig):
    """
    Fetches ASNs assigned to a company using Hurricane Electric BGP Toolkit.
    
    :param company_name: The name of the company (e.g., 'Google', 'Amazon').
    :return: A list of dictionaries with ASN and company name or None if not found.
    """
    url = f'https://bgp.he.net/search?search[search]={company_name_orig}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        
        # Parse the HTML using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all ASN entries in the table (typically in 'a' tags within table rows)
        asns = []
        for row in soup.select('table tbody tr'):
            asn_link = row.find('a')
            if asn_link and asn_link.get('href', '').startswith('/AS'):
                asn = asn_link.text.strip()  # Extract the ASN number
                company_name = row.find_all('td')[2].text.strip()  # Company name in 3rd <td>
                if company_name_orig == company_name:
                    asns.append({'asn': asn, 'company_name': company_name})
        
        return asns if asns else None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching ASNs for {company_name}: {e}")
        return None


# Function to get IP ranges for a given ASN using RIPEstat API
def get_ip_ranges_for_asn(asn):
    """
    Fetches the IP ranges assigned to a specific ASN using the RIPEstat API.
    
    :param asn: The ASN number (e.g., 'AS13920').
    :return: A list of IP ranges.
    """
    url = f'https://stat.ripe.net/data/announced-prefixes/data.json?resource={asn}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        
        data = response.json()
        if 'data' in data and 'prefixes' in data['data']:
            # Extracting both IPv4 and IPv6 ranges
            ip_ranges = [prefix['prefix'] for prefix in data['data']['prefixes']]
            return ip_ranges
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching IP ranges for ASN {asn}: {e}")
        return None
    
# Function to get IP ranges for a given ASN
def get_ip_ranges_for_asn_old(asn):
    """
    Fetches the IP ranges assigned to a specific ASN using the BGPView API.
    
    :param asn: The ASN number (e.g., 'AS13920').
    :return: A list of IP ranges.
    """
    url = f'https://api.bgpview.io/asn/{asn}/prefixes'
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        
        data = response.json()
        if 'data' in data and 'ipv4_prefixes' in data['data']:
            # Extracting only IPv4 ranges
            ipv4_ranges = [prefix['prefix'] for prefix in data['data']['ipv4_prefixes']]
            return ipv4_ranges
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching IP ranges for ASN {asn}: {e}")
        return None

# Function to check if an IP address is in a range defined by CIDR
def cidr_to_ip_range(cidr):
    """
    Convert a CIDR notation string into a tuple (range_start, range_end) with IP strings.
    
    :param cidr: The CIDR notation string (e.g., '203.104.80.0/20').
    :return: A tuple of (start_ip, end_ip) as strings.
    """
    network = ipaddress.ip_network(cidr, strict=False)
    return str(network[0]), str(network[-1])  # Returns first and last IP in the range

def get_company_ranges(company_name):
    """
    Retrieves ASNs for the company, fetches IP ranges for each ASN, 
    and checks if the given IP address falls within any of those ranges.
    Returns a dictionary of IP ranges with 'start', 'finish', and 'asn_name'.
    
    :param company_name: The name of the company (e.g., 'Government of Canada').
    :param ip_to_check: The IP address to be checked.
    :return: A dictionary of IP ranges, or an empty dictionary if no ranges found.
    """
    result = []
    
    # Step 1: Get ASNs for the company
    asns = get_asns_for_company(company_name)
    if asns:
        #print(f"ASNs found for {company_name}: {', '.join(asns)}\n")  # Ensure all ASNs are strings
        #print(f"ASNs found for {company_name}: {', '.join(asn_numbers)}\n")

        # Step 2: Loop through each ASN and get IP ranges
        for asn in asns:
            ip_ranges = get_ip_ranges_for_asn(asn['asn'])
            if ip_ranges:
                print(f"Checking IP ranges assigned to {company_name} ({asn}):")
                for cidr in ip_ranges:
                    # Convert CIDR to start/end range
                    range_start, range_end = cidr_to_ip_range(cidr)
                    
                    # Add range details to the result list
                    result.append({
                        'start': range_start,
                        'end': range_end,
                        'asn_name': asn
                    })
            else:
                
                #ip_range_start = '205.192.0.0'
                #ip_range_end = '205.195.255.255'

                #result.append({
                #        'start': ip_range_start,
                #        'end': ip_range_end,
                #        'asn_name': 'Default'
                #    })


                print(f"No IP ranges found for ASN {asn}.")
    else:
        print(f"No ASNs found for {company_name}.")
    
    return result

    
def is_ip_in_range(ip_address, ip_ranges):
    """
    Check if the given IP address (IPv4 or IPv6) falls within any of the specified IP ranges.
    
    :param ip_address: The IP address to check (as a string).
    :param ip_ranges: A list of dictionaries where each dictionary contains 'start', 'end', and 'asn_name' fields.
    :return: True if the IP is within any of the ranges, False otherwise.
    """
    try:
        # Convert the IP address to the appropriate IP address object
        ip_obj = ipaddress.ip_address(ip_address)
        
        # Iterate through the list of IP ranges
        for ip_range in ip_ranges:
            start_ip = ipaddress.ip_address(ip_range['start'])
            end_ip = ipaddress.ip_address(ip_range['end'])
            
            # Check if the IP versions are compatible
            if type(ip_obj) != type(start_ip):
                # IP address and range are not of the same version (IPv4 vs IPv6)
                continue
            
            # Check if the IP address falls within the specified range
            if start_ip <= ip_obj <= end_ip:
                print(f"IP {ip_address} is in range {ip_range['start']} - {ip_range['end']} (ASN: {ip_range['asn_name']})")
                return True  # IP is within this range, no need to check further
        
        # If no ranges matched, return False
        return False
    
    except ValueError as e:
        print(f"Error: Invalid IP address or range '{ip_address}' - {e}")
        return False



# Dictionary mapping ip to region
region_by_ip_range = {
    ("10.17.0.0", "10.17.255.255"): "BC-YK",
    ("10.18.0.0", "10.18.255.255"): "BC-YK",
    ("10.19.0.0", "10.19.255.255"): "BC-YK",
    ("10.20.0.0", "10.20.255.255"): "BC-YK",
    ("10.21.0.0", "10.21.255.255"): "BC-YK",
    ("10.22.0.0", "10.22.255.255"): "BC-YK",
    ("10.23.0.0", "10.23.255.255"): "BC-YK",
    ("10.24.0.0", "10.24.255.255"): "BC-YK",
    ("10.25.0.0", "10.25.255.255"): "BC-YK",
    ("10.26.0.0", "10.26.255.255"): "BC-YK",
    ("10.27.0.0", "10.27.255.255"): "BC-YK",
    ("10.28.0.0", "10.28.255.255"): "BC-YK",
    ("10.29.0.0", "10.29.255.255"): "BC-YK",
    ("10.30.0.0", "10.30.255.255"): "BC-YK",
    ("10.31.0.0", "10.31.255.255"): "BC-YK",
    ("10.33.0.0", "10.33.255.255"): "AB-NWT",
    ("10.34.0.0", "10.34.255.255"): "AB-NWT",
    ("10.35.0.0", "10.35.255.255"): "AB-NWT",
    ("10.36.0.0", "10.36.255.255"): "AB-NWT",
    ("10.37.0.0", "10.37.255.255"): "AB-NWT",
    ("10.49.0.0", "10.49.255.255"): "SASK",
    ("10.50.0.0", "10.50.255.255"): "SASK",
    ("10.51.0.0", "10.51.255.255"): "SASK",
    ("10.52.0.0", "10.52.255.255"): "SASK",
    ("10.53.0.0", "10.53.255.255"): "SASK",
    ("10.65.0.0", "10.65.255.255"): "MAN",
    ("10.66.0.0", "10.66.255.255"): "MAN",
    ("10.67.0.0", "10.67.255.255"): "MAN",
    ("10.68.0.0", "10.68.255.255"): "MAN",
    ("10.69.0.0", "10.69.255.255"): "MAN",
    ("10.70.0.0", "10.70.255.255"): "MAN",
    ("10.71.0.0", "10.71.255.255"): "MAN",
    ("10.72.0.0", "10.72.255.255"): "MAN",
    ("10.73.0.0", "10.73.255.255"): "MAN",
    ("10.81.0.0", "10.81.255.255"): "ONT",
    ("10.82.0.0", "10.82.255.255"): "ONT",
    ("10.83.0.0", "10.83.255.255"): "ONT",
    ("10.84.0.0", "10.84.255.255"): "ONT",
    ("10.85.0.0", "10.85.255.255"): "ONT",
    ("10.86.0.0", "10.86.255.255"): "ONT",
    ("10.87.0.0", "10.87.255.255"): "ONT",
    ("10.88.0.0", "10.88.255.255"): "ONT",
    ("10.89.0.0", "10.89.255.255"): "ONT",
    ("10.90.0.0", "10.90.255.255"): "ONT",
    ("10.91.0.0", "10.91.255.255"): "ONT",
    ("10.92.0.0", "10.92.255.255"): "ONT",
    ("10.93.0.0", "10.93.255.255"): "ONT",
    ("10.94.0.0", "10.94.255.255"): "ONT",
    ("10.97.0.0", "10.97.255.255"): "QUE",
    ("10.98.0.0", "10.98.255.255"): "QUE",
    ("10.99.0.0", "10.99.255.255"): "QUE",
    ("10.100.0.0", "10.100.255.255"): "QUE",
    ("10.101.0.0", "10.101.255.255"): "QUE",
    ("10.102.0.0", "10.102.255.255"): "QUE",
    ("10.103.0.0", "10.103.255.255"): "QUE",
    ("10.104.0.0", "10.104.255.255"): "QUE",
    ("10.113.0.0", "10.113.255.255"): "ATL",
    ("10.114.0.0", "10.114.255.255"): "ATL",
    ("10.115.0.0", "10.115.255.255"): "ATL",
    ("10.116.0.0", "10.116.255.255"): "ATL",
    ("10.117.0.0", "10.117.255.255"): "ATL",
    ("10.118.0.0", "10.118.255.255"): "ATL",
    ("10.147.0.0", "10.147.255.255"): "NCR",
    ("10.148.0.0", "10.148.255.255"): "NCR",
    ("10.149.0.0", "10.149.255.255"): "NCR",
    ("10.150.0.0", "10.150.255.255"): "NCR",
    ("10.151.0.0", "10.151.255.255"): "NCR",
    ("10.152.0.0", "10.152.255.255"): "NCR",
    ("10.153.0.0", "10.153.255.255"): "NCR",
    ("10.154.0.0", "10.154.255.255"): "NCR",
    ("10.155.0.0", "10.155.255.255"): "NCR",
    ("10.156.0.0", "10.156.255.255"): "NCR",
    ("10.157.0.0", "10.157.255.255"): "NCR",
    ("10.158.0.0", "10.158.255.255"): "NCR",
    ("10.159.0.0", "10.159.255.255"): "NCR",
    ("10.131.0.0", "10.131.255.255"): "TP",
    ("10.132.0.0", "10.132.255.255"): "TP",
    ("10.133.0.0", "10.133.255.255"): "TP",
    ("10.134.0.0", "10.134.255.255"): "TP",
    ("10.135.0.0", "10.135.255.255"): "TP",
    ("10.136.0.0", "10.136.255.255"): "TP",
    ("10.137.0.0", "10.137.255.255"): "TP",
    ("10.138.0.0", "10.138.255.255"): "TP",
    ("10.139.0.0", "10.139.255.255"): "TP",
    ("10.140.0.0", "10.140.255.255"): "TP",
    ("10.141.0.0", "10.141.255.255"): "TP",
    ("10.254.0.0", "10.254.255.255"):"TP",
}
# Dictionary mapping IP range (start, end) to building names
building_by_ip_range = {
    ("10.17.2.0", "10.17.62.255"): {"location": "SINCLAIR CENTER 757 WEST HASTINGS STREET", "timezone": "America/Vancouver"},
    ("10.18.2.0", "10.18.62.255"): {"location": "3155 WILLINGDON GREEN", "timezone": "America/Vancouver"},
    ("10.19.58.0", "10.19.62.255"): {"location": "3211 GRANT MCCONACHIE WAY, RICHMOND Vancouver Airport", "timezone": "America/Vancouver"},
    ("10.21.2.0", "10.21.62.255"): {"location": "1230 GOVERNMENT STREET", "timezone": "America/Vancouver"},
    ("10.22.2.0", "10.22.62.255"): {"location": "5101-50TH AVENUE", "timezone": "America/Vancouver"},
    ("10.25.2.0", "10.25.62.255"): {"location": "3211 GRANT MCCONACHIE WAY", "timezone": "America/Vancouver"},
    ("10.26.2.0", "10.26.62.255"): {"location": "311-471 QUEENSWAY AVE Kelowna", "timezone": "America/Vancouver"},
    ("10.28.2.0", "10.28.62.255"): {"location": "351 ABBOTT ST", "timezone": "America/Vancouver"},
    ("10.29.2.0", "10.29.62.255"): {"location": "4595 CANADA WAY", "timezone": "America/Vancouver"},
    ("10.33.2.0", "10.33.62.255"): {"location": "9700 JASPER AVENUE", "timezone": "America/Edmonton"},
    ("10.34.2.0", "10.34.62.255"): {"location": "HARRY HAYES BLDG S ALBERTA ZONE-TREATY 7 220 4TH AVENUE S.E.", "timezone": "America/Edmonton"},
    ("10.35.2.0", "10.35.62.255"): {"location": "2000 AIRPORT RD NE, CALGARY", "timezone": "America/Edmonton"},
    ("10.49.2.0", "10.49.62.255"): {"location": "1783 HAMILTON ST - REGINA", "timezone": "America/Regina"},
    ("10.51.2.0", "10.51.62.255"): {"location": "412-101 22ND STREET EAST", "timezone": "America/Regina"},
    ("10.52.2.0", "10.52.62.255"): {"location": "PRINCE ALBERT SERVICE CENTRE 3601 EAST 5TH STREET", "timezone": "America/Regina"},
    ("10.65.2.0", "10.65.62.255"): {"location": "STANLEY KNOWLES BUILDING 391 YORK AVENUE", "timezone": "America/Winnipeg"},
    ("10.66.2.0", "10.66.62.255"): {"location": "SCIENCE CENTER 1015 ARLINGTON AVENUE", "timezone": "America/Winnipeg"},
    ("10.66.71.0", "10.66.72.255"): {"location": "SCIENCE CENTER 1015 ARLINGTON AVENUE WiFi", "timezone": "America/Winnipeg"},
    ("10.66.73.0", "10.66.73.255"): {"location": "435 ELLICE AVE, WINNIPEG WiFi", "timezone": "America/Winnipeg"},
    ("10.67.2.0", "10.67.62.255"): {"location": "475 LOGAN, WINNIPEG", "timezone": "America/Winnipeg"},
    ("10.68.2.0", "10.68.62.255"): {"location": "435 ELLICE AVE, WINNIPEG", "timezone": "America/Winnipeg"},
    ("10.69.2.0", "10.69.62.255"): {"location": "NORWAY HOUSE HOSPITAL", "timezone": "America/Winnipeg"},
    ("10.73.2.0", "10.73.62.255"): {"location": "1821 WELLINGTON, WINNIPEG", "timezone": "America/Winnipeg"},
    ("10.81.2.0", "10.81.62.255"): {"location": "180 QUEEN STREET TORONTO", "timezone": "America/Toronto"},
    ("10.82.2.0", "10.82.62.255"): {"location": "2301 MIDLAND AVE. SCARBOROUGH", "timezone": "America/Toronto"},
    ("10.84.2.0", "10.84.62.255"): {"location": "200 TOWN CENTER COURT, SCARBOROUGH", "timezone": "America/Toronto"},
    ("10.86.2.0", "10.86.62.255"): {"location": "LABORATORY FOR FOODBORNE ZOONOSES BUILDING 110 STONE ROAD WEST", "timezone": "America/Toronto"},
    ("10.90.2.0", "10.90.62.255"): {"location": "55 BAY STREET HAMILTON", "timezone": "America/Toronto"},
    ("10.91.2.0", "10.91.62.255"): {"location": "370 SPEEDVALE GUELPH", "timezone": "America/Toronto"},
    ("10.92.2.0", "10.92.62.255"): {"location": "5800 HURONTARIO, MISSISSAUGA", "timezone": "America/Toronto"},
    ("10.93.2.0", "10.93.62.255"): {"location": "86 CLARENCE AVE. KINGSTON", "timezone": "America/Toronto"},
    ("10.97.2.0", "10.97.62.255"): {"location": "PLACE GUY-FAVREAU 200 RENE LEVESQUE BLVD WEST SUITE 202", "timezone": "America/Montreal"},
    ("10.98.2.0", "10.98.62.255"): {"location": "1001 ST. LAURENT BLVD. WEST SUITE 365", "timezone": "America/Montreal"},
    ("10.99.2.0", "10.99.62.255"): {"location": "3400 CASAVANT BOULEVARD ST-HYACINTHE", "timezone": "America/Montreal"},
    ("10.100.2.0", "10.100.62.255"): {"location": "1550, AVE D'ESTIMAUVILLE", "timezone": "America/Montreal"},
    ("10.101.2.0", "10.101.62.255"): {"location": "101 ROLAND-THERIEN, LONGUEUIL", "timezone": "America/Montreal"},
    ("10.102.58.0", "10.102.62.255"): {"location": "975 ROMEO-VACHON, DORVAL", "timezone": "America/Montreal"},
    ("10.113.2.0", "10.113.62.255"): {"location": "MARITIME CENTER 1505 BARRINGTON STREET", "timezone": "America/Halifax"},
    ("10.114.20.0", "10.114.20.255"): {"location": "MARITIME CENTER 1505 BARRINGTON STREET WiFi", "timezone": "America/Halifax"},
    ("10.114.58.0", "10.114.62.255"): {"location": "DARTMOUTH, 1 CHALLENGER", "timezone": "America/Halifax"},
    ("10.116.2.0", "10.116.62.255"): {"location": "SIR HUMPHREY GILBERT BUILDING 10 BARTERS HILL", "timezone": "America/St_Johns"},
    ("10.118.2.0", "10.118.62.255"): {"location": "33 WELDON STREET, MONCTON", "timezone": "America/Moncton"},
    ("10.140.58.0", "10.140.61.255"): {"location": "55 CHARDON DRIVEWAY BLDG 17", "timezone": "America/Toronto"},
    ("10.141.56.0", "10.141.61.255"): {"location": "PERSONNEL RECORDS CENTRE BLDG 18", "timezone": "America/Toronto"},
    ("10.147.2.0", "10.147.59.255"): {"location": "RADIATION PROTECTION BUILDING 775 BROOKFIELD ROAD", "timezone": "America/Toronto"},
    ("10.148.130.0", "10.148.189.255"): {"location": "340 LEGGET", "timezone": "America/Toronto"},
    ("10.149.7.0", "10.149.7.255"): {"location": "130 COLONNADE ROAD WiFi", "timezone": "America/Toronto"},
    ("10.150.186.0", "10.150.189.255"): {"location": "359 TERRY FOX", "timezone": "America/Toronto"},
    ("10.150.58.0", "10.150.62.255"): {"location": "HEALTH PROTECTION BRANCH 1800 WALKLEY ROAD", "timezone": "America/Toronto"},
    ("10.151.2.0", "10.151.187.255"): {"location": "2525 LANCASTER", "timezone": "America/Toronto"},
    ("10.152.58.0", "10.152.59.255"): {"location": "960 CARLING, CENTRAL EXPERIMENTAL FARM", "timezone": "America/Toronto"},
    ("10.152.60.0", "10.152.60.255"): {"location": "1339 BASELINE", "timezone": "America/Toronto"},
    ("10.152.168.0", "10.152.190.255"): {"location": "785 CARLING", "timezone": "America/Toronto"},
    ("10.153.58.0", "10.153.62.255"): {"location": "1285 BASELINE", "timezone": "America/Toronto"},
    ("10.154.58.0", "10.154.59.255"): {"location": "350 KING EDWARD", "timezone": "America/Toronto"},
    ("10.156.50.0", "10.156.62.255"): {"location": "VANGUARD BUILDING 171 SLATER STREET", "timezone": "America/Toronto"},
    ("10.157.8.0", "10.157.10.255"): {"location": "405 TERMINAL RD Wifi", "timezone": "America/Toronto"},
    ("10.157.48.0", "10.157.62.255"): {"location": "405 TERMINAL RD", "timezone": "America/Toronto"},
    ("10.157.171.0", "10.157.190.255"): {"location": "269 LAURIER AVE", "timezone": "America/Toronto"},
    ("10.158.130.0", "10.158.190.255"): {"location": "BACKUP CRISIS CENTER 1481 MICHAEL ST.", "timezone": "America/Toronto"},
    ("10.159.6.0", "10.159.6.255"): {"location": "130 COLONNADE ROAD", "timezone": "America/Toronto"},
    ("10.159.34.0", "10.159.39.255"): {"location": "100 COLONNADE ROAD", "timezone": "America/Toronto"},
    ("10.159.46.0", "10.159.47.255"): {"location": "100 COLONNADE ROAD", "timezone": "America/Toronto"},
    ("10.159.54.0", "10.159.55.255"): {"location": "100 COLONNADE ROAD", "timezone": "America/Toronto"},
    ("10.159.40.0", "10.159.43.255"): {"location": "120 COLONNADE ROAD", "timezone": "America/Toronto"},
    ("10.159.2.0", "10.159.3.255"): {"location": "130 COLONNADE ROAD", "timezone": "America/Toronto"},
    ("10.159.44.0", "10.159.45.255"): {"location": "130 COLONNADE ROAD", "timezone": "America/Toronto"},
    ("10.159.48.0", "10.159.53.255"): {"location": "130 COLONNADE ROAD", "timezone": "America/Toronto"},
    ("10.159.56.0", "10.159.61.255"): {"location": "130 COLONNADE ROAD", "timezone": "America/Toronto"},
    ("10.159.136.0", "10.159.138.255"): {"location": "2 CONSTELLATION DRIVE WiFi", "timezone": "America/Toronto"},
    ("10.159.172.0", "10.159.190.255"): {"location": "2 CONSTELLATION DRIVE", "timezone": "America/Toronto"},
    ("10.131.10.0", "10.131.61.255"): {"location": "MAIN STATS BLDG", "timezone": "America/Toronto"},
    ("10.132.2.0", "10.132.61.255"): {"location": "LABORATORY CENTER FOR DISEASE CONTROL LCDC", "timezone": "America/Toronto"},
    ("10.133.2.0", "10.133.61.255"): {"location": "BROOKE CLAXTON BLDG", "timezone": "America/Toronto"},
    ("10.134.44.0", "10.134.61.255"): {"location": "ENVIRONMENTAL HEALTH CENTRE EHC", "timezone": "America/Toronto"},
    ("10.135.2.0", "10.135.61.255"): {"location": "FINANCE BLDG", "timezone": "America/Toronto"},
    ("10.137.40.0", "10.137.49.255"): {"location": "HOLLAND CROSS - TOWER A 1100 HOLLAND AVENUE", "timezone": "America/Toronto"},
    ("10.137.50.0", "10.137.61.255"): {"location": "HOLLAND CROSS - TOWER B 1600 SCOTT STREET", "timezone": "America/Toronto"},
    ("10.137.36.0", "10.137.39.255"): {"location": "HOLLAND CROSS - TOWER B 1600 SCOTT STREET", "timezone": "America/Toronto"},
    ("10.138.2.0", "10.138.61.255"): {"location": "JEANNE MANCE BLDG", "timezone": "America/Toronto"},
    ("10.139.2.0", "10.139.61.255"): {"location": "SIR FREDERICK G. BANTING BLDG", "timezone": "America/Toronto"},
    ("10.254.0.0", "10.254.6.255"): {"location": "JEANNE MANCE WiFi", "timezone": "America/Toronto"},
    ("10.254.7.0", "10.254.9.255"): {"location": "130 COLONNADE WiFi", "timezone": "America/Toronto"},
    ("10.254.10.0", "10.254.11.255"): {"location": "100 COLONNADE WiFi", "timezone": "America/Toronto"},
    ("10.254.12.0", "10.254.12.255"): {"location": "120 COLONNADE WiFi", "timezone": "America/Toronto"},
    ("10.254.13.0", "10.254.16.255"): {"location": "BROOKE CLAXTON WiFi", "timezone": "America/Toronto"},
    ("10.254.19.0", "10.254.21.255"): {"location": "269 LAURIER WiFi", "timezone": "America/Toronto"},
    ("10.254.22.0", "10.254.24.255"): {"location": "785 CARLING WiFi", "timezone": "America/Toronto"},
    ("10.254.28.0", "10.254.30.255"): {"location": "HOLLAND CROSS WiFi", "timezone": "America/Toronto"},
    ("10.254.31.0", "10.254.31.255"): {"location": "171 SLATER WiFi", "timezone": "America/Toronto"},
    ("10.254.32.0", "10.254.33.255"): {"location": "200 RENE LEVESQUE WiFi", "timezone": "America/Toronto"},
    ("10.254.34.0", "10.254.36.255"): {"location": "MAIN STATS BLDG WiFi", "timezone": "America/Toronto"},
    ("10.254.40.0", "10.254.40.255"): {"location": "ROLAND THERIEN LONGUEUIL Wifi", "timezone": "America/Toronto"},
    ("10.254.41.0", "10.254.44.255"): {"location": "HOLLAND CROSS WiFi", "timezone": "America/Toronto"},
    ("10.254.47.0", "10.254.47.255"): {"location": "OHU WiFi", "timezone": "America/Toronto"}
}


def get_asns_for_company(company_name_orig):
    """
    Fetches ASNs assigned to a company using Hurricane Electric BGP Toolkit.
    
    :param company_name: The name of the company (e.g., 'Google', 'Amazon').
    :return: A list of dictionaries with ASN and company name or None if not found.
    """
    url = f'https://bgp.he.net/search?search[search]={company_name_orig}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        
        # Parse the HTML using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all ASN entries in the table (typically in 'a' tags within table rows)
        asns = []
        for row in soup.select('table tbody tr'):
            asn_link = row.find('a')
            if asn_link and asn_link.get('href', '').startswith('/AS'):
                asn = asn_link.text.strip()  # Extract the ASN number
                company_name = row.find_all('td')[2].text.strip()  # Company name in 3rd <td>
                if company_name_orig == company_name:
                    asns.append({'asn': asn, 'company_name': company_name})
        
        return asns if asns else None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching ASNs for {company_name}: {e}")
        return None

# Function to get IP ranges for a given ASN using RIPEstat API
def get_ip_ranges_for_asn(asn):
    """
    Fetches the IP ranges assigned to a specific ASN using the RIPEstat API.
    
    :param asn: The ASN number (e.g., 'AS13920').
    :return: A list of IP ranges.
    """
    url = f'https://stat.ripe.net/data/announced-prefixes/data.json?resource={asn}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        
        data = response.json()
        if 'data' in data and 'prefixes' in data['data']:
            # Extracting both IPv4 and IPv6 ranges
            ip_ranges = [prefix['prefix'] for prefix in data['data']['prefixes']]
            return ip_ranges
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching IP ranges for ASN {asn}: {e}")
        return None

# Function to get IP ranges for a given ASN
def get_ip_ranges_for_asn_old(asn):
    """
    Fetches the IP ranges assigned to a specific ASN using the BGPView API.
    
    :param asn: The ASN number (e.g., 'AS13920').
    :return: A list of IP ranges.
    """
    url = f'https://api.bgpview.io/asn/{asn}/prefixes'
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        
        data = response.json()
        if 'data' in data and 'ipv4_prefixes' in data['data']:
            # Extracting only IPv4 ranges
            ipv4_ranges = [prefix['prefix'] for prefix in data['data']['ipv4_prefixes']]
            return ipv4_ranges
        else:
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching IP ranges for ASN {asn}: {e}")
        return None

# Function to check if an IP address is in a range defined by CIDR
def cidr_to_ip_range(cidr):
    """
    Convert a CIDR notation string into a tuple (range_start, range_end) with IP strings.
    
    :param cidr: The CIDR notation string (e.g., '203.104.80.0/20').
    :return: A tuple of (start_ip, end_ip) as strings.
    """
    network = ipaddress.ip_network(cidr, strict=False)
    return str(network[0]), str(network[-1])  # Returns first and last IP in the range

def get_company_ranges(company_name):
    """
    Retrieves ASNs for the company, fetches IP ranges for each ASN, 
    and checks if the given IP address falls within any of those ranges.
    Returns a dictionary of IP ranges with 'start', 'finish', and 'asn_name'.
    
    :param company_name: The name of the company (e.g., 'Government of Canada').
    :param ip_to_check: The IP address to be checked.
    :return: A dictionary of IP ranges, or an empty dictionary if no ranges found.
    """
    result = []
    
    # Step 1: Get ASNs for the company
    asns = get_asns_for_company(company_name)
    if asns:
        #print(f"ASNs found for {company_name}: {', '.join(asns)}\n")  # Ensure all ASNs are strings
        #print(f"ASNs found for {company_name}: {', '.join(asn_numbers)}\n")

        # Step 2: Loop through each ASN and get IP ranges
        for asn in asns:
            ip_ranges = get_ip_ranges_for_asn(asn['asn'])
            if ip_ranges:
                print(f"Checking IP ranges assigned to {company_name} ({asn}):")
                for cidr in ip_ranges:
                    # Convert CIDR to start/end range
                    range_start, range_end = cidr_to_ip_range(cidr)
                    
                    # Add range details to the result list
                    result.append({
                        'start': range_start,
                        'end': range_end,
                        'asn_name': asn
                    })
            else:
                
                #ip_range_start = '205.192.0.0'
                #ip_range_end = '205.195.255.255'

                #result.append({
                #        'start': ip_range_start,
                #        'end': ip_range_end,
                #        'asn_name': 'Default'
                #    })


                print(f"No IP ranges found for ASN {asn}.")
    else:
        print(f"No ASNs found for {company_name}.")
    
    return result

    
def is_ip_in_range(ip_address, ip_ranges):
    """
    Check if the given IP address (IPv4 or IPv6) falls within any of the specified IP ranges.
    
    :param ip_address: The IP address to check (as a string).
    :param ip_ranges: A list of dictionaries where each dictionary contains 'start', 'end', and 'asn_name' fields.
    :return: True if the IP is within any of the ranges, False otherwise.
    """
    try:
        # Convert the IP address to the appropriate IP address object
        ip_obj = ipaddress.ip_address(ip_address)
        
        # Iterate through the list of IP ranges
        for ip_range in ip_ranges:
            start_ip = ipaddress.ip_address(ip_range['start'])
            end_ip = ipaddress.ip_address(ip_range['end'])
            
            # Check if the IP versions are compatible
            if type(ip_obj) != type(start_ip):
                # IP address and range are not of the same version (IPv4 vs IPv6)
                continue
            
            # Check if the IP address falls within the specified range
            if start_ip <= ip_obj <= end_ip:
                #print(f"IP {ip_address} is in range {ip_range['start']} - {ip_range['end']} (ASN: {ip_range['asn_name']})")
                return True  # IP is within this range, no need to check further
        
        # If no ranges matched, return False
        return False
    
    except ValueError as e:
        print(f"Error: Invalid IP address or range '{ip_address}' - {e}")
        return False
    
def flatten_data(data, parent_key='', sep='_'):
    """
    Recursively flatten a nested dictionary or list into a single level dictionary.
    
    :param data: The dictionary or list to flatten.
    :param parent_key: The base key string (used for recursive calls).
    :param sep: The separator between parent and child keys.
    :return: A flattened dictionary.
    """
    items = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, dict):
                items.extend(flatten_data(value, new_key, sep=sep).items())
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    items.extend(flatten_data(item, f"{new_key}{sep}{i}", sep=sep).items())
            else:
                items.append((new_key, value))
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            items.extend(flatten_data(item, f"{parent_key}{sep}{i}", sep=sep).items())
    
    else:
        items.append((parent_key, data))
    
    return dict(items)



def save_to_file(
    data=None,
    file='data',
    file_type='CSV',
    flatten=True,
    service_client=None,
    container_name=None,
    directory_name=None
):
    """
    Generic function to save data to a file (CSV or JSON).
    Can save to local storage or Azure Data Lake based on provided parameters.
    Can handle dictionaries, lists, and nested data structures.

    :param data: The data to save.
    :param file: The base file name to save.
    :param file_type: The type of file to save ('CSV' or 'JSON').
    :param flatten: Whether to flatten the data before saving (default is True).
    :param service_client: (Optional) An instance of DataLakeServiceClient.
    :param container_name: (Optional) The name of the container in Azure Data Lake.
    :param directory_name: (Optional) The name of the directory in Azure Data Lake.
    """
    try:
        if data is None:
            raise ValueError("No data provided.")

        # Flatten the data if required
        if flatten:
            if isinstance(data, dict):
                data = [flatten_data(data, max_depth=2)]
            elif isinstance(data, list):
                data = [flatten_data(item, max_depth=2) if isinstance(item, dict) else item for item in data]
            else:
                data = [data]

        # Determine file extension and prepare data
        if file_type.upper() == 'JSON':
            file_name = f'{file}.json'
            file_content = json.dumps(data, ensure_ascii=False, indent=4)
            data_bytes = file_content.encode('utf-8')
        elif file_type.upper() == 'CSV':
            file_name = f'{file}.csv'
            df = pd.DataFrame(data)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False, quoting=csv.QUOTE_ALL, encoding='utf-8')
            file_content = csv_buffer.getvalue()
            data_bytes = file_content.encode('utf-8')
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        # Decide where to save the file
        if service_client and container_name:
            # Save to Azure Data Lake
            from azure.storage.filedatalake import DataLakeServiceClient  # Import here to keep it optional

            # Get file system client
            file_system_client = service_client.get_file_system_client(file_system=container_name)

            # Get directory client
            if directory_name:
                directory_client = file_system_client.get_directory_client(directory_name)
            else:
                directory_client = file_system_client.get_directory_client('/')

            # Create or overwrite the file in Azure Data Lake
            file_client = directory_client.create_file(file_name)
            file_client.append_data(data=data_bytes, offset=0, length=len(data_bytes))
            file_client.flush_data(len(data_bytes))

            print(f"Data saved to {file_name} in Azure Data Lake")
        else:
            # Save locally
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write(file_content)
            print(f"Data saved to {file_name} locally")

    except Exception as e:
        print(f"Error: Saving File '{file}' - {e}")
        return False

def flatten_data(d, parent_key='', sep='_', max_depth=2, current_depth=0):
    """
    Flattens a nested dictionary up to a maximum depth.
    
    :param d: The dictionary to flatten.
    :param parent_key: The prefix key (used in recursive calls).
    :param sep: Separator between keys.
    :param max_depth: Maximum recursion depth (None for unlimited).
    :param current_depth: Current recursion depth.
    :return: A flattened dictionary.
    """
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict) and (max_depth is None or current_depth < max_depth):
            items.update(flatten_data(v, new_key, sep=sep, max_depth=max_depth, current_depth=current_depth+1))
        elif isinstance(v, list) and (max_depth is None or current_depth < max_depth):
            # Only flatten list items if the list is non-empty.
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    items.update(flatten_data(item, f"{new_key}{sep}{i}", sep=sep, max_depth=max_depth, current_depth=current_depth+1))
                else:
                    items[f"{new_key}{sep}{i}"] = item
        else:
            items[new_key] = v
    return items


def save_to_file_old(data=None, file='data', file_type='CSV', flatten=True):
    """
    Generic function to save data to a file (CSV or JSON). 
    Can handle dictionaries, lists, and nested data structures.
    
    :param data: The data to save.
    :param file: The base file name to save.
    :param file_type: The type of file to save ('CSV' or 'JSON').
    :param flatten: Whether to flatten the data before saving (default is True).
    """
    try:
        if data is None:
            raise ValueError("No data provided.")
        
        if flatten:
            # Flatten the data if it's a dictionary or list
            if isinstance(data, dict) or isinstance(data, list):
                data = [flatten_data(item) if isinstance(item, dict) else item for item in data] if isinstance(data, list) else [flatten_data(data)]

        if file_type.upper() == 'JSON':
            # Save data to a JSON file with proper handling of extended characters
            with open(f'{file}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"Data saved to {file}.json")
        
        elif file_type.upper() == 'CSV':
            # Save data to a CSV file with proper handling of quotes and extended characters
            df = pd.DataFrame(data)
            df.to_csv(f'{file}.csv', index=False, quoting=csv.QUOTE_ALL, encoding='utf-8')
            print(f"Data saved to {file}.csv")
        
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    except ValueError as e:
        print(f"Error: Saving File '{file}' - {e}")
        return False
    
def write_aad_tree_to_csv(aad_tree, file_name='aad_tree.csv', expected_num_columns=3):
    """
    Writes the Azure AD tree structure to a CSV file, ensuring proper quoting and consistent row length.

    :param aad_tree: The Azure AD tree structure (dictionary).
    :param file_name: The name of the CSV file to write.
    :param expected_num_columns: The expected number of columns in the CSV (default is 3).
    """
    # Open the file for writing with quoting enabled
    with open(file_name, 'w', newline='') as csvfile:
        # Define the CSV writer with quoting enabled for all fields
        csvwriter = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
        
        # Write the header (adjust based on your data structure)
        csvwriter.writerow(['Group Name', 'Member Name', 'Member Type'])
        
        # Loop through the aad_tree and write each group and its members
        for group_name, group_data in aad_tree.items():
            for member in group_data['members']:
                # Determine if the member is a user or a group
                member_type = 'User' if 'userPrincipalName' in member else 'Group'
                member_name = member.get('userPrincipalName', member.get('displayName', ''))
                
                # Ensure the row has the expected number of columns
                row = [group_name, member_name, member_type]
                while len(row) < expected_num_columns:
                    row.append('')  # Add empty strings to match expected number of columns
                
                # Write the row with proper quoting and consistent length
                csvwriter.writerow(row)

def clean_csv(input_file, output_file, expected_num_columns=3):
    """
    Cleans the CSV file to ensure proper quoting and consistent row length.

    :param input_file: The path to the input CSV file.
    :param output_file: The path to the output (cleaned) CSV file.
    :param expected_num_columns: The expected number of columns in the CSV (default is 3).
    """
    with open(input_file, 'r') as infile, open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile, quoting=csv.QUOTE_ALL)
        
        for row in reader:
            # Ensure each row has the expected number of columns (add empty strings where necessary)
            while len(row) < expected_num_columns:
                row.append('')
            writer.writerow(row)

def save_group_members_to_csv(group_data, file_name='group_members'):
    """
    Saves group member data from a dictionary to a CSV file, where each row contains group_id, group_name, and userPrincipalName.
    
    :param group_data: The dictionary containing group member data.
    :param file_name: The name of the CSV file to write.
    """

    file_name = file_name + '.csv'
    # Open the file for writing with quoting enabled
    with open(file_name, 'w', newline='', encoding='utf-8') as csvfile:
        # Define the CSV writer with quoting enabled for all fields
        csvwriter = csv.writer(csvfile, quoting=csv.QUOTE_ALL)
        
        # Write the header (group_id, group_name, userPrincipalName)
        csvwriter.writerow(['Group ID', 'Group Name', 'User Principal Name'])

        # Loop through the group data and write each member's details
        for group_name, group_info in group_data.items():
            for member in group_info['members']:
                #if member['group_id'] and member['group_name'] and member['userPrincipalName']:
                csvwriter.writerow([member['group_id'], member['group_name'], member['userPrincipalName']])



class TimezoneConverter:
    """
    A class to handle timezone conversion and list all available timezones.
    """

    def __init__(self):
        """
        Initialize the converter.
        """
        self.utc_zone = pytz.utc  # UTC timezone reference

    def convert_to_timezone(self, utc_timestamp, timezone_str):
        """
        Convert a UTC timestamp to the specified timezone.

        :param utc_timestamp: The UTC timestamp (datetime) to convert.
        :param timezone_str: The string of the timezone to convert to.
        :return: The timestamp converted to the specified timezone.
        """
        try:
            # Ensure the UTC timestamp has a timezone associated with it
            utc_time = utc_timestamp.replace(tzinfo=self.utc_zone)
            
            # Get the target timezone from the supplied string
            target_timezone = pytz.timezone(timezone_str)
            
            # Convert the UTC timestamp to the target timezone
            local_time = utc_time.astimezone(target_timezone)
            
            return local_time
        
        except Exception as e:
            raise ValueError(f"Invalid timezone or conversion error: {e}")

    def list_all_timezones(self):
        """
        List all available timezones supported by pytz.

        :return: A list of all timezone strings.
        """
        return pytz.all_timezones