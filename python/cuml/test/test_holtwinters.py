# Copyright (c) 2019, NVIDIA CORPORATION.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
from cuml.holtwinters.holtwinters import HoltWinters
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import pytest
from sklearn.metrics import r2_score
import cudf

airpassengers = [112, 118, 132, 129, 121, 135, 148, 148, 136, 119, 104, 118,
                 115, 126, 141, 135, 125, 149, 170, 170, 158, 133, 114, 140,
                 145, 150, 178, 163, 172, 178, 199, 199, 184, 162, 146, 166,
                 171, 180, 193, 181, 183, 218, 230, 242, 209, 191, 172, 194,
                 196, 196, 236, 235, 229, 243, 264, 272, 237, 211, 180, 201,
                 204, 188, 235, 227, 234, 264, 302, 293, 259, 229, 203, 229,
                 242, 233, 267, 269, 270, 315, 364, 347, 312, 274, 237, 278,
                 284, 277, 317, 313, 318, 374, 413, 405, 355, 306, 271, 306,
                 315, 301, 356, 348, 355, 422, 465, 467, 404, 347, 305, 336,
                 340, 318, 362, 348, 363, 435, 491, 505, 404, 359, 310, 337]

co2 = [315.42, 316.31, 316.50, 317.56, 318.13, 318.00, 316.39, 314.65, 313.68,
       313.18, 314.66, 315.43, 316.27, 316.81, 317.42, 318.87, 319.87, 319.43,
       318.01, 315.74, 314.00, 313.68, 314.84, 316.03, 316.73, 317.54, 318.38,
       319.31, 320.42, 319.61, 318.42, 316.63, 314.83, 315.16, 315.94, 316.85,
       317.78, 318.40, 319.53, 320.42, 320.85, 320.45, 319.45, 317.25, 316.11,
       315.27, 316.53, 317.53, 318.58, 318.92, 319.70, 321.22, 322.08, 321.31,
       319.58, 317.61, 316.05, 315.83, 316.91, 318.20, 319.41, 320.07, 320.74,
       321.40, 322.06, 321.73, 320.27, 318.54, 316.54, 316.71, 317.53, 318.55,
       319.27, 320.28, 320.73, 321.97, 322.00, 321.71, 321.05, 318.71, 317.66,
       317.14, 318.70, 319.25, 320.46, 321.43, 322.23, 323.54, 323.91, 323.59,
       322.24, 320.20, 318.48, 317.94, 319.63, 320.87, 322.17, 322.34, 322.88,
       324.25, 324.83, 323.93, 322.38, 320.76, 319.10, 319.24, 320.56, 321.80,
       322.40, 322.99, 323.73, 324.86, 325.40, 325.20, 323.98, 321.95, 320.18,
       320.09, 321.16, 322.74]

nybirths = [26.663, 23.598, 26.931, 24.740, 25.806, 24.364, 24.477, 23.901,
            23.175, 23.227, 21.672, 21.870, 21.439, 21.089, 23.709, 21.669,
            21.752, 20.761, 23.479, 23.824, 23.105, 23.110, 21.759, 22.073,
            21.937, 20.035, 23.590, 21.672, 22.222, 22.123, 23.950, 23.504,
            22.238, 23.142, 21.059, 21.573, 21.548, 20.000, 22.424, 20.615,
            21.761, 22.874, 24.104, 23.748, 23.262, 22.907, 21.519, 22.025,
            22.604, 20.894, 24.677, 23.673, 25.320, 23.583, 24.671, 24.454,
            24.122, 24.252, 22.084, 22.991, 23.287, 23.049, 25.076, 24.037,
            24.430, 24.667, 26.451, 25.618, 25.014, 25.110, 22.964, 23.981,
            23.798, 22.270, 24.775, 22.646, 23.988, 24.737, 26.276, 25.816,
            25.210, 25.199, 23.162, 24.707, 24.364, 22.644, 25.565, 24.062,
            25.431, 24.635, 27.009, 26.606, 26.268, 26.462, 25.246, 25.180,
            24.657, 23.304, 26.982, 26.199, 27.210, 26.122, 26.706, 26.878,
            26.152, 26.379, 24.712, 25.688, 24.990, 24.239, 26.721, 23.475,
            24.767, 26.219, 28.361, 28.599, 27.914, 27.784, 25.693, 26.881]


def unit_param(*args, **kwargs):
    return pytest.param(*args, **kwargs, marks=pytest.mark.unit)


def quality_param(*args, **kwargs):
    return pytest.param(*args, **kwargs, marks=pytest.mark.quality)


def stress_param(*args, **kwargs):
    return pytest.param(*args, **kwargs, marks=pytest.mark.stress)


@pytest.mark.parametrize('seasonal', ['ADDITIVE', 'MULTIPLICATIVE'])
@pytest.mark.parametrize('h', [12, 24])
@pytest.mark.parametrize('datatype', [np.float64])
def test_singlets_holtwinters(seasonal, h, datatype):
    global airpassengers
    airpassengers = np.asarray(airpassengers, dtype=datatype)
    train = airpassengers[:-h]
    test = airpassengers[-h:]

    cu_hw = HoltWinters(1, 12, seasonal)
    cu_hw.fit(train)

    sm_hw = ExponentialSmoothing(train, seasonal=seasonal.lower(),
                                 seasonal_periods=12)
    sm_hw = sm_hw.fit()

    cu_pred = cu_hw.predict(0, h)
    sm_pred = sm_hw.forecast(h)

    cu_r2 = r2_score(cu_pred, test)
    sm_r2 = r2_score(sm_pred, test)

    assert (cu_r2 >= sm_r2) or (abs(cu_r2 - sm_r2) < 2e-1)


@pytest.mark.parametrize('seasonal', ['ADDITIVE', 'MULTIPLICATIVE'])
@pytest.mark.parametrize('h', [12, 24])
@pytest.mark.parametrize('datatype', [np.float64])
@pytest.mark.parametrize('input_type', ['cudf', 'np'])
def test_multits_holtwinters(seasonal, h, datatype, input_type):
    global airpassengers, co2
    airpassengers = np.asarray(airpassengers, dtype=datatype)
    co2 = np.asarray(co2, dtype=datatype)

    air_train = airpassengers[:-h]
    air_test = airpassengers[-h:]
    co2_train = co2[:-h]
    co2_test = co2[-h:]
    data = np.asarray([air_train, co2_train], dtype=datatype)

    if input_type == 'cudf':
        data = cudf.DataFrame({i: data[i] for i in range(data.shape[0])})
    cu_hw = HoltWinters(2, 12, seasonal)

    sm_air_hw = ExponentialSmoothing(air_train,
                                     seasonal=seasonal.lower(),
                                     seasonal_periods=12)
    sm_co2_hw = ExponentialSmoothing(co2_train,
                                     seasonal=seasonal.lower(),
                                     seasonal_periods=12)
    cu_hw.fit(data)
    sm_air_hw = sm_air_hw.fit()
    sm_co2_hw = sm_co2_hw.fit()

    cu_air_pred = cu_hw.predict(0, h)
    cu_co2_pred = cu_hw.predict(1, h)
    sm_air_pred = sm_air_hw.forecast(h)
    sm_co2_pred = sm_co2_hw.forecast(h)

    cu_air_r2 = r2_score(cu_air_pred, air_test)
    cu_co2_r2 = r2_score(cu_co2_pred, co2_test)
    sm_air_r2 = r2_score(sm_air_pred, air_test)
    sm_co2_r2 = r2_score(sm_co2_pred, co2_test)

    assert (cu_air_r2 >= sm_air_r2) or (abs(cu_air_r2 - sm_air_r2) < 2e-1)
    assert (cu_co2_r2 >= sm_co2_r2) or (abs(cu_co2_r2 - sm_co2_r2) < 2e-1)

    full_cu_pred = cu_hw.predict(-1, h)
    air_cu_r2 = r2_score(full_cu_pred[0], air_test)
    co2_cu_r2 = r2_score(full_cu_pred[1], co2_test)
    assert (air_cu_r2 >= sm_air_r2) or (abs(air_cu_r2 - sm_air_r2) < 2e-1)
    assert (co2_cu_r2 >= sm_co2_r2) or (abs(co2_cu_r2 - sm_co2_r2) < 2e-1)


@pytest.mark.parametrize('seasonal', ['ADDITIVE', 'MULTIPLICATIVE'])
@pytest.mark.parametrize('h', [12, 24])
@pytest.mark.parametrize('predict', [0, 2])
@pytest.mark.parametrize('datatype', [np.float32, np.float64])
@pytest.mark.parametrize('input_type', ['cudf', 'np', 'cupy'])
@pytest.mark.parametrize('frequency', [7, 12])
@pytest.mark.parametrize('start_periods', [2, 6])
def test_inputs_holtwinters(seasonal, h, predict, datatype, input_type,
                            frequency, start_periods):
    global airpassengers, co2, nybirths
    data = np.asarray([airpassengers, co2, nybirths], dtype=datatype)
    if input_type == 'cudf':
        data = cudf.DataFrame({i: data[i] for i in range(data.shape[0])})
    elif input_type == 'cupy':
        try:
            import cupy as cp
            data = cp.asarray(data)
        except ImportError:
            pytest.skip("CuPy import error -- skipping test.")
    cu_hw = HoltWinters(3, frequency, seasonal, start_periods)
    cu_hw.fit(data)
    cu_hw.predict(predict, h)
