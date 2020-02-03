#!/bin/bash

if [ -t 0 ]
then
   # interactive terminal
   docker exec -ti mysql-meter mysql -uroot -pMyMeter18 meter $*
else
   # non interactive, e.g. shell pipe input
   docker exec -i mysql-meter mysql -uroot -pMyMeter18 meter $*
fi

