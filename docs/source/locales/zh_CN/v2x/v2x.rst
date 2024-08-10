V2X 通信信道模型计算指南
==========================

TSHub 中实现了 V2X（Vehicle-to-Everything）通信中的信道模型计算方法。V2X 通信包括 V2I（Vehicle-to-Infrastructure）和 V2V（Vehicle-to-Vehicle）两种情况，它们在路径损耗的计算上有所不同。计算流程主要包括：

1. 路径损耗（Path Loss）
2. 遮蔽效应（Shadowing）
3. 接收端功率（Received Power）
4. 信噪比（Signal-to-Noise Ratio, SNR）的计算。

通过这些步骤，我们可以进一步评估包括数据包丢失率（Packet Loss）、噪声（Noise）和通信容量（Capacity）等通信性能指标。

路径损耗计算
--------------

自由空间路径损耗 (FSPL)
^^^^^^^^^^^^^^^^^^^^^^^^

在 V2I 通信中，通常采用自由空间路径损耗模型来估计信号强度的减少。该模型适用于信号在没有障碍物阻挡的直线路径上传播时的情况。计算公式如下：

.. math::
   FSPL(dB) = 20 \log_{10}(d) + 20 \log_{10}(f) + 20 \log_{10}\left(\frac{4 \pi}{c}\right)

其中，:math:`d` 是发射机和接收机之间的距离，:math:`f` 是信号频率，默认为 2.4 GHz，:math:`c` 是光速，约为 :math:`3 \times 10^8` 米/秒。

WINNER II Channel Model
^^^^^^^^^^^^^^^^^^^^^^^

对于 V2V 通信，我们采用 WINNER II Channel 模型来描述车辆间的路径损耗。这个模型考虑了车辆间复杂的城市环境和多路径效应，更适合描述 V2V 场景下的信号传播。详细介绍可以参考 `WINNER II Channel <https://ww2.mathworks.cn/help/comm/ug/winner-ii-channel.html>`_。

遮蔽效应 (Shadowing)
----------------------

无线信号在传播过程中会遇到各种障碍物，如建筑物、树木等，这些障碍物会导致信号功率的衰减，这种现象称为遮蔽效应。在 V2X 通信中，由于车辆的移动性，遮蔽效应尤其重要。遮蔽效应可以用一个对数正态分布的随机变量来建模，其数学表示如下：

.. math::
   S(dB) = X_{\sigma} = \sigma \cdot Z

:math:`Z` 是一个标准正态分布随机变量，:math:`\sigma` 是遮蔽效应的标准差。遮蔽效应的相关性随着距离变化而减小，可以通过以下指数衰减模型来描述：

.. math::
   \rho(\Delta d) = e^{-\frac{|\Delta d|}{d_{corr}}}

:math:`\Delta d` 是两点之间的距离变化，:math:`d_{corr}` 是 decorrelation distance。如果已知某点的遮蔽值 :math:`S_1`，在距离 :math:`\Delta d` 处的另一点的遮蔽值 :math:`S_2` 可以通过以下公式计算：

.. math::
   S_2 = \rho(\Delta d) \cdot S_1 + \sqrt{1 - \rho(\Delta d)^2} \cdot \sigma \cdot Z

接收端功率 (Received Power)
------------------------------

接收端功率指的是在考虑路径损耗、天线增益和噪声系数后，接收器处的信号功率。计算公式如下：

.. math::
   P_{rx}(dBm) = P_{tx}(dBm) - L_{path}(dB) - S(dB) - L_{noise}(dB) + G_{v}(dBi) + G_{b}(dBi) - NF_{b}(dB)

其中，:math:`P_{tx}(dBm)` 是发射功率，:math:`L_{path}(dB)` 是路径损耗，:math:`S(dB)` 是遮蔽值，:math:`L_{noise}(dB)` 是高斯噪声水平，:math:`G_{v}(dBi)` 是车载天线增益，默认为 3 dBi，:math:`G_{b}(dBi)` 是基站天线增益，默认为 8 dBi，:math:`NF_{b}(dB)` 是基站噪声系数。

信噪比 (SNR)
--------------

信噪比是信号功率与噪声功率的比率，是衡量通信质量的重要指标。计算公式为：

.. math::
   SNR(dB) = 10 \log_{10}\left(\frac{P_{rx}}{N_{0}}\right)

:math:`P_{rx}` 是接收端功率，:math:`N_{0}` 是噪声功率。

通过以上步骤，我们可以计算出通信链路的 SNR。在得到 SNR 后，我们可以进一步计算数据包丢失率、噪声水平和通信容量等性能指标，以评估 V2X 通信系统的性能。
