import json
import gspread
import pandas
from oauth2client.client import SignedJwtAssertionCredentials

json_key = json.load(open('drive-api-creds.json'))
scope = ['https://spreadsheets.google.com/feeds', ]

credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'].encode(), scope)

gc = gspread.authorize(credentials)

sheet = gc.open('MWP Subject Info').sheet1
records = sheet.get_all_records()
subj_info = pandas.DataFrame.from_records(records)
subj_info = subj_info[sheet.row_values(1)] # set column order
subj_info.to_csv('subj_info.csv', index = False)
