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
# CONFIGURE: Your company specific configuration options can go in this file.
#            Any settings present here will override the ones present in
#            metaflow_config.py. You can also optionally add additional configuration
#            options.
#
#            The entries below are simple examples
###
NUVOLARIS_DEFAULT_API_URL = "http://localhost:3233/api/v1/namespaces"
NUVOLARIS_DEFAULT_NAMESPACE = "nuvolaris"
NUVOLARIS_DEFAULT_API_USER = "cbd68075-dac2-475e-8c07-d62a30c7e683"
NUVOLARIS_DEFAULT_API_AUTH = "123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP"


# EXAMPLE: Force s3 datastore and the bucket to use (testing nuvolaris based action)
DEFAULT_DATASTORE = "s3"
DATASTORE_SYSROOT_S3 = "s3://mflowtest"

# CUSTOM ACTION IMAGE LAUNCHER
NUVOLARIS_METAFLOW_IMAGE = "ghcr.io/nuvolaris/nuvolaris-metaflow:0.2.1-trinity.22062010"



###
# CONFIGURE: You can override any conda dependencies when a Conda environment is created
###
def get_pinned_conda_libs(python_version):
    return {
        "click>=8.0.0",
        "requests=2.24.0"
        # ...
}