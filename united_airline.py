import csv
import json
import datetime
import time

import requests
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

headers = dict()


def total_available_seats(availability_string):
    # Split the string into individual class-availability pairs
    class_availability_pairs = availability_string.split('|')

    # Sum up the available seats across all classes
    total_seats = sum(int(pair[-1]) for pair in class_availability_pairs)

    return total_seats


def get_data(origin, destination, departure_date):
    global headers
    url = 'https://www.united.com/api/flight/FetchFlights'

    payload = {"SearchTypeSelection": 1, "SortType": "bestmatches", "SortTypeDescending": False, "Trips": [
        {"Origin": origin, "Destination": destination, "DepartDate": "2024-02-15", "Index": 1, "TripIndex": 1,
         "SearchRadiusMilesOrigin": 0, "SearchRadiusMilesDestination": 0, "DepartTimeApprox": 0,
         "SearchFiltersIn": {"FareFamily": "FIRST", "AirportsStop": None, "AirportsStopToAvoid": None}}],
               "CabinPreferenceMain": "premium", "PaxInfoList": [{"PaxType": 1}], "AwardTravel": True, "NGRP": True,
               "CalendarLengthOfStay": 0, "PetCount": 0, "RecentSearchKey": "ORDATH6/9/2024",
               "CalendarFilters": {"Filters": {"PriceScheduleOptions": {"Stops": 1}}},
               "Characteristics": [{"Code": "SOFT_LOGGED_IN", "Value": False},
                                   {"Code": "UsePassedCartId", "Value": False}], "FareType": "mixedtoggle",
               "CartId": "8014E5CF-5E05-4F18-84A1-14A4F0459DE3"}
    blocked = True
    while blocked:
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=10)
            blocked = False
        except:
            print('got blocked')

            headers = get_headers()

    flights_data = json.loads(response.text)

    arr = []

    for flight in flights_data['data']['Trips'][0]['Flights']:
        for product in flight["Products"]:
            item = dict()

            def safe_get(container, keyss, default=''):
                """Safely get a value from a nested dictionary or list."""
                temp = container
                for key in keyss:
                    try:
                        temp = temp[key]
                    except (KeyError, IndexError, TypeError):
                        return default
                return temp

            # Use the safe_get function to retrieve values safely
            item['Departure Date'] = flight.get('DepartDateTime', '').split()[0]
            item['Departure Time'] = flight.get('DepartDateTime', '').split()[1]

            item['Departure Airport Code'] = safe_get(flight,
                                                      ['Warnings', 0, 'SDLMessages', 0, 'Params', 'DepartAirportCode'])
            item['Arrival Airport Code'] = safe_get(flight,
                                                    ['Warnings', 0, 'SDLMessages', 1, 'Params', 'ArriveAirportCode'])
            item['Departure City'] = flight.get('Origin', '')
            item['Departure State'] = flight.get('OriginStateCode', '')
            item['Departure Country'] = flight.get('OriginCountryCode', '')

            item['Arrival Date'] = flight.get('DestinationDateTime', '').split()[0]
            item['Arrival Time'] = flight.get('DestinationDateTime', '').split()[1]

            item['Arrival City'] = flight.get('Destination', '')
            item['Arrival State'] = flight.get('DestinationStateCode', '')
            item['Arrival Country'] = flight.get('DestinationCountryCode', '')
            item['Flight Duration'] = flight.get('TravelMinutesTotal', '')

            overnight_flights = [v for v in flight.get('Warnings', []) if 'Night' in v.get('Title', '')]
            item['Overnight Flight'] = 'Yes' if overnight_flights and not overnight_flights[0].get('Hidden',
                                                                                                   False) else 'No'

            item['# Stops'] = 'Yes' if flight.get('StopInfos') else 'No'
            item['Nonstop Flight'] = 'No' if flight.get('StopInfos') else 'Yes'
            item['# Available Tickets'] = total_available_seats(flight.get("BookingClassAvailability", []))

            item['Booking Airline Code'] = flight.get('MarketingCarrier', '')
            item['Booking Airline Description'] = flight.get('MarketingCarrierDescription', '')
            item['Operating Airline Code'] = flight.get('OperatingCarrier', '')
            item['Operating Airline Description'] = flight.get('OperatingCarrierDescription', '')
            item['Operating Airline Flight #'] = flight.get('OriginalFlightNumber', '')
            item['Operating Airline Flight # Description'] = flight.get("OperatingCarrier", "") + flight.get(
                "OriginalFlightNumber", "")

            item['Aircraft Code'] = safe_get(flight, ['EquipmentDisclosures', 'EquipmentType'])
            item['Aircraft Description'] = safe_get(flight, ['EquipmentDisclosures', 'EquipmentDescription'])
            item['Cabin Class'] = product.get('CabinType', '')

            item['Airline Points'] = product['Prices'][0]['Amount'] if product['Prices'] else ''

            item['Airline Taxes'] = product['Prices'][1]['Amount'] if product['Prices'] else ''
            item['Currency'] = product['Prices'][1]['Currency'] if product['Prices'] else ''
            if item['Airline Points']:
                arr.append(item)

    unique_arr = []
    seen = set()

    for item in arr:
        # Convert the dictionary to a tuple of its sorted items for comparison
        item_tuple = tuple(sorted(item.items()))
        if item_tuple not in seen:
            seen.add(item_tuple)
            unique_arr.append(item)

    # Now unique_arr contains only unique items
    arr = unique_arr

    # Specify the filename for your CSV file
    filename = 'data/flights_data_{}_{}_{}.csv'.format(origin, destination, departure_date)

    # Determine the fieldnames from the keys of the first dictionary in the list
    # This assumes all dictionaries have the same structure
    fieldnames = arr[0].keys() if arr else []

    # Write the data to a CSV file
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer1 = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write the header
        writer1.writeheader()

        # Write the data rows
        for item in arr:
            writer1.writerow(item)

    print(f"Data successfully saved to {filename}")


def create_driver():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)

    return driver


def get_headers():
    print('Getting Headers')
    driver = create_driver()
    driver.maximize_window()
    driver.get('https://www.united.com/')
    time.sleep(5)
    driver.find_element(By.ID, 'bookFlightOriginInput').send_keys('NYC')
    driver.find_element(By.ID, 'bookFlightOriginInput').send_keys(Keys.TAB)
    time.sleep(2)
    driver.find_element(By.ID, 'bookFlightDestinationInput').send_keys('DXB')
    driver.find_element(By.ID, 'bookFlightDestinationInput').send_keys(Keys.TAB)
    time.sleep(2)
    driver.find_element(By.CSS_SELECTOR, '#bookFlightForm > div.app-components-BookFlightForm-bookFlightForm__basicEconomyToggle--pRdq1 > div > div:nth-child(1) > div > div > div.app-components-BookFlightForm-bookFlightForm__actionButtons--nHDk1 > button.atm-c-btn.app-components-BookFlightForm-bookFlightForm__findFlightBtn--wBfJd.atm-c-btn--primary').send_keys(Keys.RETURN)
    time.sleep(10)
    while not [v for v in driver.requests if 'FetchFlights' in v.path]:
        time.sleep(1)
    request = [v for v in driver.requests if 'FetchFlights' in v.path][0]
    global headers
    headers = dict(request.headers)
    driver.quit()
    return headers


if __name__ == '__main__':
    origin = 'ORD'
    destination = 'ATH'
    today = datetime.datetime.now()
    print(today)
    headers = get_headers()
    for i in range(1, 90):
        due_date = today + datetime.timedelta(days=i)
        print('getting data for {}'.format(due_date))
        get_data(origin, destination, str(due_date).split()[0])

    print(datetime.datetime.now())
