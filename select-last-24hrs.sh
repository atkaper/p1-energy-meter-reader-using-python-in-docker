#!/bin/bash
echo "select timestamp, prev_timestamp, DELIVERY_LOW_WH,DELIVERY_HIGH_WH,BACKDELIVERY_LOW_WH,BACKDELIVERY_HIGH_WH,GAS_DM3 from METER_VIEW where timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR) order by timestamp asc;" | ./mysql.sh -t

