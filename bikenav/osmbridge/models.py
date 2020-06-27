from django.contrib.gis.db import models

# Create your models here.
class Node(models.Model):
    node_id = models.BigIntegerField()
    node_geom = models.PointField()
    way_id = models.BigIntegerField()

class Way(models.Model):
    way_id = models.BigIntegerField()
    way_geom = models.LineStringField()
    way_tags_osm = models.TextField()
    green = models.CharField()
    vehicle_traffic = models.CharField()
    foot_traffic = models.CharField()
    cycling_score = models.IntegerField()

class User(models.Model):
    user_id = models.IntegerField()
    user_name = models.CharField()
    user_email = models.CharField()
