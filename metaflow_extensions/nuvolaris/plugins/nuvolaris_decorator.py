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
import platform
import sys
import json

import requests

from metaflow import util
from metaflow.decorators import StepDecorator
from metaflow.exception import MetaflowException, NuvolarisException
from metaflow.metadata import MetaDatum
from metaflow.metadata.util import sync_local_metadata_to_datastore
from metaflow.metaflow_config import (
    DATASTORE_LOCAL_DIR,
    NUVOLARIS_DEFAULT_NAMESPACE
)
from metaflow.plugins.timeout_decorator import get_run_time_limit_for_task
from metaflow.sidecar import Sidecar

try:
    unicode
except NameError:
    unicode = str
    basestring = str

class NuvolarisDecorator(StepDecorator):
    """
    Specifies that this step should execute on Nuvolaris.

    Parameters
    ----------
    action : str
        Name of the action to be deployed as Nuvolaris OpenWhisk action    
    namespace : str
        Nuvolaris OpenWhisk namespace to use when launching action in Nuvolaris. If
        not specified, the value of `METAFLOW_NUVOLARIS_NAMESPACE` is used
        from Metaflow configuration.        
    """

    name = "nuvolaris"
    defaults = {
        "action":None,
        "namespace": None
    }
    package_url = None
    package_sha = None
    run_time_limit = None

    def __init__(self, attributes=None, statically_defined=False):
        super(NuvolarisDecorator, self).__init__(attributes, statically_defined)

    # Refer https://github.com/Netflix/metaflow/blob/master/docs/lifecycle.png
    def step_init(self, flow, graph, step, decos, environment, flow_datastore, logger):
        # Executing Nuvolaris jobs requires a non-local datastore
        if flow_datastore.TYPE not in ("s3", "azure"):
            raise NuvolarisException(
                "The *@nuvolaris* decorator requires --datastore=s3 or --datastore=azure at the moment."
        )

        if not self.attributes["action"]:
            raise NuvolarisException(
                "Step *{step}* marked for execution on Nuvolaris requires an action name".format(step=step)
            )

        if not self.attributes["namespace"]:
            self.attributes["namespace"] = NUVOLARIS_DEFAULT_NAMESPACE          

        # Set internal state.
        self.logger = logger
        self.environment = environment
        self.step = step
        self.flow_datastore = flow_datastore        

        if any([(deco.name == "batch" or deco.name == "kubernetes") for deco in decos]):
            raise NuvolarisException(
                "Step *{step}* is marked for execution both on AWS Batch/Kubernetes and "
                "Nuvolaris. Please use one or the other.".format(step=step)
            )
        
        for deco in decos:
            if getattr(deco, "IS_PARALLEL", False):
                raise NuvolarisException(
                    "@nuvolaris does not support parallel execution currently."
                )

        # Set run time limit for the OW Action job.
        self.run_time_limit = get_run_time_limit_for_task(decos)
        if self.run_time_limit < 60:
            raise NuvolarisException(
                "The timeout for step *{step}* should be at least 60 seconds for "
                "execution on Nuvolaris.".format(step=step)
            )
        
        self.action = self.attributes["action"]

    def package_init(self, flow, step_name, environment):
        # TODO if required to import some libraries
        pass

    def runtime_init(self, flow, graph, package, run_id):
        # Set some more internal state.
        self.flow = flow
        self.graph = graph
        self.package = package
        self.run_id = run_id

    def runtime_task_created(
        self, task_datastore, task_id, split_index, input_paths, is_cloned, ubf_context
    ):
        # To execute the Nuvolaris job, the job container needs to have
        # access to the code package. We store the package in the datastore
        # which ow is able to download as part of it's entrypoint.
        if not is_cloned:
            self._save_package_once(self.flow_datastore, self.package)

    def runtime_step_cli(
        self, cli_args, retry_count, max_user_code_retries, ubf_context
    ):
        if retry_count <= max_user_code_retries:
            # After all attempts to run the user code have failed, we don't need
            # to execute on Nuvolaris anymore. We can execute possible fallback
            # code locally.
            cli_args.commands = ["nuvolaris", "step"]
            cli_args.command_args.append(self.package_sha)
            cli_args.command_args.append(self.package_url)        

            # --namespace is used to specify Metaflow namespace (a different concept from nuvolaris namespace).
            for k, v in self.attributes.items():
                if k == "namespace":
                    cli_args.command_options["nuv_namespace"] = v
                else:
                    cli_args.command_options[k] = v

            cli_args.command_options["run-time-limit"] = self.run_time_limit        
            cli_args.command_options["action"] = self.action
            cli_args.entrypoint[0] = sys.executable

    def task_pre_step(
        self,
        step_name,
        task_datastore,
        metadata,
        run_id,
        task_id,
        flow,
        graph,
        retry_count,
        max_retries,
        ubf_context,
        inputs,
    ):
        self.metadata = metadata
        self.task_datastore = task_datastore

        if "METAFLOW_RUNTIME_ENVIRONMENT" in os.environ and os.environ["METAFLOW_RUNTIME_ENVIRONMENT"] == "nuvolaris":
            meta = {}

            meta["nuvolaris-action-name"] = self.action
            entries = [
                MetaDatum(field=k, value=v, type=k, tags=[]) for k, v in meta.items()
            ]
            # Register book-keeping metadata for debugging.
            metadata.register_metadata(run_id, step_name, task_id, entries)

            # Start MFLog sidecar to collect task logs.
            self._save_logs_sidecar = Sidecar("save_logs_periodically")
            self._save_logs_sidecar.start()

    def task_finished(
        self, step_name, flow, graph, is_task_ok, retry_count, max_retries
    ):
        # task_finished may run locally if fallback is activated for @catch
        # decorator.
        if "METAFLOW_RUNTIME_ENVIRONMENT" in os.environ and os.environ["METAFLOW_RUNTIME_ENVIRONMENT"] == "nuvolaris":
            # If `local` metadata is configured, we would need to copy task
            # execution metadata from the AWS Batch container to user's
            # local file system after the user code has finished execution.
            # This happens via datastore as a communication bridge.
            if self.metadata.TYPE == "local":
                # Note that the datastore is *always* Amazon S3 (see
                # runtime_task_created function).
                
                sync_local_metadata_to_datastore(
                    DATASTORE_LOCAL_DIR, self.task_datastore
                )
        
        try:
            self._save_logs_sidecar.terminate()
        except:
            # Best effort kill
            pass

    @classmethod
    def _save_package_once(cls, flow_datastore, package):
        if cls.package_url is None:
            cls.package_url, cls.package_sha = flow_datastore.save_data(
                [package.blob], len_hint=1
            )[0]
