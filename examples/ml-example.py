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
from metaflow import FlowSpec, S3, IncludeFile, step, nuvolaris
from sklearn import datasets
from sklearn.model_selection import train_test_split
from sklearn import linear_model, metrics

from metaflow.metaflow_config import (
    DATASTORE_SYSROOT_S3
)

class TrainingExampleFlow(FlowSpec):

    _s3_dataset_file =  "regression_dataset.txt"
    _s3_tmp_folder =  DATASTORE_SYSROOT_S3 + "/tmp"

    def _train_from__dataset(self, test_size=0.30, random_state=42):
        print(f"using s3 bucket {self._s3_tmp_folder}")
        Xs = []
        Ys = []

        with S3(s3root=self._s3_tmp_folder) as s3:            
            path = s3.get(self._s3_dataset_file).path
            print(f"Downloaded dataset file to {path}")

            with open(path) as f:
                lines = f.readlines()
                for line in lines:
                    x, y = line.split('\t')
                    Xs.append([float(x)])
                    Ys.append(float(y))

        X_train, X_test, y_train, y_test = train_test_split(Xs, Ys, test_size=test_size, random_state=random_state)
        print(len(X_train), len(X_test))
        
        # train a regression model
        reg = linear_model.LinearRegression()
        reg.fit(X_train, y_train)
        print("Coefficient {}, intercept {}".format(reg.coef_, reg.intercept_))
        
        # predict unseeen values and evaluate the model
        y_predicted = reg.predict(X_test)         
        mse = metrics.mean_squared_error(y_test, y_predicted)
        r2 = metrics.r2_score(y_test, y_predicted)
        print('MSE is {}, R2 score is {}'.format(mse, r2))    

        return mse, r2

    @step
    def start(self):
        self.next(self.create_dataset)

    @step
    def create_dataset(self):
        x, y, coef = datasets.make_regression(
            n_samples=1000, # number of samples
            n_features=1, # number of features
            n_informative=1, # number of useful features 
            noise=10, # guassian noise
            coef=True,
            random_state=42)

        dataset = ""
        for _x, _y in zip(x, y):
            dataset = dataset + '{}\t{}\n'.format(_x[0], _y)
                        
        with S3(s3root=self._s3_tmp_folder) as s3:            
            url = s3.put(self._s3_dataset_file, dataset)
            print("Dataset saved at", url)

        self.next(self.a, self.b)        
    
    @nuvolaris(namespace="nuvolaris", action="train_a", timeout=120000, memory=512)
    @step
    def a(self):
        self.mse, self.r2 = self._train_from__dataset(0.10,42)
        self.next(self.join)

    @nuvolaris(namespace="nuvolaris", action="train_b", timeout=120000, memory=512)
    @step
    def b(self):
        self.mse, self.r2 = self._train_from__dataset(0.30,42)
        self.next(self.join)

    @step
    def join(self, inputs):
        print('Step train_a returned MSE {}, R2 score {}'.format(inputs.a.mse, inputs.a.r2))
        print('Step train_b returned MSE {}, R2 score {}'.format(inputs.b.mse, inputs.b.r2))
        self.next(self.end)

    @step
    def end(self):
        pass

if __name__ == '__main__':
    TrainingExampleFlow()