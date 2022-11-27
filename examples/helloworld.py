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

from metaflow import FlowSpec, step, nuvolaris

class HelloFlow(FlowSpec):
    """
    A flow where Metaflow prints 'Hi'.
    Run this flow to validate that Metaflow is installed correctly.
    """

    @step
    def start(self):
        """
        This is the 'start' step. All flows must have a step named 'start' that
        is the first step in the flow.
        """
        print("HelloFlow is starting.")
        self.next(self.hello)

    @nuvolaris(namespace="nuvolaris", action="mf")
    @step
    def hello(self):
        """
        A step for metaflow to introduce itself.
        """
        print("Metaflow hello running inside Nuvolaris OW Function step says: Hi!")
        self.next(self.end)

    @step
    def end(self):
        """
        This is the 'end' step. All flows must have an 'end' step, which is the
        last step in the flow.
        """
        print("HelloFlow is all done.")


if __name__ == "__main__":
    HelloFlow()