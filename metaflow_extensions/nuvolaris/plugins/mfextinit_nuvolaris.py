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
###
# CONFIGURE: Define additional plugins here. Your defined plugins will typically fall
#            into one of the categories defined below
###

###
# CONFIGURE: Define any additional CLI-level plugins. As examples, batch and step-functions
#            are two such plugins.
###
def get_plugin_cli():
    from . import nuvolaris_cli
    return [nuvolaris_cli.cli]

###
# CONFIGURE: Flow level decorators; implements FlowDecorator (from decorators.py)
###
FLOW_DECORATORS = []

###
# CONFIGURE: Step level decorators; implements StepDecorator (from decorators.py)
###
from .nuvolaris_decorator import NuvolarisDecorator
STEP_DECORATORS = [NuvolarisDecorator]

###
# CONFIGURE: Environments; implements MetaflowEnvironment
###
ENVIRONMENTS = []

###
# CONFIGURE: Metadata providers; as examples plugins.metadata.local. Implements MetadataProvider
METADATA_PROVIDERS = []

###
# CONFIGURE: Various sidecars
###
SIDECARS = {"name": None}

LOGGING_SIDECARS = {"name": None}

MONITOR_SIDECARS = {"name": None}

###
# CONFIGURE: Your own AWS client provider
#            Class must implement a static method:
#            get_client(module, with_error=False, params={}, role=None) -> (Client, ClientError)
###
AWS_CLIENT_PROVIDERS = []

###
# CONFIGURE: Similar to datatools, you can make visible under metaflow.plugins.* other
#            submodules not referenced in this file
###
__mf_promote_submodules__ = []