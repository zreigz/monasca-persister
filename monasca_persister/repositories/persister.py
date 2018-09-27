# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP
# (C) Copyright 2017 SUSE LLC
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
import os
import time

from monasca_common.kafka import consumer
from oslo_log import log
from prometheus_client import multiprocess

from prometheus_client import CollectorRegistry
from prometheus_client import Counter
from prometheus_client import Gauge

LOG = log.getLogger(__name__)


class Persister(object):

    def __init__(self, kafka_conf, zookeeper_conf, repository):

        self._data_points = []

        self._kafka_topic = kafka_conf.topic

        self._batch_size = kafka_conf.batch_size

        self._consumer = consumer.KafkaConsumer(
            kafka_conf.uri,
            zookeeper_conf.uri,
            kafka_conf.zookeeper_path,
            kafka_conf.group_id,
            kafka_conf.topic,
            repartition_callback=self._flush,
            commit_callback=self._flush,
            commit_timeout=kafka_conf.max_wait_time_seconds)

        self.repository = repository()
        self._start_time = time.time()
        self._end_time = 0
        self.registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(self.registry)
        self.message_counter = Counter('monasca_persister_message_count_total',
                                       'total count of messages', ['version'])
        self.message_counter.labels(version='v1.0')
        self.message_counter_per_topic = Counter(
            'monasca_persister_message_count_per_topic',
            'total number of messages processed from one topic', ['topic'])
        self.message_process_rate_gauge = Gauge(
            'monasca_persister_messages_processed_per_sec',
            'messages processed per second from one topic', ['topic'],
            multiprocess_mode='all')

    def _flush(self):
        if not self._data_points:
            return

        try:
            self.repository.write_batch(self._data_points, self._kafka_topic)
            self._end_time = time.time()
            LOG.info("Processed {} messages from topic '{}'".format(
                len(self._data_points), self._kafka_topic))

            self.message_counter.labels(version='v1.0').inc(
                amount=len(self._data_points))
            self.message_counter_per_topic.labels(topic=self._kafka_topic).inc(
                amount=len(self._data_points))
            self.message_process_rate_gauge.labels(
                topic=self._kafka_topic).set(
                len(self._data_points) / (self._end_time - self._start_time))

            self._start_time = self._end_time
            self._data_points = []
            self._consumer.commit()
        except Exception as ex:
            if "partial write: points beyond retention policy dropped" in ex.message:
                LOG.warning("Some points older than retention policy were dropped")
                self._data_points = []
                self._consumer.commit()
            else:
                LOG.exception("Error writing to database: {}"
                              .format(self._data_points))
                raise ex

    def run(self):
        try:
            for raw_message in self._consumer:
                try:
                    message = raw_message[1]
                    data_point = self.repository.process_message(message)
                    self._data_points.append(data_point)
                except Exception:
                    LOG.exception('Error processing message. Message is '
                                  'being dropped. {}'.format(message))

                if len(self._data_points) >= self._batch_size:
                    self._flush()
        except Exception:
            LOG.exception(
                'Persister encountered fatal exception processing '
                'messages. '
                'Shutting down all threads and exiting')
            os._exit(1)
