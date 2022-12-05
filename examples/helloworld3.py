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

class ForeachFlow(FlowSpec):

    @step
    def start(self):
        self.titles = ['Stranger Things',
                       'House of Cards',
                       'Narcos']
        self.next(self.a, foreach='titles')

    @nuvolaris(namespace="nuvolaris", action="each", memory=256, timeout=120000)
    @step
    def a(self):
        self.title = '%s processed' % self.input
        self.next(self.join)

    @step
    def join(self, inputs):
        self.results = [input.title for input in inputs]
        self.next(self.end)

    @step
    def end(self):
        print('\n'.join(self.results))

if __name__ == '__main__':
    ForeachFlow()