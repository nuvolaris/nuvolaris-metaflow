

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
# CONFIGURE: Name of this extension; will be shown as part of MF's version number as
#            <mf version>+EXTENSION(<extension version>)
###
__mf_extensions__ = "nuvolaris"

###
# CONFIGURE: Import any subpackages you want to expose directly under metaflow.*.
#            You can make individul objects visible as well as whole submodules
###

# EXAMPLE: Will be accessible as metaflow.my_value
# from ..datatools import nuv_value


###
# CONFIGURE: Override anything present in the __init__.py.
#            This allows you to modify the code base even more invasively. Be careful
#            using this feature as you can potentially cause hard-to-detect breakages.
###
#from .parameter_override import Parameter

###
# CONFIGURE: You can also promote anything present in the metaflow_extensions plugin
#            to also be accessible using metaflow.*. For example, listing something like
#            client.client_extension will make metaflow.client.client_extension alias
#            metaflow_extensions.client.client_extension.
###
__mf_promote_submodules__ = []

import pkg_resources

try:
    __version__ = pkg_resources.get_distribution("metaflow_extension.nuvolaris").version
except:
    # this happens on remote environments since the job package
    # does not have a version
    __version__ = None