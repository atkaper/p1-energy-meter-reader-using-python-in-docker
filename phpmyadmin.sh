
docker rm -f myadmin-meter
docker run --restart=always --name myadmin-meter -d -e PMA_HOST=192.168.0.120 -p 8088:80 phpmyadmin/phpmyadmin

