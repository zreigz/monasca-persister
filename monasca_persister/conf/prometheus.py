# (C) Copyright 2016-2017 Hewlett Packard Enterprise Development LP
# Copyright 2017 FUJITSU LIMITED
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

from oslo_config import cfg

prometheus_group = cfg.OptGroup(name='prometheus',
                                title='prometheus')
prometheus_opts = [
    cfg.BoolOpt('enabled',
                help='Enable prometheus client',
                default=True),
    cfg.IntOpt('port',
               help='Prometheus client port',
               default=2000),
    cfg.StrOpt('multiproc_dir',
               help='Prometheus multiproc_dir',
               default='/var/prometheus_multiproc_dir'),
]

def register_opts(conf):
    conf.register_group(prometheus_group)
    conf.register_opts(prometheus_opts, prometheus_group)


def list_opts():
    return prometheus_group, prometheus_opts
