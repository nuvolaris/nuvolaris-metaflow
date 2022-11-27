<!---
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
-->
# Nuvolaris metaflow enabled showcase 

This folder contains a minimal implementation of a nuvolaris metaflow extension to showcase the possibility to use Nuvolaris Openwhisk runtime as ML serverless engine!
The project uses the *metaflow-extensions-template* model to implement a @nuvolaris decorator which is inspired by the @kubernetes decorator alaready available in *metaflow* standard distribution

> References:
>* https://metaflow.org
>* https://github.com/Netflix/metaflow
>* https://github.com/Netflix/metaflow-extensions-template

## Scope

The implementation aims to demostrate that using the Nuvolaris *Metaflow* extesion it possible to

* Implement a *@nuvolaris* decorator to run arbitrary python code annotated as a Metaflow step inside a Nuvolaris OpenWhisk runtime
* Scale easily the number of ML Tasks
* Possibility to execute long running job as serverless functions (@TODO)
* Easily customize CPU, MEMORY, TIMEOUT per @step using specific annotation (@TODO)

## Project structure

* examples: contains a couple of Metaflow example defining @nuvolaris decorated step
* metaflow_extension: it contains the source code of the @nuvolaris metaflow aware decorator
* runtime: defines a custom python openwhisk runtime which is used to execute the @nuvolaris decorated @step
* templates: contain the source code of a nuvolaris open whisk python action which capable to execute a metaflow step

## Usage

> Note 1: The @nuvolaris decorator execute a step in a separate runtime and therefore it is not possible to use a local metaflow datastore. Similarly to the @kubernetes or @batch decorfator, using the @nuvolaris decorator requires
> a flow datastore to be enabled to S3 or Azure. For the purpose of the demo an S3 one has been used, to setup the proper S3 bucket reference change the value *DATASTORE_SYSROOT_S3* into the *metaflow_extension/nuvolaris/config*folder

> Note 2: This demo has been developed and tested from inside the nuvolaris development container. To enable the communication with the S3 datastore it is required to setup a default AWS profile with the required credentials. The @nuvolaris decorator uses the default profile to extract and pass to the openwhisk executed action the values of AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY as parameters, as currently it is not possible to pass these values as environment variable to an OpenWhisk runtime prior to the execution.

```sh
# To build and load the custom python3 metaflow enabled openwhisk runtime
task build-and-load

# Annotate the new generated name and updat the NUVOLARIS_METAFLOW_IMAGE under the config folder

# Install the @nuvolaris extension
task install

# Execute a simple call
task run
```

If everything is fine this is the output

```sh
[demo-metaflow:metaflow-demo]$ task run
Metaflow 2.7.14+nuvolaris executing HelloFlow for user:timpefr
Validating your flow...
    The graph looks good!
Running pylint...
    Pylint is happy!
2022-11-24 21:37:15.220 Workflow starting (run-id 1669325834213206):
2022-11-24 21:37:15.384 [1669325834213206/start/1 (pid 68396)] Task is starting.
2022-11-24 21:37:16.816 [1669325834213206/start/1 (pid 68396)] HelloFlow is starting.
2022-11-24 21:37:18.197 [1669325834213206/start/1 (pid 68396)] Task finished successfully.
2022-11-24 21:37:18.619 [1669325834213206/hello/2 (pid 68481)] Task is starting.
2022-11-24 21:37:19.489 [1669325834213206/hello/2 (pid 68481)] checking completion of nuvolaris activation 9f8d02a8c942466e8d02a8c942466e55
2022-11-24 21:37:21.471 [1669325834213206/hello/2 (pid 68481)] checking completion of nuvolaris activation 9f8d02a8c942466e8d02a8c942466e55
2022-11-24 21:37:24.015 [1669325834213206/hello/2 (pid 68481)] checking completion of nuvolaris activation 9f8d02a8c942466e8d02a8c942466e55
2022-11-24 21:37:28.149 [1669325834213206/hello/2 (pid 68481)] checking completion of nuvolaris activation 9f8d02a8c942466e8d02a8c942466e55
2022-11-24 21:37:36.395 [1669325834213206/hello/2 (pid 68481)] checking completion of nuvolaris activation 9f8d02a8c942466e8d02a8c942466e55
2022-11-24 21:37:52.502 [1669325834213206/hello/2 (pid 68481)] checking completion of nuvolaris activation 9f8d02a8c942466e8d02a8c942466e55
2022-11-24 21:37:52.703 [1669325834213206/hello/2 (pid 68481)] [job 9f8d02a8c942466e8d02a8c942466e55] Task status (Job is done)...
2022-11-24 21:37:52.852 [1669325834213206/hello/2 (pid 68481)] tail_logs
2022-11-24 21:37:21.121 [1669325834213206/hello/2 (pid 68481)] [job 9f8d02a8c942466e8d02a8c942466e55] Setting up task environment.
2022-11-24 21:37:21.125 [1669325834213206/hello/2 (pid 68481)] [job 9f8d02a8c942466e8d02a8c942466e55] Downloading code package...
2022-11-24 21:37:32.721 [1669325834213206/hello/2 (pid 68481)] [job 9f8d02a8c942466e8d02a8c942466e55] Code package downloaded.
2022-11-24 21:37:32.745 [1669325834213206/hello/2 (pid 68481)] [job 9f8d02a8c942466e8d02a8c942466e55] Task is starting.
2022-11-24 21:37:38.889 [1669325834213206/hello/2 (pid 68481)] [job 9f8d02a8c942466e8d02a8c942466e55] Metaflow hello running inside Nuvolaris OW Function step says: Hi!
2022-11-24 21:37:53.011 [1669325834213206/hello/2 (pid 68481)] [job 9f8d02a8c942466e8d02a8c942466e55] Task finished with exit code 0.
2022-11-24 21:37:54.634 [1669325834213206/hello/2 (pid 68481)] Task finished successfully.
2022-11-24 21:37:54.991 [1669325834213206/end/3 (pid 69040)] Task is starting.
2022-11-24 21:37:56.188 [1669325834213206/end/3 (pid 69040)] HelloFlow is all done.
2022-11-24 21:37:57.617 [1669325834213206/end/3 (pid 69040)] Task finished successfully.
2022-11-24 21:37:57.857 Done!
[demo-metaflow:metaflow-demo]$ 
```