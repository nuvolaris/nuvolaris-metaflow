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
#
# Generic @nuvolaris.io action capable of exdcuting a metaflow launching command in a subprocess
#
import subprocess
import json
import os

def main(args):
    if( args['environment_variables']):        
        for k,v in args['environment_variables'].items():
            os.environ[k]=v

    if ( args['command']) :
        print(args['command'])
        cp = subprocess.run(args['command'])
        return { 
                "mf_process_status": cp.returncode == 0 and "success" or "failed",
                "mf_process_ret_code": cp.returncode,
                "mf_process_stderr": cp.stderr,
                "mf_process_stdout": cp.stdout
             }
    else:
        return { "mf_process_status": "failed" }

    
    