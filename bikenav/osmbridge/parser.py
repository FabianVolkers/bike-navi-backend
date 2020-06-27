import re
import datetime

weekdaysShort = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su', 'PH']
weekdaysFull = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
monthsShort = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                
opening_hours = [
    'Mo-Fr 10:00-19:00; Sa 10:00-15:00', 
    "Mo-Fr 10:00-19:00, Sa 10:00-16:00",
    "Mo-Fr 10:00-19:00; Sa 10:00-16:00; Su,PH off",
    "We 12:00-20:00; Mo, Tu, Th, Fr 11:00-19:00; Sa 12:00-19:00",
    #"Dec-Feb: Mo,We,Sa 09:30-18:00; Mar-Apr: 09:30-18:00; May-Sep: 09:30-20:00; Oct-Nov: 09:30-18:00",
    "Mo-Fr 08:00-13:00,14:00-18:00; Sa 08:00-13:00",
    "Mo 14:00-18:00; Tu-Fr 11:00-14:00, Tu-Th 15:00-18:30, Fr 15:00-18:00; Sa 11:00-15:00",
    "11:00+",
    "Mo-Su 10:00-02:00",
    "24/7",
    "Mo-Su,PH 19:00-03:00+",
    "We-Fr 10:00-19:00, Sa-Mo 10:00-16:00",
]

def parseMonths(opening_hours_string):
    month_regex = r'(' + '|'.join(monthsShort) + r')-('+ '|'.join(monthsShort) + r')'
    month_match = re.findall(month_regex, opening_hours_string)
    if len(month_match) > 0:
        now = datetime.datetime.now()
        for match in month_match:
            start_month = monthsShort.index(match[0]) + 1
            end_month = monthsShort.index(match[1]) + 1
            if start_month <= now.month and now.month <= end_month:
                parseHours(opening_hours_string, match)
                return match
            elif start_month > end_month and start_month <= now.month:
                return match
            else:
                return None
    else:
        return None       

def parseDays(opening_hours_string, *args):
    # Check if there are seasonal opening hours
    # months = parseMonths(opening_hours_string)
    opening_hours = {}
    if opening_hours_string == "24/7":
        opening_hours['display_string'] = "Open 24/7"
    else:
        single_days_regex = r'(?<!-)(' + '|'.join(weekdaysShort) + r')(?!-)'
        single_days_match = re.findall(single_days_regex, opening_hours_string)
        #print(opening_hours_string)
        for match in single_days_match:
            day_regex = match
            day_match = re.search(match, opening_hours_string)
            if day_match is not None:
                hours_dict = parseHours(opening_hours_string, day_match, day_match.group())
                opening_hours.update(hours_dict)
            #time_regex = r'(\d\d:\d\d)'
            #opening_time_match = re.search(time_regex, opening_hours_string[day_match.span()[1]:])
            #closing_time_match = re.search(time_regex, opening_hours_string[opening_time_match.span()[1]:])
            #opening_hours
    
        multi_days_regex = r'(' + '|'.join(weekdaysShort) + r')(?:-)(' + '|'.join(weekdaysShort) + r')'
        multi_days_match = re.findall(multi_days_regex, opening_hours_string)
        for match in multi_days_match:
            days_regex = '(' + match[0] + ')-(' + match[1] + ')'
            days_match = re.search(days_regex, opening_hours_string)
            hours_dict = parseHours(opening_hours_string, days_match, days_match.group()[:2])
            start_day = weekdaysShort.index(match[0])
            end_day = weekdaysShort.index(match[1])
        
            i = start_day
            j = start_day - end_day
            if j < 0:
                j *= -1
            #j += 1
            for weekday in weekdaysShort[:7]:
                weekday_num = weekdaysShort.index(weekday)
                if (start_day <= weekday_num and weekday_num  <= end_day) or ((start_day > end_day) and (weekday_num >= start_day or weekday_num<= end_day)):
                    opening_hours[weekday] = {
                        'open_am' : hours_dict[days_match.group()[:2]]['open_am'],
                        'close_pm' : hours_dict[days_match.group()[:2]]['close_pm']
                    }
                    if 'close_am' in hours_dict[days_match.group()[:2]] and 'open_pm' in hours_dict[days_match.group()[:2]]:
                        opening_hours[weekday]['close_am'] = hours_dict[days_match.group()[:2]]['close_am']
                        opening_hours[weekday]['open_pm'] = hours_dict[days_match.group()[:2]]['open_pm']

        opening_hours['display_string'] = setOpeningHoursString(opening_hours)

    return (opening_hours)

def parseHours(opening_hours_string, day_match, weekday):
    closing_time_match = None
    opening_time = ""
    closing_time = ""
    time_regex = r'(\d\d:\d\d)'
    multi_time_regex = r'(\d\d:\d\d.*?)(?:(' + '|'.join(weekdaysShort) + '))'
    multi_time_match = re.search(multi_time_regex, opening_hours_string[day_match.span()[1]:])
    if multi_time_match is not None:
        #print(multi_time_match)
        all_times = re.findall(time_regex, multi_time_match.string[multi_time_match.span()[0]:multi_time_match.span()[1]])

    if multi_time_match is not None and len(all_times) > 2:
            print('Closing at lunch', all_times)
            day_dict = {
                weekday : {
                    'open_am' : all_times[0],
                    'close_am' : all_times[1],
                    'open_pm' : all_times[2],
                    'close_pm' : all_times[3]
                }
            }
    else:
        opening_time_match = re.search(time_regex, opening_hours_string[day_match.span()[1]:])
        if opening_time_match is not None:
            opening_time = opening_time_match.group()
            closing_time_match = re.search(time_regex, opening_time_match.string[opening_time_match.span()[1]:])
            if closing_time_match is None:
                closing_time_match = re.search(r'\+', opening_hours_string[opening_time_match.span()[1]:])
                if closing_time_match is not None:
                    closing_time = 'Open End'
            else:
                #print('Closing time match:', closing_time_match)
                closing_time = closing_time_match.group()
    
        day_dict = {
            weekday : {
            'open_am' : opening_time,
            'close_am' : "",
            'open_pm': "",
            'close_pm' : closing_time,
            }
        }
    
    return day_dict
            
def setOpeningHoursString(opening_hours):
    hours_display_string = "No opening hours found"
    current_time = datetime.datetime.now()
    current_weekday = weekdaysShort[current_time.weekday()]
    if current_weekday in opening_hours:
        todays_hours = opening_hours[current_weekday]
        open_timestamp = datetime.datetime(current_time.year, current_time.month, current_time.day, int(todays_hours['open_am'][0:2]), int(todays_hours['open_am'][3:5]))
        close_timestamp = datetime.datetime(current_time.year, current_time.month, current_time.day, int(todays_hours['close_pm'][0:2]), int(todays_hours['close_pm'][3:5]))
         

        # If there is a lunch break
        if len(todays_hours['close_am']) > 0:
            close_am_timestamp = datetime.datetime(current_time.year, current_time.month, current_time.day, int(todays_hours['close_am'][0:2]), int(todays_hours['close_am'][3:5]))
            open_pm_timestamp = datetime.datetime(current_time.year, current_time.month, current_time.day, int(todays_hours['open_pm'][0:2]), int(todays_hours['open_pm'][3:5]))
            # If start of lunch break is in the past, set open timestamp to open pm timestamp
            if close_am_timestamp < current_time:
                open_timestamp = open_pm_timestamp
            # If lunch break is in the future, set closing time to lunch break time
            elif close_am_timestamp > current_time:
                close_timestamp = close_am_timestamp
           
        # If closing time after midnight add one day
        if close_timestamp < open_timestamp:
           close_timestamp = close_timestamp + datetime.timedelta(days=1)

        # If current time is in between opening and closing time, 
        if open_timestamp <= current_time and current_time < close_timestamp:
            if close_timestamp - current_time > datetime.timedelta(hours=1):
                hours_display_string = "home.results.selected.open_until-_-" + close_timestamp.strftime('%H:%M')
            # If closing time is less than an hour away change string to closing soon
            elif close_timestamp - current_time <= datetime.timedelta(hours=1):
                hours_display_string = "home.results.selected.closing_soon-_-" + close_timestamp.strftime('%H:%M')
        # If opening time is in the future
        elif open_timestamp > current_time:
            hours_display_string = "home.results.selected.opening_at-_-" + open_timestamp.strftime('%H:%M')
        # If closing time is in the past, list tomorrows opening time
        elif close_timestamp <= current_time:
            tomorrow = current_time + datetime.timedelta(days=1)
            tomorrow_weekday = weekdaysShort[tomorrow.weekday()]
            if tomorrow_weekday in opening_hours:
                tomorrows_hours = opening_hours[tomorrow_weekday]
                open_timestamp = datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, int(tomorrows_hours['open_am'][0:2]), int(tomorrows_hours['open_am'][3:5]))
                hours_display_string = "home.results.selected.opening_tomorrow-_-" + open_timestamp.strftime('%H:%M')

        #print(hours_display_string)
        return hours_display_string
    #else:
        #for weekday in weekdaysShort:
        #    if weekday in opening_hours and
        #'weekdaysShort[current_time.weekday() + 1] in opening_hours:
        
    
    



#for hours_string in opening_hours:
    #print(parseDays(hours_string))            
#egex = r'' + re.escape(weekday) + '\s?-'
#weekday_match = re.findall(re.escape(weekday) + r'\s?-', opening_hours)
#if((weekday_match is not None) and (start_days_range < 0)):
                                
# Store weekday number (Monday == 0, Sunday == 6)
#first_day = j