# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
import os
import sys
import time
import subprocess

from metaflow.exception import MetaflowException
from .nuvolaris_job import NuvolarisJob
from .openwhisk_client import WskCli

CLIENT_REFRESH_INTERVAL_SECONDS = 300

class NuvolarisClientException(MetaflowException):
    headline = "Nuvolaris client error"

class NuvolarisClient(object):
    def __init__(self):        
        self._refresh_client()

    def _refresh_client(self):
        self._client = WskCli()
        self._client_refresh_timestamp = time.time()

    def get(self):
        if (
            time.time() - self._client_refresh_timestamp
            > CLIENT_REFRESH_INTERVAL_SECONDS
        ):
            self._refresh_client()

        return self._client

    def job(self, **kwargs):
        return NuvolarisJob(self, **kwargs)

    def get_action_detail(self, action_name, namespace):
        return self._client.get_action_detail(action_name, namespace)

    def get_activation_detail(self, activation_id, namespace):
        return self._client.get_activation_detail(activation_id, namespace)

    def execute_action(self, action_name, command, namespace):
        return self._client.execute_action(action_name, command, namespace)

