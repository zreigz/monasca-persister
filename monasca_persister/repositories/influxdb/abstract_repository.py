# (C) Copyright 2016-2017 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import abc
import influxdb
from oslo_config import cfg
import six
import time

from monasca_persister.repositories import abstract_repository
from prometheus_client import CollectorRegistry
from prometheus_client import Gauge
from prometheus_client import multiprocess


@six.add_metaclass(abc.ABCMeta)
class AbstractInfluxdbRepository(abstract_repository.AbstractRepository):

    def __init__(self):
        super(AbstractInfluxdbRepository, self).__init__()
        self.conf = cfg.CONF
        self._influxdb_client = influxdb.InfluxDBClient(
            self.conf.influxdb.ip_address,
            self.conf.influxdb.port,
            self.conf.influxdb.user,
            self.conf.influxdb.password,
            self.conf.influxdb.database_name)
        self.registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(self.registry)
        self.influxdb_write_time_per_message = Gauge(
            'influxdb_write_latency_per_message',
            'seconds per message for influxdb to write', ['topic'],
            multiprocess_mode='all')
        self._start_time = 0
        self._end_time = 0

    def write_batch(self, data_points, kafka_topic):
        self._start_time = time.time()
        self._influxdb_client.write_points(data_points, 'ms', protocol='line')
        self._end_time = time.time()
        self.influxdb_write_time_per_message.labels(topic=kafka_topic).set(
            (self._end_time - self._start_time) / len(data_points))
