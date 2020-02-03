docker rm -f python-meter
docker run -d --name python-meter --device=/dev/ttyUSB0 python-meter
