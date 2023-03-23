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
import traceback

from metaflow import util
from metaflow._vendor import click
from metaflow.exception import METAFLOW_EXIT_DISALLOW_RETRY, CommandException
from metaflow.metadata.util import sync_local_metadata_from_datastore
from metaflow.metaflow_config import DATASTORE_LOCAL_DIR
from metaflow.mflog import TASK_LOG_SOURCE

from metaflow.metaflow_config import (
    NUVOLARIS_DEFAULT_NAMESPACE
)

from .nuvolaris import Nuvolaris

@click.group()
def cli():
    pass

@cli.group(help="Commands related to Nuvolaris.")
def nuvolaris():
    pass

@nuvolaris.command(
    help="Execute a single task on Nuvolaris. This command calls the top-level step "
    "command inside a Nuvolaris OpenWhisk runtime with the given options. Typically you do not call "
    "this command directly; it is used internally by Metaflow."
)
@click.argument("step-name")
@click.argument("code-package-sha")
@click.argument("code-package-url")
@click.option("--run-id", help="Passed to the top-level 'step'.")
@click.option("--task-id", help="Passed to the top-level 'step'.")
@click.option("--input-paths", help="Passed to the top-level 'step'.")
@click.option("--split-index", help="Passed to the top-level 'step'.")
@click.option("--clone-path", help="Passed to the top-level 'step'.")
@click.option("--clone-run-id", help="Passed to the top-level 'step'.")
@click.option(
    "--tag", multiple=True, default=None, help="Passed to the top-level 'step'."
)
@click.option("--retry-count", default=0, help="Passed to the top-level 'step'.")
@click.option(
    "--max-user-code-retries", default=0, help="Passed to the top-level 'step'."
)
@click.option(
    "--run-time-limit",
    default=5 * 24 * 60 * 60,  # Default is set to 5 days
    help="Run time limit in seconds for Kubernetes pod.",
)
@click.option(
    # Note that ideally we would have liked to use `namespace` rather than
    # `nuv-namespace` but unfortunately, `namespace` is already reserved for
    # Metaflow namespaces.
    "--nuv-namespace",
    default=None,
    help="Namespace for Nuvolaris action.",
)
@click.option("--action", default=None, help="Name of the nuvolaris action to be deployed.")
@click.option("--memory", default=256, help="Memory that nuvolaris should assign in megabytes. Default to 256")
@click.option("--timeout", default=60000, help="Nuvoalris deployed action timeout. Deafult to 60000 milliseconds")
@click.option("--namespace", default=None, help="Passed to the top-level 'step'.")
@click.pass_context
def step(
    ctx,
    step_name,
    code_package_sha,
    code_package_url,
    executable=None,
    nuv_namespace=None,
    run_time_limit=None,
    action=None,
    memory=None,
    timeout=None,
    **kwargs
):
    def echo(msg, stream="stderr", job_id=None):
        msg = util.to_unicode(msg)
        if job_id:
            msg = "[%s] %s" % (job_id, msg)
        ctx.obj.echo_always(msg, err=(stream == sys.stderr))

    node = ctx.obj.graph[step_name]

    # Construct entrypoint CLI
    if executable is None:
        executable = ctx.obj.environment.executable(step_name)

    # Set environment
    env = {}
    env_deco = [deco for deco in node.decorators if deco.name == "environment"]
    if env_deco:
        env = env_deco[0].attributes["vars"]

    # Set input paths.
    input_paths = kwargs.get("input_paths")
    split_vars = None
    if input_paths:
        max_size = 30 * 1024
        split_vars = {
            "METAFLOW_INPUT_PATHS_%d" % (i // max_size): input_paths[i : i + max_size]
            for i in range(0, len(input_paths), max_size)
        }
        kwargs["input_paths"] = "".join("${%s}" % s for s in split_vars.keys())
        env.update(split_vars)

    # Set retry policy.
    retry_count = int(kwargs.get("retry_count", 0))
    retry_deco = [deco for deco in node.decorators if deco.name == "retry"]
    minutes_between_retries = None
    if retry_deco:
        minutes_between_retries = int(
            retry_deco[0].attributes.get("minutes_between_retries", 2)
        )
    if retry_count:
        ctx.obj.echo_always(
            "Sleeping %d minutes before the next retry" % minutes_between_retries
        )
        time.sleep(minutes_between_retries * 60)
        
    step_cli = "{entrypoint} {top_args} step {step} {step_args}".format(
        entrypoint="%s -u %s" % (executable, os.path.basename(sys.argv[0])),
        top_args=" ".join(util.dict_to_cli_options(ctx.parent.parent.params)),
        step=step_name,
        step_args=" ".join(util.dict_to_cli_options(kwargs)),
    )

    # Set log tailing.
    ds = ctx.obj.flow_datastore.get_task_datastore(
        mode="w",
        run_id=kwargs["run_id"],
        step_name=step_name,
        task_id=kwargs["task_id"],
        attempt=int(retry_count),
    )

    stdout_location = ds.get_log_location(TASK_LOG_SOURCE, "stdout")
    stderr_location = ds.get_log_location(TASK_LOG_SOURCE, "stderr")

    def _sync_metadata():
        if ctx.obj.metadata.TYPE == "local":
            sync_local_metadata_from_datastore(
                DATASTORE_LOCAL_DIR,
                ctx.obj.flow_datastore.get_task_datastore(
                    kwargs["run_id"], step_name, kwargs["task_id"]
                ),
            )

    try:
        nuvolaris = Nuvolaris(
            datastore=ctx.obj.flow_datastore,
            metadata=ctx.obj.metadata,
            environment=ctx.obj.environment,
        )
        # Configure and launch Nuvolaris action.
        with ctx.obj.monitor.measure("metaflow.nuvolaris.launch_job"):
            nuvolaris.launch_job(
                flow_name=ctx.obj.flow.name,
                run_id=kwargs["run_id"],
                step_name=step_name,
                task_id=kwargs["task_id"],
                attempt=str(retry_count),
                user=util.get_username(),
                code_package_sha=code_package_sha,
                code_package_url=code_package_url,
                code_package_ds=ctx.obj.flow_datastore.TYPE,
                step_cli=step_cli,
                run_time_limit=run_time_limit,
                namespace=nuv_namespace,
                action=action,
                memory=memory,
                timeout=timeout,
                env=env
            )
    except Exception as e:
        traceback.print_exc(chain=False)
        _sync_metadata()
        sys.exit(METAFLOW_EXIT_DISALLOW_RETRY)
    try:
        nuvolaris.wait(stdout_location, stderr_location, echo=echo)        
    except Exception:        
        # don't retry abnormally terminated tasks
        traceback.print_exc()
        sys.exit(METAFLOW_EXIT_DISALLOW_RETRY)
    finally:        
        _sync_metadata()
