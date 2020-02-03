FROM python:2

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends cron python-serial python-mysqldb
RUN pip install crcmod

COPY read.py /
RUN chmod 755 /read.py

# For some reason, without next env var, the crcmod is not found. Weird...
ENV PYTHONPATH /usr/local/lib/python2.7/site-packages/

COPY jobs.txt /etc/crontab
# lower hardlink back to 1 for cron files (cron does not allow running otherwise)
RUN touch /etc/crontab /etc/cron.*/*

COPY job.sh /
RUN chmod 755 /job.sh

CMD ["cron", "-f"]

