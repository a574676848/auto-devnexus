---
name: mijia
description: 控制与查询米家（小米智能家居）设备。通过 <HA_HOST> 上的 Home Assistant + 小米官方集成（ha_xiaomi_home）读取设备状态、开关灯/晾衣架/热水器、执行场景。当用户提到米家、小爱、吸顶灯、晾衣架、摄像头、热水器、智能家居状态或"把主卧灯关掉"这类指令时使用。
---

# 米家（Mijia / Home Assistant）

## 接通方式

不是第三方中转，也不是 mijiaAPI。链路是：

```
本机脚本 --HTTP--> HA <HA_HOST>:8123 --OAuth token--> 小米官方云端 api.io.mi.com
```

- HA 容器名 `homeassistant`（Docker context `default`，宿主 <HA_HOST>）
- 集成：小米官方 `ha_xiaomi_home` v0.5.0，entry `<HA_CONFIG_ENTRY_ID>`
- 家庭：`示例家庭`（8 台设备，223 个实体）
- 凭据目录：`~/.mijia\`
  - `ha.json`：HA 地址 + 管理员账号 + 30 天 access_token
  - `ha_mcp_token.txt`：长期访问令牌（脚本用它，10 年有效）

## 用法

```bash
python skills/mijia/scripts/mijia.py entities --domain light
python skills/mijia/scripts/mijia.py entities --grep 主卧
python skills/mijia/scripts/mijia.py state light.example_light_a
python skills/mijia/scripts/mijia.py on  light.example_light_a
python skills/mijia/scripts/mijia.py off light.example_light_a
python skills/mijia/scripts/mijia.py service light.turn_on --entity light.example_light_b --data '{"brightness":200}'
python skills/mijia/scripts/mijia.py scenes
```

脚本零依赖（标准库 urllib），Windows 下用哪个 Python 都行。

## 已知设备与实体前缀

| 设备 | model | 关键实体 |
| --- | --- | --- |
| 雷士吸顶灯（多房间） | leishi.light.eps127 | `light.leishi_cn_<did>_eps127_s_2_light`（灯）、`_s_4_ambient_light`（氛围灯） |
| 米家智能双控晾衣机 | xiaomi.airer.lyj4qc | `light.example_light_b`、cover/switch 若干 |
| 小米智能摄像机2 云台版 | chuangmi.camera.039a01 | `light.…_s_3_indicator_light`（指示灯）、camera/switch |
| 米家电热水器 S1 7L | zimi.waterheater.h03 | water_heater + 若干 sensor/switch |
| 左点小艾2代艾灸盒 | zdeer.ajh.a9 | 多为传感器，仅指示灯 |

## 状态说明

实体状态 `unavailable` 表示设备当前离线或断电（云端拿不到属性），不是脚本故障。先把设备通电再用 `state` 复验。

## 边界与安全

- 只读优先：查状态、列设备随时可做。
- 写操作（开灯/关灯/调亮度/执行场景）属于改变真实物理环境，用户明确说了再做；一次只发一条，发完复查状态。
- 摄像头、门锁类不要做任何开关动作；涉及隐私的动作先问。
- 不涉及支付与下单，这个技能不产生费用。

## 维护

- HA 重启：`docker restart homeassistant`（context 已指向 HA 主机）
- 看日志：`docker logs --tail 100 homeassistant`
- 令牌失效：用 HA 的 WebSocket 命令 `auth/long_lived_access_token` 重新签发
- 重装集成：把 release zip 解到 `/config/custom_components/xiaomi_home` 后重启容器

## 实测设备全景（2026-10-29 核对，以本节为准）

| 设备 | did | 实体数 | 说明 |
| --- | --- | --- | --- |
| 雷士吸顶灯 A | `<did>` | 灯+氛围灯 | 当前离线 |
| 雷士吸顶灯 B | `<did>` | 灯+氛围灯 | 当前离线 |
| 雷士吸顶灯 C | `<did>` | 灯+氛围灯 | 当前离线 |
| 雷士吸顶灯 pro | `<did>` | 灯+氛围灯 | 当前离线 |
| 小米智能摄像机2 云台版 | `<did>` | 50 | 可读事件/配置，无视频流 |
| 米家智能双控晾衣机 | `<did>` | 27 | 灯、收合开关、故障、运行速度 |
| 米家智能小厨宝7L S1 | `<did>` | 12 | 档位、加热状态、杀菌、防冻 |
| 左点小艾2代艾灸盒 | `<did>` | 少量 | 仅指示灯等 |

示例家庭共 223 个实体：switch 85 / number 39 / sensor 30 / select 14 / event 13 / light 11 / text 11 / button 10 / cover 3。

### 实体命名规律

`<domain>.<品牌>_cn_<did>_<型号短名>_<siid>_<piid>_<功能名>`

例：`light.example_light_a`。查某台设备的全部实体，最快是 `--grep <did>`，比按中文名匹配可靠。

### 摄像机的真实边界

50 个实体里**没有 camera 域**，也没有云台转向实体。可用的是：

- `binary_sensor.example_motion`：移动事件，state 为最近一次触发时间
- 移动侦测时段、巡航起止时间/位置/重复项、常看位置配置（text 类）
- 存储卡格式化/弹出按钮、P2P 流开始/停止按钮

`button.*_start_p2p_stream` 只是向云端发指令，不会把视频交给 HA。要画面只能走米家 App 或私有 P2P 协议。不要对外承诺"能看监控"。

### 小厨宝要点

- 档位：`water_heater.example_heater`，state 为中档/低档/高档
- 加热状态：`sensor.…example_heater_status`，`Keep-warming` 保温、`Heating` 加热中
- 电源：`switch.…_h03_on_p_2_6`；故障码：`sensor.…_h03_fault_p_2_1`，0 为正常

### 操作口径

- 查询类指令直接跑，不用问。
- 开关灯、调档位、执行场景：用户明确说了才动手，一次一条，回读状态确认。
- 摄像头只读，绝不碰格式化、弹出存储卡、开关机、云台。
