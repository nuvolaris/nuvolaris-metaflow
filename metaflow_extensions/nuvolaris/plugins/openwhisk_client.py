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
import subprocess
import hashlib
import json
import requests as req

from metaflow.metaflow_config import (
    NUVOLARIS_DEFAULT_API_URL,
    NUVOLARIS_DEFAULT_API_USER,
    NUVOLARIS_DEFAULT_API_AUTH,
    NUVOLARIS_METAFLOW_OW_KIND
)

class WskCli(object):
        def __init__(self):
            self._headers = {'Content-Type': 'application/json'}
            self._ow_auth = self.get_auth()
            self._nuv_action_template = self.get_mf_nuvolaris_action_template()

        def get_mf_nuvolaris_action_template(self):
            with open("templates/mf_nuvolaris_action.go", "r") as file:
                action_src = file.read()
                file.close()
                return action_src                

        def build_action_url(self,baseurl,action_name, namespace, package=None ):   
            url = f"{baseurl}/{namespace}/actions/"
            if package:
                url += f"{package}/"

            url += action_name    
            return url 

        def build_activations_url(self,baseurl,activation_id, namespace, package=None ):   
            url = f"{baseurl}/{namespace}/activations/{activation_id}"
            if package:
                url += f"{package}/"
            return url 

        def get_auth(self):
            return {'username':NUVOLARIS_DEFAULT_API_USER, 'password':NUVOLARIS_DEFAULT_API_AUTH}
        
        def get_hash(self, action_name,memory, timeout):
            to_hash_data = json.dumps({"name":action_name,"memory":memory,"timeout":timeout,"code":self._nuv_action_template})
            return self.get_action_hash(to_hash_data)
        
        def should_deploy_action(self, action_name, namespace, memory, timeout):
            """ Check if the given action should be deployed or not checking on the
            action annotations hash key
            """
            print(f"checking existence of action {action_name} with memory={memory} and timeout={timeout}")

            try:
                response = self.get_action_detail(action_name, namespace)

                if (response.status_code not in [200]):
                    print(f"action {action_name} does not exists. Forcing deployment")
                    return True
                
                action_data = json.loads(response.text)
                print(f"action {action_name} exists. Checking hash")                

                if "annotations" in action_data:
                    annotations = action_data["annotations"]
                    action_hash = self.get_hash(action_name,memory,timeout)

                    for ann in annotations:
                        if ann["key"] == "hash":
                            current_hash = ann["value"]
                            return not current_hash == action_hash

                    return True    
                else:
                    return True        

                return False
            except:
                print(f"unpredicatable error checking existence of action{action_name}")
                return True
            
        def deploy_action(self, action_name, namespace, memory, timeout):
            print(f"creating action {action_name} with memory={memory} and timeout={timeout}")            
            
            action_hash = self.get_hash(action_name,memory,timeout)
            # Deploy the action using the rest api
            params = {
                    "namespace":namespace,
                    "name":action_name,
                    "exec":{"kind":NUVOLARIS_METAFLOW_OW_KIND,"code":self._nuv_action_template},
                    "limits": {"timeout": timeout,"memory": memory,"logs": 10},
                    "annotations":[{"key":"hash","value":action_hash}]
                    }
            url = self.build_action_url(NUVOLARIS_DEFAULT_API_URL,action_name,namespace)
            response = req.put(f"{url}?overwrite=true", auth=(self._ow_auth['username'],self._ow_auth['password']), headers=self._headers, data=json.dumps(params))

            if (response.status_code not in [200]):
                print(json.dumps(response.text))
            
            return response

        
        # Execute an action in a non blocking fashion passing the metaflow generated command as argument
        def execute_action(self, action_name, command, environment_variables, namespace):            
            params = {"command":command}

            if(environment_variables):
                params["environment_variables"]=environment_variables

            url = self.build_action_url(NUVOLARIS_DEFAULT_API_URL,action_name,namespace)
            return req.post(url, auth=(self._ow_auth['username'],self._ow_auth['password']), headers=self._headers, data=json.dumps(params))

        # Fetch the detail about the action
        def get_action_detail(self, action_name, namespace):
            url = self.build_action_url(NUVOLARIS_DEFAULT_API_URL,action_name,namespace)
            return req.get(url, auth=(self._ow_auth['username'],self._ow_auth['password']))            

        # Fetch the detail about the activation id
        def get_activation_detail(self, activation_id, namespace):
            url = self.build_activations_url(NUVOLARIS_DEFAULT_API_URL,activation_id, namespace)
            return req.get(url, auth=(self._ow_auth['username'],self._ow_auth['password']))
        
        def get_action_hash(self,data:str):
            """ Suitable helper method to calculate an HASH (by default MD5) from string data
            :param data
            """
            h = hashlib.sha256()
            h.update(bytes(data, 'utf-8'))
            digest = h.hexdigest()
            return digest