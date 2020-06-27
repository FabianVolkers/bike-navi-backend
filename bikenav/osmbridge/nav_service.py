import math
import numpy as np
import json

def deg2rad(deg):
    return deg * (math.pi / 180)

def calculate_distance(a, b):
    # Haversine Formula
    radius = 6371
    dLat = deg2rad(b['lat'] - a['lat'])
    dLon = deg2rad(b['lon'] - a['lon'])
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(deg2rad(a['lat'])) * math.cos(deg2rad(b['lat'])) * math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = radius * c
    return d

def calculate_distance_point_line(a, b, c):
    p1=np.array([a['lat'],a['lon']])
    p2=np.array([b['lat'],b['lon']])
    p3=np.array([c['lat'],c['lon']])
    d=np.cross(p2-p1,p3-p1)/np.linalg.norm(p2-p1)
    return d

def draw_semi_circle(a, b, radius):
    bbox = 3
    return bbox

origin = {
    'lon' : 13.4000813,
    'lat' : 52.5187762,
}
# 52.5187762,13.4000813


destination = {
    'lon' : 13.4049733,
    'lat' : 52.5211922,
}
# 52.5211922,13.4049733


park = {
    'lon' : 13.4069313,
    'lat' : 52.5169372,
}
# 52.5169372,13.4069313

#with open('sample-response.json', 'r'):
'''
[
    13.446895,
    52.493965
],
[
    13.446442,
    52.494301
],
'''
#print(calculate_distance(destination, origin))
print(calculate_distance_point_line(origin, destination, park))