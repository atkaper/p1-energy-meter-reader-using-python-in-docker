Energy Meter Poller / Storage
==============================================================================================================

See also blog post: https://www.kaper.com/software/p1-energy-meter-reader-using-python-in-docker/

This read.py script can be used to read a (Dutch?) energy meter, using it's P1 port and a serial to usb cable.
It is targeted at the DSMR version 5.0 meters, no clue if it works with older types as well. The data which
is read will be inserted in a mysql database for further processing. Make sure you find a proper serial to usb
cable for your meter. Some need an additional resistor in it, and some use inverted levels.

In addition to writing to MYSQL (or instead of), you can now also write your meter data to an influx-db.
Choice can be made at the top of the read.py script, by setting up the proper variables.
Installing an influx database is not described here. It is assumed you already have one, if you want to use this.
In influx command line interface, create the database to be used. For example: "create database meter".

To get this an easy portable installation, I have changed my setup to run in docker containers.

The script runs using python 2.x, not meant for python 3. Will have to upgrade somewhere soon due to
deprecation of python 2.x. For now, the container does build fine (but shows a deprecation warning).

The read.py is a simple run-from-top-to-bottom script, lots of comments to explain it's inner workings,
so hopefully easy to read and change where needed for your usecase. What's missing is nice
error handling. Feel free to add it where needed. For me this works good enough, error means no data inserted.

I am scheduling this script from an embedded cron-tab to run every 15 minutes, but you can run it at any
interval you like. My meter can be polled as fast as once every second (not recommended, it would need
a changed script to just keep reading the data-stream, and not stop after each message).

The list of files / scripts:
--------------------------------------------------------------------------------------------------------------

build.sh                 - use to build the docker container containing python, the read.py, and cron.
create-table.sql         - use to create the meter table.
create-view.sql          - use to create the meter view (it shows the diff between two measurements - multiply
                           by 4 if using 15 minute interval to get to real WH values for fields
                           DELIVERY_LOW/HIGH_WH and BACKDELIVERY_LOW/HIGH_WH!, same for GAS_DM3, also tims 4).
Dockerfile               - the Docker build instruction file.
drop-table.sql           - not to be used ;-)
job.sh                   - executes the cron job (needed to setup an env var before run).
jobs.txt                 - the crontab contents
mysql-server.sh          - script to start a mysql server.
mysql.sh                 - script to start command line interface to mysql server.
phpmyadmin.sh            - scrpit to start a GUI container to browse through the mysql server.
README.txt               - this file.
read.py                  - the python script to read the serial port P1 meter, and store in database.
run-meter-read-once.sh   - for testing; run reading and inserting data just once.
select-last-24hrs.sh     - show results of last 24 hours.
start.sh                 - start the measurement container with the cron job in it.

Used ports:
--------------------------------------------------------------------------------------------------------------
8088 - for phpmyadmin.sh, you can browse to http://192.168.0.120:8088/ to start it (replace 192.168.0.120 by
       your docker server host ip): User: root, password: MyMeter18
3306 - for mysql-server.sh, if you need to change it, find out how ;-) all parts use it from their default.
       should be handled in mysql-server.sh, mysql.sh, phpmyadmin.sh, read.py.
8086 - the influx server port. User: admin, passwod: SomePassword18, ip: 192.168.0.120

Note: I took the shortcut of exposing the database port on the docker host IP, and using that from all
scripts. If you want, you could add a special docker network for it, and inside the containers access the
database by name. I'll leave that as an exercise for yourself ;-)

I have done the same port expose for influx, on my host IP, port 8086, and that's used from the script.

Installing:
--------------------------------------------------------------------------------------------------------------

# Edit phpmyadmin.sh and read.py to put in the ip number of your docker server host.
# Search for 192.168.0.120, and replace by your docker host ip:
vi phpmyadmin.sh read.py

# Edit mysql-server.sh, mysql.sh, and read.py to change the password (optional).
# Seach for: MyMeter18 and replace it by something else:
vi mysql-server.sh mysql.sh read.py

# Edit read.py to setup proper influx connection information, and enable/disable influx or postgres storage as you wish.
# settings: store_in_influx, store_in_postgres, influx_host_port, influx_db, influx_user_password, influx_use_credentials
vi read.py

# build the image:
./build.sh

# start sql server:
./mysql-server.sh

# create table+view:
./mysql.sh < create-table.sql
./mysql.sh < create-view.sql

# fix login password encryption method to prevent error
# "Authentication plugin 'caching_sha2_password' cannot be loaded".
# Note: in next commands, use your new password if you changed it in the scripts:
./mysql.sh

ALTER USER root@localhost IDENTIFIED WITH mysql_native_password BY 'MyMeter18';
ALTER USER root IDENTIFIED WITH mysql_native_password BY 'MyMeter18';
FLUSH PRIVILEGES;
exit;

# start sql GUI (optional), access using http://192.168.0.120:8088/ (replace IP with your host IP).
# User: root, password: MyMeter18 (or your newly chosen password):
./phpmyadmin.sh

# test reading using the read once:
./run-meter-read-once.sh

# if that works fine, start the measurement container:
./start.sh

# and look at the results using:
./select-last-24hrs.sh


Note: in scripts run-meter-read-once.sh and start.sh, there is the /dev/ttyUSB0 device, which will be used to
talk to the P1 meter serial port. If you need to change that to something else, do that in these two scripts
PLUS in the read.py script. Make sure to execute a ./build.sh after this change.

Note: if you use influx, don't forget to create the database using the influxdb command line; "create database meter"


Synology Serial Port Notes:
--------------------------------------------------------------------------------------------------------------

Not related to above stuff, only for people trying to run this on a Synology NAS (I use a DS918+).
The NAS might not know about serial USB adapters normally...
To fix this, try adding a file: /usr/local/etc/rc.d/startup.sh to your NAS,
With this content in it:

insmod /lib/modules/usbserial.ko
insmod /lib/modules/ftdi_sio.ko

And make that file executable:

chmod 755 /usr/local/etc/rc.d/startup.sh

And execute it to get it active (or reboot NAS). This works for FTDI serial converters.
Plug in your serial cable, and check to see if /dev/ttyUSB0 exists (execute: ls -la /dev/ttyUSB0).

If you are unlucky enough to have an unsupported USB serial converter (like a cp210x), you are on your own.
Google for it "cp210x synology". You might end up at something like this:
http://blog.deadcode.net/2009/12/21/compile-kernel-modules-for-firmware-2-2-0944/
Which describes how to compile your own module files. Try it to create the cp210x.ko module.
It needs to be stored in the proper location, something similar to this: /usr/lib/modules/cp210x.ko
Or find an FTDI serial converter, might be easier.


Short notes on adding grafana to the mix:
--------------------------------------------------------------------------------------------------------------

Create a start script "grafana.sh", containing these lines:

#!/bin/bash
docker volume create grafana-storage
docker rm -f grafana
docker run -d -p 3000:3000 --name=grafana -v grafana-storage:/var/lib/grafana grafana/grafana

You can reach it on your servers' IP and port 3000, for example: http://192.168.0.120:3000/

In grafana, set up a datasource pointing to your mysql database.

And create a dashboard with this query (note, I just added 4* to the queries [Nov 1, 2020], as they were per 15 minutes, instead of per hour):

SELECT
  TIMESTAMP AS "time",
  4*GAS_DM3 as GAS_DM3h,
  4*(DELIVERY_LOW_WH + DELIVERY_HIGH_WH) as DELIVERY_WH,
  4*(BACKDELIVERY_LOW_WH + BACKDELIVERY_HIGH_WH) as BACKDELIVERY_WH
FROM METER_VIEW
WHERE
  $__timeFilter(TIMESTAMP)
ORDER BY TIMESTAMP

Set timeline to 24 HR's to see your last day usage.

Note: yes, this graph is running quite slow. At least for my system with lots of records in it.
To get this up-to-performance, we probably need to switch to use influx-db instead of mysql.
I'll try that some other time. For now, my data is stored nicely.

Thijs Kaper, February 2, 2020.


--------------------------------------------------------------------------------------------------------------
Changes: added influx write option.

Thijs Kaper, October 30, 2020.


--------------------------------------------------------------------------------------------------------------
Another addition (just in this readme):

I wanted to use the new influxdb option to insert data every minute, instead of once per 15 minutes.
But, for now, I also do want to keep inserting data in the sql table every 15 minutes also.
So how can we do that? Relatively easy ;-)

Alter the jobs.txt run pattern into this pattern, to run the script every minute:

# run every minute
* * * * * root /job.sh > /proc/1/fd/1 2>/proc/1/fd/2

And alter read.py to have an extra line just below the import's at the top, add this line:

from datetime import datetime as dt

Just below that line, add the next line (I added an empty line before and after it):

minute = dt.now().minute 

And finally, change the "store_in_postgres = True" line into this:

store_in_postgres = (minute == 1 or minute == 16 or minute == 31 or minute == 46)

This will make store_in_postgres only have a "True" value 4 times per hour. While having "store_in_influx = True" for every run.

That's all!

Of course, you can also choose to run both influx and postgres every minute, in that case, just change the jobs.txt file.
Warning: I did not realise before, but the postgres view shows the difference between two measurements, and if you run that
every 15 minutes, the KWH values need to be multiplied by 4 to get to hourly rates! If you run per minute for postgres,
multiply by 60 ;-) But it's perhaps better to switch to influx per minute, and use grafana functions to show the proper data.

----

A note on adding influx enery graphs to your grafana setup:

Create a grafana datsource, pointing to your influxdb, using proper ip/port/credentials and database name.

Add a graph for actual/current power use from the NET:

SELECT mean("value") FROM "ACTUAL_DELIVERY_KW" WHERE $timeFilter GROUP BY time($__interval) fill(null)

And one for back delivery to the NET:

SELECT mean("value") FROM "ACTUAL_BACKDELIVERY_KW" WHERE $timeFilter GROUP BY time($__interval) fill(null)


For graphing separate values, per tarrif, try the next (if you store measurements every 15 minutes, use this graph query):

SELECT (4*derivative(first("value"), 15m)) FROM "TOTAL_DELIVERY_LOW_KWH" WHERE $timeFilter GROUP BY time($__interval) fill(null)

And add 3 more of the same queries, using names: TOTAL_DELIVERY_HIGH_KWH, TOTAL_BACKDELIVERY_HIGH_KWH, TOTAL_BACKDELIVERY_LOW_KWH.
Of course your situation can be different than mine, I have a dual measurement energy meter, and I have solar panels.
You might want to remove (or just not add) the graphs which do not get any data ;-)

In a second graph, I have added this query, to show the voltage:

SELECT mean("value") FROM "VOLTAGE_L1_V" WHERE $timeFilter GROUP BY time($__interval) fill(null)

Voltage does show quite a range, measuring between roughly 219 volts and 231 volts over the last 24 hours.

In a second line, same graph, I added current, and made it use the right hand scale:

SELECT mean("value") FROM "CURRENT_L1_A" WHERE $timeFilter GROUP BY time($__interval) fill(null)

To choose righ hand scale, you can click on the line legend line color under the graph, which gives you a popup
to choose color, and which axis to use. Don't forget to hit save after changing anything.


To connect the dots in your graphs, make sure you set type to lines, and the null value handling to "connected" for the graphs which only show dots otherwise.

Note: I just changed from measuring each 15 minutes to every minute. I wil later find out if I can alter the queries to get rid of the 15m notation in the derivative function.
However, in the short time this is running per minute, it does not really seem to do any big harm for the graph. It sometimes goes a bit over, and sometimes a bit under
the ACTUAL_* graphs. So on average looks the same.

Thijs Kaper, November 1, 2020.


