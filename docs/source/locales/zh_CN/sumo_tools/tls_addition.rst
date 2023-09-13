信号灯输出
===============

在 `TransSimHub` 中提供了 `generate_traffic_lights_additions` 的工具，来生成 `.add.xml` 文件，从而在模拟过程中保存交通灯状态的一些可能性。
这些保存的结果主要用于评估自适应交通灯算法。
详细内容可以参考 `Traffic Lights Output <https://sumo.dlr.de/docs/Simulation/Output/Traffic_Lights.html>`_。


信号灯 addition 生成
~~~~~~~~~~~~~~~~~~~~~


我们使用 `sumo_tools` 中的 `generate_traffic_lights_additions` 工具可以生成自定义的 `.add.xml` 文件。
下面是整体的流程，完成的代码见 `Traffic Lights Output Example <https://github.com/Traffic-Alpha/TransSimHub/blob/main/examples/sumo_tools/additional_file/tls_additions.py>`_。

.. code-block:: python

    from tshub.sumo_tools.additional_files.traffic_light_additions import generate_traffic_lights_additions

    generate_traffic_lights_additions(
        network_file='xxx.net.xml',
        output_file='./tls.add.xml'
    )

运行上面的代码，可以生成如下的配置文件。
我们只需要在运行仿真的时候，带上这个配置文件即可，
或是在 `.sumocfg` 中的 `additional-files` 指定这个文件即可。

.. code-block:: xml

    <additional xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/additional_file.xsd">
        <timedEvent type="SaveTLSStates" source="htddj_gsndj" dest="SaveTLSStates_htddj_gsndj.out.xml"/>
        <timedEvent type="SaveTLSProgram" source="htddj_gsndj" dest="SaveTLSProgram_htddj_gsndj.out.xml"/>
        <timedEvent type="SaveTLSSwitchStates" source="htddj_gsndj" dest="SaveTLSSwitchStates_htddj_gsndj.out.xml"/>
        <timedEvent type="SaveTLSSwitchTimes" source="htddj_gsndj" dest="SaveTLSSwitchTimes_htddj_gsndj.out.xml"/>
    </additional>


输出结果例子
~~~~~~~~~~~~~~~~

TLS States
-------------

每一个 `step` 记录一次每一个信号灯的状态。输出格式如下：

.. code-block:: xml

    <tlsStates>
        <tlsState time="<SIM_STEP>" id="<TLS_ID>" programID="<TLS_SUBID>" phase="<PHASE_INDEX>" state="<STATE>"/>
        ... further states ...
    </tlsStates>


下面是一个输出的例子：

.. code-block:: xml

    <tlsStates xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/tlsstates_file.xsd">
        <tlsState time="0.00" id="htddj_gsndj" programID="0" phase="0" state="rrrrrrGGGGrrrrrGGGr"/>
        <tlsState time="1.00" id="htddj_gsndj" programID="0" phase="0" state="rrrrrrGGGGrrrrrGGGr"/>
        <tlsState time="2.00" id="htddj_gsndj" programID="0" phase="0" state="rrrrrrGGGGrrrrrGGGr"/>
        <tlsState time="3.00" id="htddj_gsndj" programID="0" phase="0" state="rrrrrrGGGGrrrrrGGGr"/>
        <tlsState time="4.00" id="htddj_gsndj" programID="0" phase="0" state="rrrrrrGGGGrrrrrGGGr"/>
        <tlsState time="5.00" id="htddj_gsndj" programID="0" phase="0" state="rrrrrrGGGGrrrrrGGGr"/>
        <tlsState time="6.00" id="htddj_gsndj" programID="0" phase="0" state="rrrrrrGGGGrrrrrGGGr"/>
        <tlsState time="7.00" id="htddj_gsndj" programID="0" phase="0" state="rrrrrrGGGGrrrrrGGGr"/>
        <tlsState time="8.00" id="htddj_gsndj" programID="0" phase="0" state="rrrrrrGGGGrrrrrGGGr"/>
        ...
    </tlsStates>


TLS Switches
---------------

记录每一个 `connection` 绿灯的信息。包含开始和结束时间，`connection` 的 `fromLane` 和 `toLane` 等信息。

.. code-block:: xml

    <tlsSwitches>
        <tlsSwitch tls="<TLS_ID>" programID="<TLS_SUB_ID>" fromLane="<LINKS_SOURCE_LANE>" toLane="<LINK_DESTINATION_LANE>" begin="<BEGIN_OF_GREEN_PHASE>" end="<END_OF_GREEN_PHASE>" duration="<DURATION_OF_GREEN_PHASE>"/>
        ... further switch points ...
    </tlsSwitches>

下面是一个输出的例子：

.. code-block:: xml

    <tlsSwitches xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/tlsswitches_file.xsd">
        <tlsSwitch id="htddj_gsndj" programID="0" fromLane="gsndj_n7_0" toLane="161701303#10_0" begin="0.00" end="27.00" duration="27.00"/>
        <tlsSwitch id="htddj_gsndj" programID="0" fromLane="gsndj_n7_1" toLane="gsndj_n6_1" begin="0.00" end="27.00" duration="27.00"/>
        <tlsSwitch id="htddj_gsndj" programID="0" fromLane="gsndj_n7_2" toLane="gsndj_n6_2" begin="0.00" end="27.00" duration="27.00"/>
        <tlsSwitch id="htddj_gsndj" programID="0" fromLane="gsndj_s4_0" toLane="29257863#5_0" begin="0.00" end="27.00" duration="27.00"/>
        <tlsSwitch id="htddj_gsndj" programID="0" fromLane="gsndj_s4_1" toLane="gsndj_s5_0" begin="0.00" end="27.00" duration="27.00"/>
        <tlsSwitch id="htddj_gsndj" programID="0" fromLane="gsndj_s4_2" toLane="gsndj_s5_1" begin="0.00" end="27.00" duration="27.00"/>
        <tlsSwitch id="htddj_gsndj" programID="0" fromLane="gsndj_n7_3" toLane="29257863#5_2" begin="33.00" end="39.00" duration="6.00"/>
        <tlsSwitch id="htddj_gsndj" programID="0" fromLane="gsndj_s4_3" toLane="161701303#10_3" begin="33.00" end="39.00" duration="6.00"/>
        <tlsSwitch id="htddj_gsndj" programID="0" fromLane="29257863#2_0" toLane="gsndj_n6_0" begin="45.00" end="72.00" duration="27.00"/>
        <tlsSwitch id="htddj_gsndj" programID="0" fromLane="29257863#2_0" toLane="29257863#5_0" begin="45.00" end="72.00" duration="27.00"/>
        ...
    </tlsSwitches>


TLS Switch States
-------------------

记录每一个 `phase` 的改变。每一个 `phase` 的开始时间，和对应的 `state`。

.. code-block:: xml

    <tlsStates>
        <tlsState time="<SIM_STEP>" id="<TLS_ID>" programID="<TLS_SUBID>" phase="<PHASE_INDEX>" state="<STATE>"/>
        ... further states ...
    </tlsStates>


下面是一个输出的例子：

.. code-block:: xml

    <tlsStates xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/tlsstates_file.xsd">
        <tlsState time="0.00" id="htddj_gsndj" programID="0" phase="0" state="rrrrrrGGGGrrrrrGGGr"/>
        <tlsState time="27.00" id="htddj_gsndj" programID="0" phase="1" state="rrrrrryyyyrrrrryyyr"/>
        <tlsState time="33.00" id="htddj_gsndj" programID="0" phase="2" state="rrrrrrrrrrGrrrrrrrG"/>
        <tlsState time="39.00" id="htddj_gsndj" programID="0" phase="3" state="rrrrrrrrrryrrrrrrry"/>
        <tlsState time="45.00" id="htddj_gsndj" programID="0" phase="4" state="GGGGrrrrrrrGGGrrrrr"/>
        <tlsState time="72.00" id="htddj_gsndj" programID="0" phase="5" state="yyyyrrrrrrryyyrrrrr"/>
        <tlsState time="78.00" id="htddj_gsndj" programID="0" phase="6" state="rrrrGGrrrrrrrrGrrrr"/>
        <tlsState time="84.00" id="htddj_gsndj" programID="0" phase="7" state="rrrryyrrrrrrrryrrrr"/>
        <tlsState time="90.00" id="htddj_gsndj" programID="0" phase="0" state="rrrrrrGGGGrrrrrGGGr"/>
        <tlsState time="117.00" id="htddj_gsndj" programID="0" phase="1" state="rrrrrryyyyrrrrryyyr"/>
        <tlsState time="123.00" id="htddj_gsndj" programID="0" phase="2" state="rrrrrrrrrrGrrrrrrrG"/>
        <tlsState time="129.00" id="htddj_gsndj" programID="0" phase="3" state="rrrrrrrrrryrrrrrrry"/>
        <tlsState time="135.00" id="htddj_gsndj" programID="0" phase="4" state="GGGGrrrrrrrGGGrrrrr"/>
        ...
    </tlsStates>

TLS Programs
-------------

记录信号灯的 `program`，包含 `state` 和持续时间。

.. code-block:: xml
    
    <tlsStates>
        <tlLogic id="<TLS_ID>" programID="<TLS_SUBID>" type="static/>
            ...
        </tlLogic>
    </tlsStates>


下面是一个输出的例子：

.. code-block:: xml

    <tlLogic id="htddj_gsndj" type="static" programID="0">
        <phase duration="27.00" state="rrrrrrGGGGrrrrrGGGr"/>
        <phase duration="6.00"  state="rrrrrryyyyrrrrryyyr"/>
        <phase duration="6.00"  state="rrrrrrrrrrGrrrrrrrG"/>
        <phase duration="6.00"  state="rrrrrrrrrryrrrrrrry"/>
        <phase duration="27.00" state="GGGGrrrrrrrGGGrrrrr"/>
        <phase duration="6.00"  state="yyyyrrrrrrryyyrrrrr"/>
        <phase duration="6.00"  state="rrrrGGrrrrrrrrGrrrr"/>
        <phase duration="6.00"  state="rrrryyrrrrrrrryrrrr"/>
        <phase duration="27.00" state="rrrrrrGGGGrrrrrGGGr"/>
        ...
    </tlLogic>