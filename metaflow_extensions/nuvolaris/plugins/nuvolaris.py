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
import shlex
import time
import boto3

from metaflow import current, util
from metaflow.exception import MetaflowException
from metaflow.metaflow_config import (
    BATCH_METADATA_SERVICE_HEADERS,
    BATCH_METADATA_SERVICE_URL,
    DATASTORE_CARD_S3ROOT,
    DATASTORE_SYSROOT_S3,
    DATATOOLS_S3ROOT,
    DEFAULT_AWS_CLIENT_PROVIDER,
    DEFAULT_METADATA,
    KUBERNETES_SANDBOX_INIT_SCRIPT,
    S3_ENDPOINT_URL,
    AZURE_STORAGE_BLOB_SERVICE_ENDPOINT,
    DATASTORE_SYSROOT_AZURE,
    DATASTORE_CARD_AZUREROOT
)

from metaflow.mflog import (
    BASH_SAVE_LOGS,
    BASH_MFLOG,
    bash_capture_logs,
    export_mflog_env_vars,
    tail_logs,
    get_log_tailer,
)

from .nuvolaris_environment import NuvolarisEnvironment
from .nuvolaris_client import NuvolarisClient

# Redirect structured logs to $PWD/.logs/
LOGS_DIR = "$PWD/.logs"
STDOUT_FILE = "mflog_stdout"
STDERR_FILE = "mflog_stderr"
STDOUT_PATH = os.path.join(LOGS_DIR, STDOUT_FILE)
STDERR_PATH = os.path.join(LOGS_DIR, STDERR_FILE)

class NuvolarisException(MetaflowException):
    headline = "Nuvolaris error"

class NuvolarisKilledException(MetaflowException):
    headline = "Nuvolaris Batch job killed"

class Nuvolaris(object):
    def __init__(
        self,
        datastore,
        metadata,
        environment,
    ):
        self._datastore = datastore
        self._metadata = metadata
        self._environment = environment

      

    def _command(
        self,
        flow_name,
        run_id,
        step_name,
        task_id,
        attempt,
        code_package_url,
        step_cmds,
    ):
        nuv_env = NuvolarisEnvironment()
        mflog_expr = export_mflog_env_vars(
            flow_name=flow_name,
            run_id=run_id,
            step_name=step_name,
            task_id=task_id,
            retry_count=attempt,
            datastore_type=self._datastore.TYPE,
            stdout_path=STDOUT_PATH,
            stderr_path=STDERR_PATH,
        )
        
        # TODO We need to handle the package setup but we use a custom implementation to skip required dependecies
        init_cmds = nuv_env.get_package_commands(
            code_package_url, self._datastore.TYPE
        )
        init_expr = " && ".join(init_cmds)
        #init_expr = " && "
        step_expr = bash_capture_logs(
            " && ".join(
                self._environment.bootstrap_commands(step_name, self._datastore.TYPE)
                + step_cmds
            )
        )

        # Construct an entry point that
        # 1) initializes the mflog environment (mflog_expr)
        # 2) bootstraps a metaflow environment (init_expr)
        # 3) executes a task (step_expr)

        # The `true` command is to make sure that the generated command
        # plays well with docker containers which have entrypoint set as
        # eval $@
        cmd_str = "true && mkdir -p %s && %s && %s && %s; " % (
            LOGS_DIR,
            mflog_expr,
            init_expr,
            step_expr,
        )
        # After the task has finished, we save its exit code (fail/success)
        # and persist the final logs. The whole entrypoint should exit
        # with the exit code (c) of the task.
        #
        # Note that if step_expr OOMs, this tail expression is never executed.
        # We lose the last logs in this scenario.
        #
        # TODO: Capture hard exit logs in Kubernetes.
        cmd_str += "c=$?; %s; exit $c" % BASH_SAVE_LOGS
        # For supporting sandboxes, ensure that a custom script is executed before
        # anything else is executed. The script is passed in as an env var.
        cmd_str = (
            '${METAFLOW_INIT_SCRIPT:+eval \\"${METAFLOW_INIT_SCRIPT}\\"} && %s'
            % cmd_str
        )
        return shlex.split('bash -c "%s"' % cmd_str)

    def launch_job(self, **kwargs):
        self._job = self.create_job(**kwargs).execute()

    def create_job(
        self,
        flow_name,
        run_id,
        step_name,
        task_id,
        attempt,
        user,
        code_package_sha,
        code_package_url,
        code_package_ds,
        step_cli,
        run_time_limit,
        namespace=None,
        action=None,      
        env={},
    ):

        job = (
            NuvolarisClient()
            .job(
                generate_name="t-",
                namespace=namespace,
                action=action,
                command=self._command(
                    flow_name=flow_name,
                    run_id=run_id,
                    step_name=step_name,
                    task_id=task_id,
                    attempt=attempt,
                    code_package_url=code_package_url,
                    step_cmds=[step_cli],
                ),
                timeout_in_seconds=run_time_limit,
                # Retries are handled by Metaflow runtime
                retries=0,
                step_name=step_name
            )
            .environment_variable("METAFLOW_CODE_SHA", code_package_sha)
            .environment_variable("METAFLOW_CODE_URL", code_package_url)
            .environment_variable("METAFLOW_CODE_DS", code_package_ds)
            .environment_variable("METAFLOW_USER", user)
            .environment_variable("METAFLOW_SERVICE_URL", BATCH_METADATA_SERVICE_URL)
            .environment_variable(
                "METAFLOW_SERVICE_HEADERS",
                json.dumps(BATCH_METADATA_SERVICE_HEADERS),
            )
            .environment_variable("METAFLOW_DATASTORE_SYSROOT_S3", DATASTORE_SYSROOT_S3)
            .environment_variable("METAFLOW_DATATOOLS_S3ROOT", DATATOOLS_S3ROOT)
            .environment_variable("METAFLOW_DEFAULT_DATASTORE", self._datastore.TYPE)
            .environment_variable("METAFLOW_DEFAULT_METADATA", DEFAULT_METADATA)
            .environment_variable("METAFLOW_RUNTIME_ENVIRONMENT", "nuvolaris")
            .environment_variable("METAFLOW_CARD_S3ROOT", DATASTORE_CARD_S3ROOT)
            .environment_variable(
                "METAFLOW_DEFAULT_AWS_CLIENT_PROVIDER", DEFAULT_AWS_CLIENT_PROVIDER
            )
            .environment_variable("METAFLOW_S3_ENDPOINT_URL", S3_ENDPOINT_URL)
            .environment_variable(
                "METAFLOW_AZURE_STORAGE_BLOB_SERVICE_ENDPOINT",AZURE_STORAGE_BLOB_SERVICE_ENDPOINT,
            )
            .environment_variable(
                "METAFLOW_DATASTORE_SYSROOT_AZURE", DATASTORE_SYSROOT_AZURE
            )
            .environment_variable("METAFLOW_CARD_AZUREROOT", DATASTORE_CARD_AZUREROOT)
            # support Metaflow sandboxes
            .environment_variable(
                "METAFLOW_INIT_SCRIPT", KUBERNETES_SANDBOX_INIT_SCRIPT
            ) 
            .environment_variable(
                "METAFLOW_DEBUG_S3CLIENT", "1"
            )  
            .environment_variable(
                "METAFLOW_DEBUG_SUBCOMMAND", "1"
            )
            .environment_variable(
                "METAFLOW_DEBUG_SIDECAR", "1"
            )                                            
            # Skip setting METAFLOW_DATASTORE_SYSROOT_LOCAL because metadata sync
            # between the local user instance and the remote Nuvolaris Kubernetes pod
            # assumes metadata is stored in DATASTORE_LOCAL_DIR on the Nuvolaris Kubernetes
            # pod; this happens when METAFLOW_DATASTORE_SYSROOT_LOCAL is NOT set (
            # see get_datastore_root_from_config in datastore/local.py).
        )

        for name, value in env.items():
            job.environment_variable(name, value)

        # Pass AWS credentials as environment_variable
        session = boto3.Session(profile_name="default")
        credentials = session.get_credentials()
        job.environment_variable("AWS_ACCESS_KEY_ID", credentials.access_key)
        job.environment_variable("AWS_SECRET_ACCESS_KEY", credentials.secret_key)

        annotations = {
            "metaflow/user": user,
            "metaflow/flow_name": flow_name,
        }
        if current.get("project_name"):
            annotations.update(
                {
                    "metaflow/project_name": current.project_name,
                    "metaflow/branch_name": current.branch_name,
                    "metaflow/project_flow_name": current.project_flow_name,
                }
            )

        for name, value in annotations.items():
            job.annotation(name, value)

        (
            job.annotation("metaflow/run_id", run_id)
            .annotation("metaflow/step_name", step_name)
            .annotation("metaflow/task_id", task_id)
            .annotation("metaflow/attempt", attempt)
            .label("app.kubernetes.io/name", "metaflow-task")
            .label("app.kubernetes.io/part-of", "metaflow")
        )

        return job.create()

    def wait(self, stdout_location, stderr_location, echo=None):
        def update_delay(secs_since_start):
            # this sigmoid function reaches
            # - 0.1 after 11 minutes
            # - 0.5 after 15 minutes
            # - 1.0 after 23 minutes
            # in other words, the user will see very frequent updates
            # during the first 10 minutes
            sigmoid = 1.0 / (1.0 + math.exp(-0.01 * secs_since_start + 9.0))
            return 0.5 + sigmoid * 30.0

        def wait_for_launch(job):
            status = job.status
            echo(
                "Task status (%s)..." % status,
                "stderr",
                job_id=job.id,
            )
            t = time.time()
            start_time = time.time()
            while job.is_waiting:
                new_status = job.status
                if status != new_status or (time.time() - t) > 30:
                    status = new_status
                    echo(
                        "Task is starting (%s)..." % status,
                        "stderr",
                        job_id=job.id,
                    )
                    t = time.time()
                time.sleep(update_delay(time.time() - start_time))

        prefix = b"[%s] " % util.to_bytes(self._job.id)
        stdout_tail = get_log_tailer(stdout_location, self._datastore.TYPE)
        stderr_tail = get_log_tailer(stderr_location, self._datastore.TYPE)

        # 1) Loop until the job has started
        wait_for_launch(self._job)

        # 2) Tail logs until the job has finished
        echo("tail_logs")
        tail_logs(
            prefix=prefix,
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
            echo=echo,
            has_log_updates=lambda: self._job.is_running,
        )
        # 3) Fetch remaining logs
        if self._job.has_failed:
            exit_code, reason = self._job.reason
            msg = next(
                msg
                for msg in [
                    reason,
                    "Task crashed",
                ]
                if msg is not None
            )
            if exit_code:
                if int(exit_code) == 139:
                    raise NuvolarisException("Task failed with a segmentation fault.")
                if int(exit_code) == 137:
                    raise NuvolarisException(
                        "Task ran out of memory. "
                        "Increase the available memory by specifying "
                        "@resource(memory=...) for the step. "
                    )
                if int(exit_code) == 134:
                    raise NuvolarisException("%s (exit code %s)" % (msg, exit_code))
                else:
                    msg = "%s (exit code %s)" % (msg, exit_code)
            raise NuvolarisException(
                "%s. This could be a transient error. Use @retry to retry." % msg
            )

        exit_code, _ = self._job.reason
        echo(
            "Task finished with exit code %s." % exit_code,
            "stderr",
            job_id=self._job.id,
        ) 
