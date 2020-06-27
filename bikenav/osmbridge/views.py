from django.shortcuts import render
from django.http import HttpResponse
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.core import serializers
from django.conf import settings
import json
import requests
import re
import datetime
from xml.etree import ElementTree
from shapely import geometry
#import shapely
from . import nav_service
from . import parser

# Create your views here.
NOMINATIM_URL = "https://nominatim.openstreetmap.org/"
def index(request):
    return HttpResponse("Hello, this is index")


# API views
@api_view(['GET'])
def search(self):
    display_name = self.query_params.get('q', None)
    viewbox = self.query_params.get('viewbox', None).split(',')
    #print(viewbox)
    #bbox = [str(round(float(viewbox[0]),1)),str(round(float(viewbox[1]),1)),str(round(float(viewbox[2]),1)),str(round(float(viewbox[3]),1))]
    #bboxStr = ','.join(bbox)
    bbox = [viewbox[1],viewbox[0],viewbox[3],viewbox[2]]
    bboxStr = ','.join(bbox)
    print(type(bboxStr), bboxStr)
    if(display_name == '26011997'):
        osm_tag = self.query_params.get('key', None)
        osm_tag_value = self.query_params.get('value', None)
        overpass_query = "[out:json][timeout:25];(node(" + bboxStr + ")['" + osm_tag + "'='" + osm_tag_value + "'];way(" + bboxStr + ")['" + osm_tag + "'='" + osm_tag_value + "'];relation(" + bboxStr + ")['" + osm_tag + "'='" + osm_tag_value + "'];);out;"      
        #print(overpass_query)
        overpassURL = 'https://overpass-api.de/api/interpreter'
        response = requests.get(overpassURL, params={'data': overpass_query})
        elements = response.json()['elements']
        search_results = {
            "type" : "FeatureCollection",
            "licence" : "Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright",
            "features" : [],
        }
        for element in elements:
            if('lon' in element and 'lat' in element):
                tmpPoint = geometry.Point(element['lon'], element['lat'])
                bbox = tmpPoint.bounds
            else:
                element['lon'] = 0
                element['lat'] = 0
                bbox = [0,0,0,0]

            resultDict = {
                "type" : "Feature",
                "properties" : {
                    "osm_type" : element['type'],
                    "osm_id" : element['id'],
                },
                "bbox" : bbox,
                "geometry" : {
                    "type" : "Point",
                    "coordinates" : [
                        element['lon'], element['lat']
                    ],
                }
            }
            #print(resultDict['properties'], element['tags'])
            resultDict['properties'].update(element['tags'])
            search_results['features'].append(resultDict)
            #print(resultDict)
        #search_results = {}
        #search_results['features'] = response.json()['elements']
    else:
        '''START OF REGULAR SEARCH SPECIFIC CODE'''
        # DOCKER INSTANCE
        #baseurl = 'http://localhost:7070/search?format=geojson'
        baseurl = NOMINATIM_URL + 'search?format=geojson'
        query = '&q=' + display_name
        limit = '&limit=50'
        viewboxQuery= '&viewbox=' + ','.join(viewbox) + '&bounded=1'
        email = '&email=fabian.volkers%40code.berlin'
        config = {
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        search_response = requests.get(baseurl + query + limit + viewboxQuery + email)
        # if response.status == 200
        search_results = search_response.json()
        # if search_response is empty try public nominatim with 1 sec timeout
        # for feature in features replace properties['icon'] with mdi-icon

        # loop through search_results['features'] to get details
        nodes = []
        ways = []
        relations = []
        result = {}

        for result in search_results['features']:
            # Loop through results and assign to array based on osm type
            if(result['properties']['osm_type'].find('way') > -1):
                ways.append(str(result['properties']['osm_id']))
            elif(result['properties']['osm_type'].find('node') > -1):
                nodes.append(str(result['properties']['osm_id']))
            elif(result['properties']['osm_type'].find('relation') > -1):
                relations.append(str(result['properties']['osm_id']))
    
        # Join List items into comma separated string
        nodesStr = ','.join(nodes)
        waysStr = ','.join(ways)
        relationsStr = ','.join(relations)

        if(len(nodes) > 0):
            nodesStr = 'node(id:' + nodesStr + ');'
        if(len(ways) > 0):
            waysStr = 'way(id:' + waysStr + ');'
        if(len(relations) > 0):
            relationsStr = 'relation(id:' + relationsStr + ');'

        # Build overpass query with all found nodes, ways, and relations and their respective IDs
        overpass_query = "[out:json][timeout:25];(" + nodesStr + waysStr + relationsStr + ");out;"       
        #print(overpass_query)
        overpassURL = 'https://overpass-api.de/api/interpreter'
        response = requests.get(overpassURL, params={'data': overpass_query})

        #print(response.json())
        '''END OF REGULAR SEARCH SPECIFIC CODE'''

    # Loop through features in search results and assign elements from response.json() 
    for result in search_results['features']:
        for element in response.json()['elements']:
            if (result['properties']['osm_type'] == element['type'] and result['properties']['osm_id'] == element['id']):
                result['properties'].update(element['tags'])

                # Set Actual Display Name
                if('name' in result['properties']):
                    result['properties']['display_name'] = result['properties']['name']
                
                
                # Set display address
                if('addr:street' in result['properties']):
                    street = result['properties']['addr:street'] + " "
                else:
                    street = ""

                if('addr:housenumber' in result['properties']):
                    house_number = result['properties']['addr:housenumber'] + " "
                else:
                    house_number = ""

                if('addr:postcode' in result['properties']):
                    postcode = result['properties']['addr:postcode'] + " "
                else:
                    postcode = ""

                if('addr:city' in result['properties']):
                    city = result['properties']['addr:city']
                else:
                    city = ""

                if('name' not in result['properties']):
                    result['properties']['display_name'] = street + house_number
                    result['properties']['display_address'] = postcode + city
                else:
                    result['properties']['display_address'] = street + house_number + postcode + city

                # Parse opening hours
                if('opening_hours' in result['properties']):
                    try:
                        result['properties']['opening_hours_dict'] = parser.parseDays(result['properties']['opening_hours'])
                        if 'display_string' in result['properties']['opening_hours_dict']:
                            result['properties']['opening_hours_string'] = result['properties']['opening_hours_dict']['display_string']
                    except:
                        result['properties']['opening_hours_string'] = result['properties']['opening_hours']
                    
    return(JsonResponse(search_results))

'''
                    weekdaysShort = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']
                    weekdaysFull = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                    opening_hours = result['properties']['opening_hours']
                
                    opening_hours_dict = {
                        'Monday' : {
                            'open': "",
                            'close': ""
                        },
                        'Tuesday' : {
                            'open': "",
                            'close': ""
                        },
                        'Wednesday' : {
                            'open': "",
                            'close': ""
                        },
                        'Thursday' : {
                            'open': "",
                            'close': ""
                        },
                        'Friday' : {
                            'open': "",
                            'close': ""
                        },
                        'Saturday' : {
                            'open': "",
                            'close': ""
                        },
                        'Sunday' : {
                            'open': "",
                            'close': ""
                        },
                    }

                    if(opening_hours == "24/7"):
                        #print('Opening Hours:', opening_hours)
                        result['properties']['opening_hours_string'] = "24/7"
                        opening_hours_dict = {
                            'Monday' : {
                                'open' : '00:00',
                                'close' : '23:59'
                            },
                            'Tuesday' : {
                                'open' : '00:00',
                                'close' : '23:59'
                            },
                            'Wednesday' : {
                                'open' : '00:00',
                                'close' : '23:59'
                            },
                            'Thursday' : {
                                'open' : '00:00',
                                'close' : '23:59'
                            },
                            'Friday' : {
                                'open' : '00:00',
                                'close' : '23:59'
                            },
                            'Saturday' : {
                                'open' : '00:00',
                                'close' : '23:59'
                            },
                            'Sunday' : {
                                'open' : '00:00',
                                'close' : '23:59'
                            },
                        }
                        break
                    else:
                        j = 0
                        start_days_range = -1
                        end_days_range = -1
                        for weekday in weekdaysShort:
'''
''' REBUILD ALGORITHM WITH REGEX'''

                            
'''
                            if(opening_hours.find(weekday + '-') > -1 and start_days_range < 0):
                                start_days_range = j
                            elif(opening_hours.find('-' + weekday) > -1 and start_days_range > -1 and end_days_range < 0):
                                end_days_range = j
                                for j in range(start_days_range, end_days_range + 1):
                                    # Regex to find opening times because to many different varieties. Sometimes 18:00+ meaning open end, sometimes 18:00-23:00, sometimes 18:00 - 23:00
                                    # Time: r^"\d\d:\d\d" 
                                    hoursString = opening_hours[opening_hours.find('-' + weekday)+4:opening_hours.find('-' + weekday)+15]
                                    hoursList = hoursString.split('-')
                                    
                                    #if(hoursList[1] == '00:00'):
                                    #    hoursList[1] = '23:59'

                                    # Add opening hours to dict
                                    opening_hours_dict[weekdaysFull[j]]['open'] = hoursList[0]
                                    opening_hours_dict[weekdaysFull[j]]['close'] = hoursList[1]
                            elif(opening_hours.find(weekday + '-') > -1 and start_days_range > -1 and end_days_range > -1):
                                # If there is multiple entries (e.g. Mo-Th; Fr-Su)
                                start_days_range = j
                                end_days_range = -1
                            elif(opening_hours.find(weekday + '-') < 0 and opening_hours.find(weekday) > -1):
                                hoursString = opening_hours[opening_hours.find('-' + weekday)+4:opening_hours.find('-' + weekday)+15]
                                hoursList = hoursString.split('-')
                                #if(hoursList[1] == '00:00'):
                                #    hoursList[1] = '23:59'
                                if(len(hoursList) > 0):
                                    opening_hours_dict[weekdaysFull[j]]['open'] = hoursList[0]
                                if(len(hoursList) > 1):
                                    opening_hours_dict[weekdaysFull[j]]['close'] = hoursList[1]
                                    
                                #opening_hours_dict[weekdaysFull[j]] = opening_hours[opening_hours.find(weekday)+3:opening_hours.find(weekday)+15]
                            j += 1
                          
                    weekdayNum = datetime.datetime.today().weekday()
                    weekday = weekdaysFull[weekdayNum]
                    currentTime = datetime.datetime.now()

                    openingTimeStr = opening_hours_dict[weekday]['open']
                    openMatch = re.search(r"\d{2}:\d{2}", openingTimeStr)
                    if(openMatch is not None):
                        openingTimeList = openingTimeStr.split(":")
                        openingTimestamp = datetime.datetime(currentTime.year, currentTime.month, currentTime.day, int(openingTimeList[0]), int(openingTimeList[1]))
                        # If opening time is in the future, return Opening at string
                        if(openingTimestamp > currentTime and openingTimestamp.day == currentTime.day):
                            result['properties']['opening_hours_string'] = "Opening at " + openingTimestamp.strftime('%H:%M')
                        elif(openingTimestamp > currentTime and openingTimestamp.day == currentTime.day + 1):
                            result['properties']['opening_hours_string'] = "Opening tomorrow at " + openingTimestamp.strftime('%H:%M')

                    closingTimeStr = opening_hours_dict[weekday]['close']
                    closingTimestamp = None

                    # Check if opening times go past midnight to next day
                    if(opening_hours != "24/7" and (closingTimeStr == "24:00" or closingTimeStr == "00:00" or closingTimeStr == "23:59")):
                        closingTimeStr = "23:59"
                        open = True
                        i = 1
                        while(open):
                            if(weekdayNum + i > 6):
                                i = weekdayNum - 6

                            tmpOpeningTimeStr = opening_hours_dict[weekdaysFull[weekdayNum + i]]['open']
                            tmpClosingTimeStr = opening_hours_dict[weekdaysFull[weekdayNum + i - 1]]['close']
                            
                                
                            #tmpClosingTimestamp = datetime.datetime()
                            print(tmpOpeningTimeStr, tmpClosingTimeStr)
                            if(tmpOpeningTimeStr == "00:00" and (tmpClosingTimeStr == "24:00" or tmpClosingTimeStr == "00:00" or tmpClosingTimeStr == "23:59")):
                                i += 1
                            elif(tmpOpeningTimeStr != "00:00"):
                                open = False
                        
                        if(i > 1):
                            closeMatch = re.search(r"\d{2}:\d{2}", tmpClosingTimeStr)
                            if(closeMatch is not None):
                                closingTimeList = closingTimeStr.split(":")
                                closingTimestamp = datetime.datetime(currentTime.year, currentTime.month, currentTime.day, int(closingTimeList[0]), int(closingTimeList[1]))
                                closingTimestamp = closingTimestamp + datetime.timedelta(days=i)
                                result['properties']['opening_hours_string'] = "Open until " + weekdaysFull[weekdayNum + i - 1] + " at " + closingTimestamp.strftime('%H:%M')

'''
'''
                            openMatch = re.search(r"\d{2}:\d{2}", openingTimeStr)
                            if(openMatch is not None):
                                openingTimeList = openingTimeStr.split(":")
                                openingTimestamp = datetime.datetime(currentTime.year, currentTime.month, currentTime.day, int(openingTimeList[0]), int(openingTimeList[1]))
                        '''
'''
                    closeMatch = re.search(r"\d{2}:\d{2}", closingTimeStr)
                    if(closeMatch is not None):
                        print(type(closeMatch.span()))
                    if(closeMatch is not None and closingTimestamp == None):
                        span = closeMatch.span()
                        closingTimeList = closingTimeStr[span[0]:span[1]].split(':')
                        closingTimestamp = datetime.datetime(currentTime.year, currentTime.month, currentTime.day, int(closingTimeList[0]), int(closingTimeList[1]))
                        # If closing time after midnight, add one day to closing time
                    
                    if(closeMatch is not None and openMatch is not None):
                        if(closingTimestamp < openingTimestamp):
                            closingTimestamp = closingTimestamp + datetime.timedelta(days=1)
                    
                        if(openingTimestamp < currentTime and closingTimestamp > currentTime and closingTimestamp.day == currentTime.day):
                            result['properties']['opening_hours_string'] = "Open until " + closingTimestamp.strftime('%H:%M')
                        elif(closingTimestamp > currentTime and closingTimestamp.day == currentTime.day + 1):
                            result['properties']['opening_hours_string'] = "Open until tomorrow at " + closingTimestamp.strftime('%H:%M')
                        elif(closingTimestamp > currentTime and closingTimestamp.day > currentTime.day + 1):
                            result['properties']['opening_hours_string'] = "Open until " + weekdaysFull[closingTimestamp.weekday()] + " at " + closingTimestamp.strftime('%H:%M')
                        elif(closingTimestamp < currentTime):
                            openingTimeStr = opening_hours_dict[weekdaysFull[weekdayNum + 1]]['open']
                            openMatch = re.search(r"\d{2}:\d{2}", openingTimeStr)
                            if(openMatch is not None):
                                openingTimeList = openingTimeStr.split(":")
                                openingTimestamp = datetime.datetime(currentTime.year, currentTime.month, currentTime.day, int(openingTimeList[0]), int(openingTimeList[1]))
                                openingTimestamp = openingTimestamp + datetime.timedelta(days=1)
                                result['properties']['opening_hours_string'] = "Opening tomorrow at " + openingTimestamp.strftime('%H:%M')
                        #result['properties']['opening_hours_string'] = "Opening at "
                        #print(openingTimestamp, closingTimestamp)

                    result['properties']['opening_hours_dict'] = opening_hours_dict
''' 
       

    


''' All these calls and functions have been refactored to only require a single overpass api response
    i = 0
    for result in search_results['features']:

        

        osm_type = str.upper(result['properties']['osm_type'][:1])
        response = requests.get('http://localhost:7070/reverse?format=geojson&osm_type=' + osm_type + '&osm_id=' + str(result['properties']['osm_id']) + email)
        details = response.json()
        search_results['features'][i] = details['features'][0]

        # Get all feature info from overpass
        response = requests.get('https://overpass-api.de/api/interpreter?data=[out:json];' + result['properties']['osm_type'] + '(' + str(result['properties']['osm_id']) + ');out;')
        search_results['features'][i]['properties'].update(response.json()['elements'][0]['tags'])

        # Set Actual Display Name
        if(search_results['features'][i]['properties']['name'] != None):
            search_results['features'][i]['properties']['display_name'] = search_results['features'][i]['properties']['name']
        
        # Set display address
        if(search_results['features'][i]['properties']['address'] != None):
            if('road' in search_results['features'][i]['properties']['address']):
                road = search_results['features'][i]['properties']['address']['road'] + " "
            else:
                road = ""

            if('house_number' in search_results['features'][i]['properties']['address']):
                house_number = search_results['features'][i]['properties']['address']['house_number'] + " "
            else:
                house_number = ""

            if('postcode' in search_results['features'][i]['properties']['address']):
                postcode = search_results['features'][i]['properties']['address']['postcode'] + " "
            else:
                postcode = ""

            if('city' in search_results['features'][i]['properties']['address']):
                city = search_results['features'][i]['properties']['address']['city']
            elif('town' in search_results['features'][i]['properties']['address']):
                city = search_results['features'][i]['properties']['address']['town']
            elif('state' in search_results['features'][i]['properties']['address']):
                city = search_results['features'][i]['properties']['address']['state']
            else:
                city = ""
        
            search_results['features'][i]['properties']['display_address'] = road + house_number + postcode + city

            # Parse opening hours
            if('opening_hours' in search_results['features'][i]['properties']):
                weekdaysShort = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']
                weekdaysFull = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                opening_hours = search_results['features'][i]['properties']['opening_hours']
                
                display_opening_hours = {
                    'Monday' : {
                        'open': "",
                        'close': ""
                    },
                    'Tuesday' : {
                        'open': "",
                        'close': ""
                    },
                    'Wednesday' : {
                        'open': "",
                        'close': ""
                    },
                    'Thursday' : {
                        'open': "",
                        'close': ""
                    },
                    'Friday' : {
                        'open': "",
                        'close': ""
                    },
                    'Saturday' : {
                        'open': "",
                        'close': ""
                    },
                    'Sunday' : {
                        'open': "",
                        'close': ""
                    },
                }

                if(opening_hours == "24/7"):
                    #print('Opening Hours:', opening_hours)
                    display_opening_hours = {
                        'Monday' : {
                            'open' : '00:00',
                            'close' : '23:59'
                        },
                        'Tuesday' : {
                            'open' : '00:00',
                            'close' : '23:59'
                        },
                        'Wednesday' : {
                            'open' : '00:00',
                            'close' : '23:59'
                        },
                        'Thursday' : {
                            'open' : '00:00',
                            'close' : '23:59'
                        },
                        'Friday' : {
                            'open' : '00:00',
                            'close' : '23:59'
                        },
                        'Saturday' : {
                            'open' : '00:00',
                            'close' : '23:59'
                        },
                        'Sunday' : {
                            'open' : '00:00',
                            'close' : '23:59'
                        },
                }
                else:
                    j = 0
                    start_days_range = -1
                    end_days_range = -1
                    for weekday in weekdaysShort:
                        if(opening_hours.find(weekday + '-') > -1 and start_days_range < 0):
                            start_days_range = j
                        elif(opening_hours.find('-' + weekday) > -1 and start_days_range > -1 and end_days_range < 0):
                            end_days_range = j
                            for j in range(start_days_range, end_days_range + 1):
                                # Regex to find opening times because to many different varieties. Sometimes 18:00+ meaning open end, sometimes 18:00-23:00, sometimes 18:00 - 23:00
                                # Time: r"\d\d:\d\d" 
                                display_opening_hours[weekdaysFull[j]]['open'] = opening_hours[opening_hours.find('-' + weekday)+4:opening_hours.find('-' + weekday)+15]
                                display_opening_hours[weekdaysFull[j]]['close'] = 15
                        elif(opening_hours.find(weekday + '-') > -1 and start_days_range > -1 and end_days_range > -1):
                            # If there is multiple entries (e.g. Mo-Th; Fr-Su)
                            start_days_range = j
                            end_days_range = -1
                        elif(opening_hours.find(weekday + '-') < 0 and opening_hours.find(weekday) > -1):
                            display_opening_hours[weekdaysFull[j]] = opening_hours[opening_hours.find(weekday)+3:opening_hours.find(weekday)+15]
                        j += 1

                print(display_opening_hours)
                search_results['features'][i]['properties']['display_opening_hours'] = display_opening_hours
            
        #search_results['features'][i]['properties']['actual_display_name'] = search_results['features'][i]['properties']['display_name']
        i += 1

    # Build lists for relation, way, node items
    # Send one big query to overpass like so 
    
    (
    way(id:4395330,4391550,4397220);
    node(id:1245,2456543);
    relation(id:12345,65432);
    );
    out;
    
    # Loop through elements of overpass response and assign data to search_results['features‘]


    return JsonResponse(search_results)
    '''


@api_view(['POST'])
def directions(self):
    #print(self.data["origin"])
    origin = self.data['origin']
    destination = self.data['destination']
    #origin = {}
    #destination = {}
    headers = {
            'Authorization' : '5b3ce3597851110001cf6248013a1de706624b69a83c5b9a2dd28edf',
            'Content-Type' : 'application/json'
    }
    routes = {
        'fastest' : {
            'route' : 'fastest',
            'request' : {
                'coordinates' : [
                    origin['geometry']['coordinates'],
                    destination['geometry']['coordinates']
                ],
                'preference' : 'fastest'
            },
            'response' : {}
        },
        'shortest' : {
            'route' : 'shortest',
            'request' : {
                'coordinates' : [
                    origin['geometry']['coordinates'],
                    destination['geometry']['coordinates']
                ],
                'preference' : 'shortest'
            },
            'response' : {}
        },
        'recommended' : {
            'route' : 'recommended',
            'request' : {
                'coordinates' : [
                    origin['geometry']['coordinates'],
                    destination['geometry']['coordinates']
                ],
                'preference' : 'recommended'
            },
            'response' : {}
        },

        'best' : {
            'route' : 'best',
            'request' : {
                'coordinates' : [
                    origin['geometry']['coordinates'],
                    destination['geometry']['coordinates']
                ],
                'preference' : 'recommended'
            },
            'response' : {}
        },
    }
    directionsUrl = 'https://api.openrouteservice.org/v2/directions/cycling-regular/geojson'

    '''
    'options': {
        'avoid_features': 'unpavedroads',
        'profile_params': {
            'weightings' : {
                'green': '1',
                'surface_type': 'cobblestone:flattened',
                'smoothness_type': 'good',
            },
            'restrictions' : {

            },  
        },
        "avoid_polygons": {
            "type": "Polygon",
            "coordinates": [
                [
                    [100.0, 0.0],
                    [101.0, 0.0],
                    [101.0, 1.0],
                    [100.0, 1.0],
                    [100.0, 0.0]
                ]
            ]
        }

    }
    '''
    
    response = requests.post(directionsUrl, data=json.dumps(routes['fastest']['request']), headers=headers)
    routes['fastest']['response'] = response.json()

    response = requests.post(directionsUrl, data=json.dumps(routes['shortest']['request']), headers=headers)
    routes['shortest']['response'] = response.json()

    response = requests.post(directionsUrl, data=json.dumps(routes['recommended']['request']), headers=headers)
    routes['recommended']['response'] = response.json()

    routes['best']['response'] = routes['recommended']['response'].copy()
    routes['best']['response']['metadata']['query']['preference'] = 'best'

    # Draw box around route
    minx = min(origin['geometry']['coordinates'][0], destination['geometry']['coordinates'][0])
    miny = min(origin['geometry']['coordinates'][1], destination['geometry']['coordinates'][1])
    maxx = max(origin['geometry']['coordinates'][0], destination['geometry']['coordinates'][0])
    maxy = max(origin['geometry']['coordinates'][1], destination['geometry']['coordinates'][1])
    # routes['best']['response']['features'][0]['geometry']['coordinates']
    for waypoint in routes['best']['response']['features'][0]['geometry']['coordinates']:
        if(waypoint[0] < minx):
            minx = waypoint[0]
        if(waypoint[1] < miny):
            miny = waypoint[1]
        if(waypoint[0] > maxx):
            maxx = waypoint[0]
        if(waypoint[1] > maxy):
            maxy = waypoint[1]
    #bounding_box = geometry.box(minx, miny, maxx, maxy)
    #print(bounding_box)

    # Build buffer around box to include nearby segments that arent directly in between
    
    buffer = 1/5
    bufferx = (maxx - minx) * buffer
    buffery = (maxy - miny) * buffer
    #print(buffery)
    
    bounding_box = geometry.box(minx - bufferx, miny - buffery, maxx + bufferx, maxy + buffery)
    segments = [
        [13.3571718,52.5146251],
        [13.44374688, 52.4944241],
        [13.3689609, 52.5339110]
    ]
    segmentTiergarten = [13.3571718,52.5146251]
    segmentGoerli = [13.44374688, 52.4944241]
    #segment = [13.4501013, 52.4965252]
    #print(bounding_box.intersects(geometry.Point(segmentGoerli)))
    #print(bounding_box)
    routes['bounding_box'] = {
        'type' : 'FeatureCollection',
        'bbox' : [minx - bufferx, miny - buffery, maxx + bufferx, maxy + buffery],
        'features' : [
            {
                'bbox' : [minx - bufferx, miny - buffery, maxx + bufferx, maxy + buffery],
                'type' : 'Feature',
                'geometry' : geometry.mapping(bounding_box)
            }
        ]
    }

    routes['isochrones'] = {
        'type' : 'FeatureCollection',
        'bbox' : [minx - bufferx, miny - buffery, maxx + bufferx, maxy + buffery],
        'features' : []
    }
    #routes['invalid_isochrones'] = []
    isochronesUrl = 'https://api.openrouteservice.org/v2/isochrones/cycling-regular'
    
    isochrone = {}
    '''To Do'''
    ### Save Isochrone in DB
    ### Query Isochrones (in bbox?) from DB
    ### Iterate over desired segments

    '''For non node segments'''
    #object.representative_point()
    #Returns a cheaply computed point that is guaranteed to be within the geometric object.

    # store all segments to route through in list
    segments_route = []

    for segment in segments:
        if(bounding_box.intersects(geometry.Point(segment))):
            isochronesData = {
                "locations":[
                segment
                    ],
                # range in seconds
                "range":[360]
                }
            response = requests.post(isochronesUrl, data=json.dumps(isochronesData), headers=headers)
            isochrone = geometry.Polygon(response.json()['features'][0]['geometry']['coordinates'][0])
        #coordinates = geometry.Polygon(isochrone)

        #print(coordinates)
        #waypoint = {}
            
            for waypoint in routes['best']['response']['features'][0]['geometry']['coordinates']:
                if(isochrone.intersects(geometry.Point(waypoint))):
                    print(segment, isochrone.intersects(geometry.Point(waypoint)))
                    # send isochrones in response for algorithm visualisation
                    newIsochrone = {
                        'properties' : {
                            'osm_id': 0,
                        },
                        'bbox' : isochrone.bounds,
                        'type' : 'Feature',
                        'geometry' : geometry.mapping(isochrone)
                    }
                    routes['isochrones']['features'].append(newIsochrone)
                    segments_route.append(segment)
                    # reroute recommended as best through segment
                    routes['best']['request']['coordinates'] = [origin['geometry']['coordinates']] + segments_route + [destination['geometry']['coordinates']]
                    
                    #print(routes['best']['request']['coordinates'])
                    response = requests.post(directionsUrl, data=json.dumps(routes['best']['request']), headers=headers)
                    routes['best']['response'] = response.json()
                    routes['best']['response']['metadata']['query']['preference'] = 'best'
                    print('Optimzed Route')
                    break


        # If routes.best goes close by park or other desirable segment, add waypoint and send again
        # Remember first distance and time of recommended so we don't add too much

    return JsonResponse(routes)

@api_view(['POST'])
def addSegment(self):
    newSegment = self.data['segment']

    headers = {
            'Authorization' : '5b3ce3597851110001cf6248013a1de706624b69a83c5b9a2dd28edf',
            'Content-Type' : 'application/json'
    }

    # Get isochrones
    segments = [
        [13.3571718,52.5146251],
    ]
    ''' store isochrones in db on input new segment '''
    # 3, 5, 7 min

    isochronesUrl = 'https://api.openrouteservice.org/v2/isochrones/cycling-regular'
    for segment in segments:
        isochronesData = {
            "locations":[
            segment
                ],
            # range in seconds
            "range":[480]
            }
        response = requests.post(isochronesUrl, data=json.dumps(isochronesData), headers=headers)



'''Overpass API Stuff'''
# Get Overpass xml data
@api_view(['GET'])
def features(self):
    lat = self.query_params.get('lat', None)
    lon = self.query_params.get('lon', None)
    print(lat,lon)
    overpassURL = 'https://overpass-api.de/api/interpreter?data=[out:json][timeout:25];'
    query = 'way(340498994);out;'
    query ="(way(around:50," + lat +',' + lon + ")['bicycle'='yes']" + "(way(around:50," + lat +',' + lon + ")['highway'='cycleway'];);out;"
    query= "way(around:50," + lat +',' + lon + ")['bicycle'!='no']['bicycle'!='use_sidepath']->.bikes_allowed;(way.bikes_allowed['bicycle'='yes'];way.bikes_allowed['highway'='cycleway'];);out;"
    response = requests.get(overpassURL + query)
    #elements = response.json()['elements']
    for element in response.json()['elements']:
        nominatimResponse = requests.get(NOMINATIM_URL + 'reverse?format=geojson&osm_type=' + str(element['type']).upper()[:1] + '&osm_id=' + str(element['id']))
        details = nominatimResponse.json()
        element['geojson'] = details
        #print(element, details)
    #print(elements)
    print(overpassURL + query)
    #tree = ElementTree.fromstring(response.content)
    #xml = response
    res = {
        'check' : 'terminal'
    }
    #for child in tree:
        #print(type(child), child.attrib)
    return JsonResponse(response.json())


# Navigation Services
#####################
'''GET /search/query'''
# autocomplete?
# local nominatim /search
#### return results

# if results
#### for result in results
####### local nominatim /reverse

# else
#### online nominatim with limited calls

'''GET Sunset'''


'''POST /directions'''
# origin 
# destination
# if after sunset avoid lit=no
# POST OpenRouteService/directions
# routes.fastest = POST prefernce: fastest
# routes.shortest = POST prefernce: shortest
# routes.recommended = POST prefernce: recommended

# segements = SELECT * from nice_segments DB
# for segment in segments
#### if routes.recommended goes closeby
####### waypoints.append(segment.waypoint)

# POST OpenRouteService/directions
#### routes.recommended = POST prefernce: recommended --> recursively


# Additional services
#####################
'''GET weather'''
@api_view(['GET'])
def weather(self):
    lat = self.query_params.get('lat', None)
    lon = self.query_params.get('lon', None)
    #lat = 35
    #lon = 139
    weatherUrl = 'https://api.openweathermap.org/data/2.5/weather?lat=' + str(lat) + '&lon=' + str(lon)
    apiKey = '&APPID=8d0fd7c023ef269dccb337777f5762cc'
    response = requests.get(weatherUrl + apiKey)
    weather = response.json()

    sunriseUrl = 'https://api.sunrise-sunset.org/json?lat=' + str(lat) + '&lng=' + str(lon) + '&date=today'
    country = weather['sys']['country']
    sunrise_timestamp = weather['sys']['sunrise']
    sunset_timestamp = weather['sys']['sunset']
    # Add sunrise / sunset times to response
    weather['sys'] = requests.get(sunriseUrl).json()['results']
    # Add removed data back to sys object
    weather['sys']['sunrise_timestamp'] = sunrise_timestamp
    weather['sys']['sunset_timestamp'] = sunset_timestamp
    weather['sys']['country'] = country
    return JsonResponse(weather)

