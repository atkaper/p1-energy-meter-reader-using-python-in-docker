docker rm -f mysql-meter
docker run -d --restart=always --name mysql-meter -p 3306:3306 -v /volume1/docker/electra-meter/mysqldata:/var/lib/mysql -e MYSQL_ROOT_PASSWORD=MyMeter18 -e MYSQL_DATABASE=meter mysql --default-authentication-plugin=mysql_native_password --skip-mysqlx
