## Overview

This project consists of a serverless data science architecture for ingesting real-time streaming data of geocoordinates to find the optimal route that minimizes the distance covered. 

The following AWS services are leveraged:

- ECR: container registry for Docker image used in Lambda 
- CloudWatch: collects real-time logs from Lambda function
- Kinesis: real-time streaming data service for both requests and predictions
- Lambda: serverless function that performs optimization

## Deployment

This project leverages AWS CLI for deployment of this service. The solution is packaged into a virtual environment, containerized using Docker, and registered in ECR. The following components are required to deploy this service:

- Execution role for access to AWS resources. Specifically, for reading items from Kinesis and writing CloudWatch logs
- Policy in IAM for GetRecord, GetRecords, PutRecord and PutRecords 
- Kinesis streams for both the request and service stream
- Lambda function with trigger as the Kinesis request stream and adding key/values for required environment variables

Using the Dockerfile located in the Route_Optimization folder, build the Docker image:

```bash
docker build -t route_optim:v1 .
```

To create and run a Docker container:

```bash
docker run -it --rm \
    -p 8080:8080 \
    -e PRED_STREAM="route_optim_pred" \
    -e AWS_SECRET_KEY_ID=”YOUR_KEY” \
    -e AWS_SECRET_ACCESS_KEY=”YOUR_SECRET”\
    -e AWS_DEFAULT_REGION=”REGION” \
    route_optim:v1

```

Once the Docker image is built, create an ECR repository: 

```bash
aws ecr create-repository –repository-name duration-model
```

Push this Docker image to the repositoryUri provided when creating the ECR repository and create a Lambda function via Container image using the REMOTE_IMAGE:

```bash
REMOTE_URI= “” 
REMOTE_TAG=”v1”
REMOTE_IMAGE=${REMOTE_URI}:${REMOTE_TAG}

LOCAL_IMAGE=”route_optim:v1”
docker tag ${LOCAL_IMAGE} ${REMOTE_IMAGE}
docker push ${REMOTE_IMAGE}
```

## Example Input

```bash
aws kinesis put-record \
    --stream-name ${KINESIS_STREAM_INPUT} \
    --partition-key 1 \
    --data '{
        "locations": ["Chicago", "Atlanta", "Los Angeles", "New York City"], 
        "coordinates": [[41.8781, -87.6298],[33.753746, -84.386330],[34.052235, -118.243683],[40.730610, -73.935242]]
    }'
```
## Reading from Kinesis Stream

```bash
SHARD_ITERATOR=$(aws kinesis \
    get-shard-iterator \
        --shard-id ${SHARD} \
        --shard-iterator-type TRIM_HORIZON \
        --stream-name ${KINESIS_STREAM_OUTPUT} \
        --query 'ShardIterator' \
)

RECORD=$(aws kinesis get-records --shard-iterator $SHARD_ITERATOR)

echo ${RECORD} | jq -r '.Records[0].Data' | base64 --decode
```





