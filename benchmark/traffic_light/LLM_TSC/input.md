<!--
 * @Author: WANG Maonan
 * @Date: 2023-09-14 20:52:12
 * @Description: 
 * @LastEditTime: 2023-09-22 14:04:35
-->
## 初始输入

- 给出路口的信息

## 询问所有的动作:

- 解释下一个 phase 的 id
- 需要去理解动作的含义，如何让 LLM 理解我们的动作

## 询问当前的状态:

- 排队长度
- 车辆的等待时间

```json
{
  "movements": {
    "north": {
      "lanes": [
        {"to": "east", "direction": "left", "lane_numbers": 1, "queue length": 20},
        {"to": "south", "direction": "through", "lane_numbers": 2, "queue length": 30},
        {"to": "west", "direction": "right", "lane_numbers": 1, "queue length": 10}
      ],
      "bicycleLane": false,
    },
    "south": {
      "lanes": [
        {"to": "west", "direction": "left", "lane_numbers": 1, "queue length": 0},
        {"to": "north", "direction": "through", "lane_numbers": 2, "queue length": 20},
        {"to": "east", "direction": "right", "lane_numbers": 1, "queue length": 7}
      ],
      "bicycleLane": false,
    },
    "east": {
      "lanes": [
        {"to": "north", "direction": "left", "lane_numbers": 1, "queue length": 0},
        {"to": "west", "direction": "through", "lane_numbers": 2, "queue length": 10},
        {"to": "south", "direction": "right", "lane_numbers": 1, "queue length": 7}
      ],
      "bicycleLane": false,
    },
    "west": {
      "lanes": [
        {"to": "south", "direction": "left", "lane_numbers": 1, "queue length": 0},
        {"to": "east", "direction": "through", "lane_numbers": 2, "queue length": 15},
        {"to": "north", "direction": "right", "lane_numbers": 1, "queue length": 14}
      ],
      "bicycleLane": false,
    }
  }
}
```

## 询问当前的相位

```json
{
  "signalPhases": [
    {
      "phaseId": 0,
      "movements": [
        {
          "from": "north",
          "to": "south",
          "direction": "through"
        },
        {
          "from": "south",
          "to": "north",
          "direction": "through"
        }
      ]
    },
    {
      "phaseId": 1,
      "movements": [
        {
          "from": "north",
          "to": "east",
          "direction": "left"
        },
        {
          "from": "south",
          "to": "west",
          "direction": "left"
        }
      ]
    },
    {
      "phaseId": 2,
      "movements": [
        {
          "from": "east",
          "to": "west",
          "direction": "through"
        },
        {
          "from": "west",
          "to": "east",
          "direction": "through"
        }
      ]
    },
    {
      "phaseId": 3,
      "movements": [
        {
          "from": "east",
          "to": "south",
          "direction": "left"
        },
        {
          "from": "west",
          "to": "north",
          "direction": "left"
        }
      ]
    }
  ]
}

```

## 询问是否有 Emergency Vehicle

```json
{
    "emergencyVehicle": {
        "distanceFromIntersection": 0.2,
        "speed": 45,
        "approach": "north",
        "lane": {"to": "south", "direction": "through"}
    },
}
```

