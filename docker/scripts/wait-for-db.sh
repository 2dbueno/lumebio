#!/bin/sh

HOST=$1
PORT=$2

echo "Aguardando $HOST:$PORT..."

while ! nc -z $HOST $PORT 2>/dev/null; do
  sleep 1
done

echo "$HOST:$PORT disponível!"
