import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random

with open("creds.json", "r") as file: # sensitive info kept in separate file
    creds = json.load(file)
    target_url = creds["targeturl"]
    login_url = creds["loginurl"]
    email = creds["email"]
    password = creds["pass"]

def extract_payrate(pay_string):
    """
    This is just a helper function that uses regex to extract the payrate as a float

    1. Searches for the pattern "$<number>" in the string argument
    2. Extracts the digits in the string
    3. Converts to a float
    """
    match = re.search(r'\$([0-9,.]+)', pay_string)
    if match:
        return float(match.group(1).replace(',',''))
    return None



def login(session):
    """
    This function logs into the url at login_url using my login credentials

    1. Gets the html for the login page using an HTTP GET request with the session argument
    2. Finds the authenticity token in the page
    3. Adds the email, password, and auth token data to a dictionary
    4. Inputs my credentials using an HTTP POST request
    5. If it works, the session ends up on the dashboard page.
    """

    login_page = session.get(login_url)
    soup = BeautifulSoup(login_page.content, 'html.parser')

    authenticity_token_input = soup.find('input', {'name': 'authenticity_token'})
    if authenticity_token_input is None:
        raise ValueError("Could not find authenticity token on the login page")
    authenticity_token = authenticity_token_input['value']

    payload = {
        'user[email]': email,
        'user[password]': password,
        'authenticity_token': authenticity_token,
    }

    response = session.post(login_url, data=payload)

def scrape_projects(session):
    """
    This function gets the JSON data from the html in the dashboard page

    1. Access the dashboard page using the requests session that's passed as an argument
    2. Find the html tag containing the dashboard table and make a bs4 tag object out of it
    3. Grab the JSON data from "data-react-props"
    4. Grab the projects list from the JSON object
    5. Initialize an empty list and add projects from the projects list if they pay more than $32.50 and have 10+ tasks
    6. Send the resulting JSON object to stdout

    The stdout is then sent to the bot to be processed and sent to the channel
    """
    target_page = session.get(target_url)
    soup = BeautifulSoup(target_page.content, 'html.parser')

    data_div = soup.find('div', {'data-react-class': 'workers/WorkerProjectsTable'})
    if data_div:
        json_props = json.loads(data_div['data-react-props'])
        projects = json_props["dashboardMerchTargeting"]["projects"]
        projects_info = []
        for project in projects:
            pay = extract_payrate(project["pay"])
            num_tasks = int(project["availableTasksFor"])
            if pay and pay >= 32.50 and num_tasks > 10:
                project_info = {"name": project["name"],
                                "id": project["id"],
                                "pay": project["pay"],
                                "numTasks": project["availableTasksFor"]}
                projects_info.append(project_info)

        print(json.dumps(projects_info), flush=True)

    else:
        print("Element with data-react-props not found")


def scrapetable():
    """
    This is the main function of the script. It scrapes the table from the website and then
    repeats at random intervals. It also logs out and logs back in very 1-2 hours.

    1. Set up a session object to interact with the website
    2. Save the time of the current login
    3. The login interval is set to be between 3600 seconds and 7200 seconds, or 1-2 hours
    4. The refresh interval is 1-5 minutes
    5. Login to the website
    6. Loop endlessly, compare the current time to the previous login time; if the elapsed time is greater than the login interval, then close the session and login again, while randomizing the interval again.
    7. Sleep for refresh_interval number of seconds, then randomize the interval again upon waking
    """
    session = requests.Session()
    last_login = time.time()
    login_interval = random.randint(3600,7200)
    refresh_interval = random.randint(60,300)
    login(session)

    while True:
        current_time = time.time()
        if current_time - last_login >= login_interval:
            session.close()
            session = None
            session = requests.Session()
            login(session)
            login_interval = random.randint(3600,7200)
            last_login = current_time

        scrape_projects(session)
        time.sleep(refresh_interval)
        refresh_interval = random.randint(60,300)

if __name__ == "__main__":
    scrapetable()
