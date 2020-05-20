from __future__ import print_function

import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import httplib2
import os
import datetime
import pytz
import HelperClass as hc
import DBClass as db


class GoogleAPI(object):

    def __init__(self):
        # If modifying these SCOPES, delete your previously saved credentials
        # at ~/.credentials/calendar-python-quickstart.json
        self.SCOPES = 'https://www.googleapis.com/auth/calendar'
        self.CLIENT_SECRET_FILE = '../resources/api/client_secret.json'
        self.TOKEN_PICKLE_FILE = '../resources/api/token.pickle'
        self.APPLICATION_NAME = 'Google Calendar API Python Quickstart'
        self.credentials = self.get_credentials()
        self.service = build('calendar', 'v3', credentials=self.credentials)

    def get_credentials(self):
        print(os.getcwd())
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(self.TOKEN_PICKLE_FILE):
            with open(self.TOKEN_PICKLE_FILE, 'rb') as token:
                creds = pickle.load(token)
                print("Crdentials retrieved from pickle token!")
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.CLIENT_SECRET_FILE, self.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            print("New credentials retrieved!")
        print("Get credentials successful!")
        return creds

    def createEvent(self, summary, location, start, end):

        # Event Details
        event = {
            'summary': summary,
            'location': location,
            'description': 'Created by TechBot',
            'start': {
                'dateTime': start,
                'timeZone': 'Asia/Singapore',
            },
            'end': {
                'dateTime': end,
                'timeZone': 'Asia/Singapore',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 60}
                ],
            },
        }
        event = self.service.events().insert(calendarId='primary', body=event).execute()
        print('Event created: %s' % (event.get('htmlLink')))
        return event.get('id')

    def CreateEventIndex(self, chat_id, summary, location, desc, start_time, end_time, first_week, first_recess_week, recurrence, day, is_ignore_first_event=False):

        # First Instance of the course
        # first_event's start_time
        first_event_start_str = first_week + 'T' + start_time  # to avoid ambiguity
        first_event_start_obj = datetime.datetime.strptime(first_event_start_str, '%Y-%m-%dT%H:%M:%S')
        first_event_start_iso = first_event_start_obj.isoformat()
        first_event_ugly_start = first_event_start_obj.strftime("%Y%m%dT%H%M%S")

        # first_event's end_time
        first_event_end_str = first_week + 'T' + end_time
        first_event_end_obj = datetime.datetime.strptime(first_event_end_str, '%Y-%m-%dT%H:%M:%S')
        first_event_end_iso = first_event_end_obj.isoformat()

        # The recess week
        first_recess_week_str = first_recess_week + 'T' + start_time
        first_recess_week_obj = datetime.datetime.strptime(first_recess_week_str, '%Y-%m-%dT%H:%M:%S')
        
        # Ignore recess week
        ParseObject = hc.StringParseGoogleAPI(start_time)
        ignore_recess_week = ParseObject.ParseDateWeek(first_recess_week_obj)

        # ignore the first event
        ignore_first_event = ""
        # Comma Issues
        if is_ignore_first_event:
            if recurrence != '':
                ignore_first_event = ',' + first_event_ugly_start + ','
            else:
                ignore_first_event = ',' + first_event_ugly_start
        else:
            recurrence = ',' + recurrence
        
        final_week_obj = datetime.datetime.strptime(first_week, '%Y-%m-%d') + datetime.timedelta(days=7 * 13 + 5)
        final_week_str = final_week_obj.strftime("%Y%m%d")
        
        # Event Details
        event = {
            'summary': summary,
            'location': location,
            'description': desc,
            'start': {
                'dateTime': first_event_start_iso,
                'timeZone': 'Asia/Singapore',
            },
            'end': {
                'dateTime': first_event_end_iso,
                'timeZone': 'Asia/Singapore',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 60}
                ],
            },
            'recurrence': [
                "EXDATE;TZID=Asia/Singapore;VALUE=DATE:" + ignore_recess_week + ignore_first_event + recurrence,
                "RRULE:FREQ=WEEKLY;UNTIL=" + final_week_str + ";BYDAY=" + day
            ]
        }

        event = self.service.events().insert(calendarId='primary', body=event).execute()
        print('Event created: %s' % (event.get('htmlLink')))
        event_id = event['id']
        print(event_id)
        course_code, course_type = summary.split(' ')
        db.DB().UpdateCourseCodeEventId(chat_id, course_code, event_id)

    def FreeBusyQuery(self, str_date_start, str_date_end):  # str_date --> yyyy-mm-dd hh:mm
        
        # Parsing date
        iso_date_start = hc.StringParseGoogleAPI(str_date_start).ParseDate()
        iso_date_end = hc.StringParseGoogleAPI(str_date_end).ParseDate()

        # query details
        query = {
            'timeMin': iso_date_start,
            'timeMax': iso_date_end,
            'timeZone': 'Asia/Singapore',
            'items': [
                {
                    'id': 'primary'
                }
            ]
        }
        query = self.service.freebusy().query(body=query).execute()
        return query

    def isFree(self, query):
        return len(query['calendars']['primary']['busy']) == 0
   
    def BusyInfo(self, query):
        busy = query['calendars']['primary']['busy']
        # start_busy = busy[0]['start']
        # end_busy = busy[0]['end']
        return busy

    def deleteEvent(self,InputtedeventID):
        self.service.events().delete(calendarId='primary', eventId=InputtedeventID).execute()

    def getUpcomingEventList(self, num_event):
        """Description: Getting upcoming events
        Return: dictionary
        """
        tz = pytz.timezone('Asia/Singapore')
        now = datetime.datetime.now()
        tz_now = tz.localize(now)
        tz_now_iso = tz_now.isoformat()
        print('Getting the upcomming %d events' %(num_event))
        eventsResult = self.service.events().list(
            calendarId='primary', timeMin=tz_now_iso, maxResults=num_event, singleEvents=True,
            orderBy='startTime').execute()
        events = eventsResult.get('items', [])
        return events
