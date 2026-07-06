#!/bin/bash

nano=${1}

if [ "$(docker inspect -f '{{.State.Running}}' jetson-registry 2>/dev/null)" != "true" ]; then
	if [ "$(docker ps -a -q -f name=jetson-registry)" ]; then
		docker start jetson-registry
	else
		docker run -d -p 5050:5000 --restart=always --name jetson-registry registry:2 || true
	fi
fi
docker buildx build . -t localhost:5050/motor-test:latest --load
docker push localhost:5050/motor-test:latest
ssh nvidia@${nano}.local "docker pull 192.168.100.1:5050/motor-test"
