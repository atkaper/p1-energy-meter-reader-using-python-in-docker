
create view METER_VIEW as
SELECT a.*, b.timestamp as prev_timestamp,
       round(COALESCE(a.TOTAL_DELIVERY_LOW_KWH - b.TOTAL_DELIVERY_LOW_KWH, 0) * 1000) as DELIVERY_LOW_WH, 
       round(COALESCE(a.TOTAL_DELIVERY_HIGH_KWH - b.TOTAL_DELIVERY_HIGH_KWH, 0) * 1000) as DELIVERY_HIGH_WH, 
       round(COALESCE(a.TOTAL_BACKDELIVERY_LOW_KWH - b.TOTAL_BACKDELIVERY_LOW_KWH, 0) * 1000) as BACKDELIVERY_LOW_WH, 
       round(COALESCE(a.TOTAL_BACKDELIVERY_HIGH_KWH - b.TOTAL_BACKDELIVERY_HIGH_KWH, 0) * 1000) as BACKDELIVERY_HIGH_WH, 
       round(COALESCE(a.MBUS1_VALUE_GAS_M3 - b.MBUS1_VALUE_GAS_M3, 0) * 1000) as GAS_DM3
FROM METER a 
left join METER b on b.timestamp = (select max(c.timestamp) from METER c where c.timestamp < a.timestamp) 
order by a.timestamp asc;


