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
import json
import math
import os
import random
import sys
import time
import subprocess

from metaflow.exception import MetaflowException

CLIENT_REFRESH_INTERVAL_SECONDS = 300

class NuvolarisJobException(MetaflowException):
    headline = "Nuvolaris job error"

class NuvolarisApiException(Exception):

    def __init__(self, status, message="An error occurred interacting with Nuvolaris Ai"):
        self.status = status
        self.message = message
        super().__init__(self.message)


# Implements truncated exponential backoff from
# https://cloud.google.com/storage/docs/retry-strategy#exponential-backoff
def nuv_retry(deadline_seconds=60, max_backoff=32):
    def decorator(function):
        from functools import wraps

        @wraps(function)
        def wrapper(*args, **kwargs):
            deadline = time.time() + deadline_seconds
            retry_number = 0

            while True:
                try:
                    result = function(*args, **kwargs)
                    return result
                except NuvolarisApiException as e:
                    if e.status == 404:
                        current_t = time.time()
                        backoff_delay = min(
                            math.pow(2, retry_number) + random.random(), max_backoff
                        )
                        if current_t + backoff_delay < deadline:
                            time.sleep(backoff_delay)
                            retry_number += 1
                            continue  # retry again
                        else:
                            raise
                    else:
                        raise

        return wrapper

    return decorator

class NuvolarisJob(object):
    def __init__(self, client, **kwargs):
        self._client = client
        self._kwargs = kwargs
        self._action_name = self._kwargs["action"]
        self._namespace = self._kwargs["namespace"]

    def create(self):
        # Will deploy the function packages as openwhisk action
        client = self._client.get()
        self._result = client.deploy_action(self._action_name,self._namespace)
        return self

    def execute(self):
        # Call the ow action via the REST api in non blocking fashion
        client = self._client.get()
        result = self._result
        try:
            result = client.execute_action(action_name=self._action_name, command=self._kwargs['command'], environment_variables=self._kwargs["environment_variables"], namespace=self._namespace)           
            response = json.loads(result.text)

            return RunningJob(
                client=self._client,
                name=self._action_name,
                uid=response['activationId'],
                namespace=self._namespace
            )
        except Exception as e:
            raise NuvolarisJobException(
                "Unable to launch Nuvolaris Whisk action.\n %s"%  e
            )

    def step_name(self, step_name):
        self._kwargs["step_name"] = step_name
        return self

    def name(self, name):
        self._kwargs["name"] = name
        return self

    def command(self, command):
        self._kwargs["command"] = command
        return self

    def environment_variable(self, name, value):
        # Never set to None
        if value is None:
            return self
        self._kwargs["environment_variables"] = dict(
            self._kwargs.get("environment_variables", {}), **{name: value}
        )
        return self

    def label(self, name, value):
        self._kwargs["labels"] = dict(self._kwargs.get("labels", {}), **{name: value})
        return self

    def annotation(self, name, value):
        self._kwargs["annotations"] = dict(
            self._kwargs.get("annotations", {}), **{name: value}
        )
        return self

class RunningJob(object):
    def __init__(self, client, name, uid, namespace):
        self._client = client
        self._name = name
        self._id = uid
        self._namespace = namespace

        self._job = self._fetch_job()

        import atexit

        def best_effort_kill():
            try:
                self.kill()
            except:
                pass

        atexit.register(best_effort_kill)

    def __repr__(self):
        return "{}('{}/{}')".format(
            self.__class__.__name__, self._namespace, self._name
        )

    @nuv_retry()
    def _fetch_job(self):
        # Get the activation detail with the complete status of the Action execution
        # The activation API returns a 404 if the activation it is still running
        # it returns onyl the activation_result['response']['result'], which is the direct response of the python function mapped to the action
        client = self._client.get()
        print(f"checking completion of nuvolaris activation {self._id}")
        try:
            response = client.get_activation_detail(activation_id=self._id, namespace=self._namespace)            
            if (response.status_code == 404):
                # 404 means that the activation is not yet finished, i.e the job is still running and OW does not returns any information
                raise NuvolarisApiException(status=404, message="Activation is not completed yet")
            else:
                activation_result = json.loads(response.text)                
                return activation_result['response']['result']
        finally:
            pass            

    def kill(self):
        # TODO Verify it is possible to kill an OW actionm via the REST API
        return self

    @property
    def id(self):
        return "job %s" % self._id

    @property
    def is_done(self):
        def done():
            return self._job and self._job['mf_process_status'] and not "running" == self._job['mf_process_status']

        if not done():
            # If not done, fetch newer status
            self._job = self._fetch_job()
        if done():
            return True
        else:
            return False

    @property
    def status(self):
        if not self.is_done:
            if (self._job and self._job['mf_process_status'] and self._job['mf_process_status'] == "running"):
                return "Job is active"
            else:
                return "Job status is not known"
        return "Job is done"

    @property
    def has_succeeded(self):
        return self.is_done and self._job['mf_process_status'] == "success"

    @property
    def has_failed(self):
        return not self.has_succeeded

    @property
    def is_running(self):
        return not self.is_done and not self.status == "Job is done"

    @property
    def is_waiting(self):
        return not self.is_done and not self.is_running

    @property
    def reason(self):
        if self.is_done:            
                return self._job["mf_process_ret_code"], None            

        return None, None