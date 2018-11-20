"""
A tutorial for testing webscraping using BeautifulSoup

Grabs invoicing issues from the system's Invoices tab.
Asks the user for a number of pages to search, searches the pages,
makes sure the data looks okay, then saves any potential issues in a CSV.
"""


import csv
import datetime
import os
import requests
import sys
import warnings

from bs4 import BeautifulSoup


# Filters out whitespace and other undesirable parts of a string
def strclean(in_str):
    out_str = in_str
    out_str = out_str.strip()
    out_str = out_str.replace("PAID", "")
    return out_str


def getExceptionList():
    """
    Creates a list of invoice numbers, customer names, etc. from a text file.
    Items inside this list are omitted from search results.
    :return: return_list - the list mentioned above.
    """
    return_list = []
    with open("ignore_list.txt", "r") as read_file:
        for line in read_file:
            return_list.append(line)

    return return_list


def saveExceptionList(exceptions):
    """
    Saves a list of invoice numbers, customer names, etc. to a text file for
    later use. This file is read upon running the program, and items inside
    are omitted from search results.
    :param exceptions: A list of invoice numbers, customer names, etc.
    :return: None
    """
    with open("ignore_list.txt", "w") as write_file:
        for item in exceptions:
            write_file.writeline(item)


# Determines if a customer is a wholesaler
def isWholesaler(cust):
    wholesalers = [
        "Lipsey\'s LLC",
        "MidwayUSA",
        "Hill Country Wholesale INC(Camfour)",
        "RSR Group INC",
        "IntegraCore..",
        "IntegraCore.. ",
        "RSR Group INC",
        "Lipsey's LLC",
        "Bill Hicks & Co LTD",
        "Sports South LLC",
        "Sports South LLC ",
        "Davidsons INC",
        "Bangers Enterprises Inc",
        "Acusport Corporation",
        "Brownells(Grinnell)",
        "Brownells(Grinnell) ",
        "Brownells (Grinnell)",
        "Brownells (Grinnell) ",
        "Big Rock Sports, LLC(MN)",
        "Ellett Brothers LLC",
        "Capitol Armory",
        "Big Rock Sports LLC",
        "Camfour INC",
        "Hill Country Class 3",
        "O.F.Mossberg & Sons Inc.(OEM)",
        "Noveske Rifleworks LLC",
        "SilencerCo(In House)"
    ]
    if cust in wholesalers:
        return True
    else:
        return False

def main_loop():

    num_pages = 120
    current_page = 1

    # Get the list of invoices, customers, etc. to ignore
    ignorelist = getExceptionList()
    used_ignorelist = []

    # Creating a new page request object
    scrape_url = "https://system.silencerco.com/invoices?page=" + \
                 str(current_page)
    
    page = requests.get(scrape_url, verify=False)

    # Running the page data through BeautifulSoup -- this holds all data
    soup = BeautifulSoup(page.content, "html.parser")

    """
    # Getting to the HTML tag
    html = soup.find("html")

    # Getting to the body tag
    body = html.find("body")
    """

    # Creating an invoice number counter, based on the top invoice
    counter = soup.find("td",
                        class_="ref_number-column sorted numeric").get_text()
    counter = int(strclean(counter))
    backup_count = 0

    # List of tuples for exporting
    export_list = []
    issue_count = 0
    issue_pages = []

    # Loop through page, then move to the next, until we're out of pages.
    while True:

        # Code for grabbing the table data
        tr = soup.find(id="as_invoices-list-" + str(counter) + "-row")

        # If the specified invoice is not found, the backup counter increases
        if not tr:
            backup_count += 1
            counter -= 1
            if backup_count < 10:
                continue
        else:
            backup_count = 0

        # Switches pages after 10 attempts to find the specified invoice
        if backup_count == 10:
            current_page += 1
            backup_count = 0
            if current_page > num_pages:

                if not issue_count:
                    print("\nEverything looks good over the last " +
                          str(num_pages) +
                          " pages!")
                    exit()
                if issue_count == 1:
                    print("\nThere was " +
                          str(issue_count) +
                          " potential issue over the last " +
                          str(num_pages) + " pages.")
                else:
                    print("\nThere were " +
                          str(issue_count) +
                          " potential issues over the last " +
                          str(num_pages) + " pages.")
                # Save results to csv file
                resultsfile = "C:\\Users\\christian\\Downloads\\refresh_results.csv"
                with open(resultsfile, "w") as file:
                    resultswriter = csv.writer(file,
                                               delimiter=",",
                                               lineterminator='\r')
                    header_row = ["Ref_Num",
                                  "Customer",
                                  "Date",
                                  "Clear-to-Ship",
                                  "Shipped",
                                  "Status",
                                  "Invoice_Page"]
                    resultswriter.writerow(header_row)
                    for item in export_list:
                        resultswriter.writerow(item)
                    print("Results saved in " + file.name)

                saveExceptionList(used_ignorelist)

                exit()
            else:
                scrape_url = None
                page = None
                soup = None

                issue_page_text = ""
                for item in issue_pages:
                    if issue_page_text:
                        issue_page_text += (", " + str(item))
                    else:
                        issue_page_text += str(item)

                print("")
                if issue_count:
                    print(str(issue_count) + " issues on following pages:")
                    print("Page(s) " + issue_page_text)
                print("Searching page " + str(current_page) + "...")

                # Creating a new page request object
                scrape_url = "https://system.silencerco.com/invoices?page=" + \
                             str(current_page)
                page = requests.get(scrape_url, verify=False)

                # Running the page data through BeautifulSoup again
                soup = BeautifulSoup(page.content, "html.parser")
                counter = soup.find("td",
                                    class_="ref_number-column sorted numeric"
                                    ).get_text()
                counter = int(strclean(counter))
                backup_count = 0
                continue

        # Grab the reference number
        refnum = tr.find(class_="ref_number-column sorted numeric").get_text()
        refnum = strclean(refnum)

        # Grab the clear-to-ship status
        cts = False
        try:
            if list(
                tr.find(class_="clear_to_ship-column ")
            )[1].attrs['value'] == "1":
                cts = True
        except:
            pass

        # Grab the shipped status (Only appears if true, errors if false)
        shp = False
        try:
            if list(tr.find(class_="shipped-column "))[1].attrs['value'] == "1":
                shp = True
        except:
            pass

        # Grab the customer name
        cust = list(tr.find(class_="customer-column "))[1].get_text()
        cust = strclean(cust)

        # Grab the invoice date
        try:
            idate = tr.find(class_="txn_date-column ").get_text()
                    
            idate = strclean(idate)
            idate = datetime.datetime.strptime(idate, "%a %b %d, %Y")
        except:
            idate = datetime.datetime.today()

        show_detail = True

        # Determine if the line item is in the exception list
        if refnum in ignorelist or cust in ignorelist:
            show_detail = False
            if refnum in ignorelist:
                used_ignorelist.append(refnum)
            else:
                used_ignorelist.append(cust)

        if not cts and \
                (datetime.datetime.today() - idate).days >= 2 and \
                isWholesaler(cust):
            status = "Invoice " + refnum + " may need sales\' approval."
            print("\n" + status)

        elif not cts and not shp and not isWholesaler(cust):
            status = "Invoice " + refnum + " may need its PDF generated."
            print("\n" + status)
        elif not shp and (datetime.datetime.today() - idate).days >= 7:
            status = "Invoice " + refnum + " is approved but has not shipped."
            print("\n" + status)
        else:
            status = ""
            print("\nInvoice " + refnum + " looks good.")
            show_detail = False

        # PRINTS DETAILED INFORMATION ABOUT EACH  ONE
        if show_detail:

            # Adds the error's page number to the list
            if current_page not in issue_pages:
                issue_pages.append(current_page)

            issue_count += 1

            print("\t" + str(cts))
            print("\t" + str(shp))
            print("\t" + cust)
            print("\t" + datetime.datetime.strftime(idate, "%m/%d/%Y"))

            # If there's an error, adds it to the export list
            export_list.append([refnum,
                                cust,
                                datetime.datetime.strftime(idate, "%m/%d/%Y"),
                                cts,
                                shp,
                                status,
                                strclean(str(current_page))])

        counter -= 1


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    main_loop()
    
