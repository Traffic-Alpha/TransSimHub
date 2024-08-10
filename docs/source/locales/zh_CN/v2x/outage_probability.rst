中断概率 (Outage Probability)
=========================================

中断概率是指在给定的目标速率下，当前信道容量小于该速率的概率。

在瑞利衰落信道的假设下，信道的功率衰减量 :math:`\mu = |h|^2` 服从参数为 1 的指数分布。因此，中断概率 :math:`P_{\text{out}}(R)` 可以表示为：

.. math::
   
   \begin{align*}
   P_{\text{out}}(R) &= \Pr\left(\mu < \frac{2^R - 1}{SNR_t}\right) \\
                     &= \int_0^{\frac{2^R - 1}{SNR_t}} e^{-u} \, du \\
                     &= 1 - \exp\left(-\frac{2^R - 1}{SNR_t}\right)
   \end{align*}
   
其中：

-  :math:`R` 是给定的目标速率（单位：比特/秒/赫兹）
-  :math:`SNR_t` 是该时刻的信噪比（单位：分贝）



中断概率例子
---------------

例如，假设信道带宽为 30 kHz，目标速率为 20 kb/s，信噪比 \( SNR \) 为 10 dB，我们可以计算中断概率为：

.. math::

   1 - \exp\left(-\frac{2^{\frac{20 \times 10^3}{30 \times 10^3}} - 1}{10}\right) \approx 0.057

这个结果表明，在当前的信噪比下，有大约 5.7% 的概率会发生中断。
