#!/bin/bash 

echo "Ejecutando medicion"

cd /home/pirate/badges_UCN/openbadge-hub-py
docker-compose -f dev_jessie.yml build
docker-compose -f dev_jessie.yml up

