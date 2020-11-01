#!/bin/bash

echo "select timestamp, prev_timestamp, DELIVERY_LOW_WH,DELIVERY_HIGH_WH,BACKDELIVERY_LOW_WH,BACKDELIVERY_HIGH_WH,GAS_DM3 from METER_VIEW where timestamp > DATE_SUB(NOW(), INTERVAL 24 HOUR) order by timestamp asc;" | ./mysql.sh -t

echo "Warning: the METER_VIEW tables calculates the WH difference of the TOTAL fields between two records."
echo "If you create a record every 15 minutes, you need to multiply the value by 4 to get to the per hour value of *_WH fields. Same for GAS_DM3, also times 4."

