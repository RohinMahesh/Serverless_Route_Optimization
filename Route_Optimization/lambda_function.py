import base64
import boto3
from geopy import distance
import json
import numpy as np
import os
import uuid

kinesis_client = boto3.client("kinesis")

PRED_STREAM = os.getenv("PRED_STREAM", "route_optim_pred")


class RouteOptimization:
    """Finds optimal path for a round-trip"""

    def __init__(self, locations, coordinates):
        """Input for optimization

        Args:
            locations (List):
                location names
            coordinates (List):
                location geocoordinates
        """
        # Initialize required variables
        self.locations = locations
        self.coordinates = coordinates
        self.indexes = list(range(0, len(self.locations)))
        self.latitude = [x[0] for x in self.coordinates]
        self.longitude = [x[1] for x in self.coordinates]
        self.dict_indexes = dict(zip(self.indexes, self.locations))
        self.dict_locations = dict(zip(self.locations, self.coordinates))
        self.ids = self.indexes[1:]
        self.coordinates_array = np.array([self.latitude, self.longitude]).T[1:]
        self.route = [0]

    def get_route(self):
        """Performs optimization

        Returns:
            route_dict (Dict):
                dictionary containing of optimal route and coordinates
        """
        # Perform optimization
        for x in range(len(self.latitude) - 1):
            previous_lat = self.latitude[self.route[-1]]
            previous_lon = self.longitude[self.route[-1]]

            distances = [
                distance.distance((x[0], x[1]), (previous_lat, previous_lon))
                for x in self.coordinates_array
            ]

            closest_location = np.array(distances).argmin()
            self.route.append(self.ids[closest_location])
            self.ids = np.delete(self.ids, closest_location, axis=0)
            self.coordinates_array = np.delete(
                self.coordinates_array, closest_location, axis=0
            )

        # Prepare and return optimal route and coordinates
        self.route.append(0)
        route_locations = [self.dict_indexes[x] for x in self.route]
        route_coordinates = [self.dict_locations[x] for x in self.dict_locations]
        route_dict = {k: v for k in route_locations for v in route_coordinates}
        return route_dict


def lambda_handler(event, context):
    predictions_events = []

    for record in event["Records"]:
        encoded_data = record["kinesis"]["data"]
        decoded_data = base64.b64decode(encoded_data).decode("utf-8")
        viapoints = json.loads(decoded_data)

        # Get the optimal route
        prediction_id = uuid.uuid4()  # Randomly generated UUID
        locations = viapoints["locations"]
        coordinates = viapoints["coordinates"]
        optimal_route = RouteOptimization(locations, coordinates).get_route()
        prediction_event = {
            "UUID": str(prediction_id),
            "route": optimal_route,
        }

        # Put prediction event in Kinesis Stream
        kinesis_client.put_record(
            StreamName=PRED_STREAM,
            Data=json.dumps(prediction_event),
            PartitionKey=str(prediction_id),
        )

        predictions_events.append(prediction_event)

    return {"predictions": predictions_events}
