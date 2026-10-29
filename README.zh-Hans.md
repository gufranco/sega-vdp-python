# Sega VDP

用 Python 实现的世嘉 315-5124、315-5246 和 315-5378 视频显示处理器，连同各自内置的声音发生器，以主时钟一个节拍为单位推进，并以世嘉的 Mark III 参考手册为准进行核对。

[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文（香港）](README.zh-HK.md)

[![ci](https://img.shields.io/github/actions/workflow/status/gufranco/sega-vdp-python/ci.yml?branch=main&style=flat-square&label=ci)](https://github.com/gufranco/sega-vdp-python/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/gufranco/sega-vdp-python?style=flat-square&label=release)](https://github.com/gufranco/sega-vdp-python/releases/latest)
[![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?style=flat-square)](https://github.com/gufranco/sega-vdp-python/actions/workflows/ci.yml)
[![openssf scorecard](https://img.shields.io/ossf-scorecard/github.com/gufranco/sega-vdp-python?style=flat-square&label=openssf%20scorecard)](https://scorecard.dev/viewer/?uri=github.com/gufranco/sega-vdp-python)
[![license](https://img.shields.io/github/license/gufranco/sega-vdp-python?style=flat-square&label=license)](LICENSE)

**2,608** 个不同的 Master System 和 Game Gear 映像各启动 **600** 帧，**0** 个属性失败（涵盖其中 **794** 个使用世嘉分页的零售映像），在手册中定位到 **64** 处引文，**3** 款芯片，**862** 个测试，**100%** 语句和分支覆盖率，除标准库和家族中的两个成员外无依赖

```python
import segavdp

part = segavdp.Chip("315-5246", segavdp.Vram(fill=0))
part.reset()
part.read_status()

for register, value in {0: 0x06, 1: 0x40, 2: 0xFF, 8: 0x00, 9: 0x00}.items():
    part.write_control(value)
    part.write_control(0x80 | register)

part.write_control(0x00)
part.write_control(0xC0)
for colour in (0x00, 0x3F):
    part.write_data(colour)
    part.run_dots(64)

for address, value in {0x3800: 0x01, 0x0020: 0x80}.items():
    part.write_control(address & 0xFF)
    part.write_control(0x40 | address >> 8)
    part.write_data(value)
    part.run_dots(64)

for line in (1, 0):
    while (part.line, part.dot) != (line, 0):
        part.clock()

shown = []
for _ in range(3):
    part.clock()
    shown.append((part.shown, part.colour))
print(shown)
print(part.model, part.region, part.read_v_counter())
```

```
[('active', 63), ('active', 0), ('active', 0)]
315-5246 ntsc 0
```

芯片上电时寄存器、调色板 RAM 和显存都是随机的，所以示例先复位，再读一次状态，清除写到一半的命令。五次寄存器写入选择模式 4、打开显示、把屏幕映射放在 3800h，并把两个滚动值清零。两次调色板 RAM 写入把颜色 0 设为黑色、颜色 1 设为白色。屏幕映射的第一个单元是图案 1，其最上一行以一个颜色 1 的点开始。等待两次第 0 行，是为了像真实芯片一样，让垂直滚动在一帧开头被锁存。

## 安装

| 要求   | 版本                 |
| :----- | :------------------- |
| Python | 3.12 或更高          |
| git    | 任意，用于获取子模块 |

```bash
git clone --recurse-submodules https://github.com/gufranco/sega-vdp-python.git
cd sega-vdp-python
export PYTHONPATH=.:ti-tms9918-python:ti-sn76489-python
python3 segavdp/doctor.py
```

这个包不复制家族中的另外两个成员，而是把它们组合起来。TMS9918 的各种模式来自 `ti-tms9918-python`，声音发生器来自 `ti-sn76489-python`，两者都是位于导入路径上的 git 子模块，`PYTHONPATH` 这一行就是设置它们的。第三个子模块 `zilog-z80-python` 驱动普查和测试卡带。通过下载 ZIP 链接得到的源码包不含子模块，无法运行；请改用 `--recurse-submodules` 克隆。由于以这种方式引用其他成员，这个包无法从索引安装，也不会在那里发布任何东西。

doctor 检查机器和检出的代码，最后输出一行结论。提交缺陷报告时，请贴上它的完整输出。

```
  11 checks, nothing to report
```

版本遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根据提交历史生成。每个版本都会打上标签，并列在[发布页面](https://github.com/gufranco/sega-vdp-python/releases)上。

## 接口

`segavdp.Chip(model, memory=None, seed=UNSET_SEED, region=None, handheld_mode=None)` 构建一个芯片。`model` 是必需的。`memory` 是任何具有 `read8(address)` 和 `write8(address, value)` 的对象，省略时芯片会自行构建一个随机的 16 KB `Vram`。`region` 为 `ntsc` 或 `pal`，省略时取该芯片支持的第一个制式。`handheld_mode` 让 Game Gear 芯片进入其自身模式，它启动时就处于该模式；主机芯片上该选项始终关闭。

| 型号       | 别名                              | 制式          | 画面             | 横向放大 | 旧模式的颜色              |
| :--------- | :-------------------------------- | :------------ | :--------------- | :------- | :------------------------ |
| `315-5124` | `5124`, `sms`, `mark3`, `markiii` | `ntsc`, `pal` | 192 行           | 4 个精灵 | 固定表                    |
| `315-5246` | `5246`, `sms2`                    | `ntsc`, `pal` | 192、224、240 行 | 8 个精灵 | 固定表                    |
| `315-5378` | `5378`, `gg`, `gamegear`          | `ntsc`        | 192、224 行      | 8 个精灵 | 调色板 RAM 第 16 至 31 项 |

### 调用

| 调用                         | 作用                                                                               |
| :--------------------------- | :--------------------------------------------------------------------------------- |
| `reset()`                    | 清除寄存器 0 和 1、状态标志以及写到一半的命令，并把电子束移到第 0 行开头。返回芯片 |
| `write_control(value)`       | 向控制端口写一个字节：带两个命令位的地址的一半，或寄存器写入的一半                 |
| `write_data(value)`          | 向显存写一个字节，命令 3 之后则写向调色板 RAM。它在访问提前量之后生效              |
| `read_data()`                | 返回读缓冲区，然后取下一个字节                                                     |
| `read_status()`              | 返回状态字节，并清除帧、溢出和碰撞标志以及挂起的行中断                             |
| `read_v_counter()`           | 当前行的 V 计数器                                                                  |
| `read_h_counter()`           | 最近一次锁存的 H 计数器                                                            |
| `latch_h_counter()`          | 锁存 H 计数器，与手柄 TH 线的变化效果相同                                          |
| `write_sound(value)`         | 向芯片内置的声音发生器写一个字节                                                   |
| `read_port(address)`         | 按 A7、A6、A0 对 40h 至 BFh 解码的读取；超出范围时为 `None`                        |
| `write_port(address, value)` | 按同样方式解码的写入：数据、控制或声音发生器                                       |
| `tick()`                     | 一个主时钟周期，即处理器时钟的三分之一                                             |
| `clock()`                    | 一个点，即两个节拍                                                                 |
| `run_dots(count)`            | `count` 个点                                                                       |

### 状态

| 属性            | 含义                                                                              |
| :-------------- | :-------------------------------------------------------------------------------- |
| `line`          | 从第一条显示行开始计数的行号。它在该行第一个显示点之前 76 个点时就会前进          |
| `dot`           | 从第一个显示点开始计数的点号                                                      |
| `shown`         | 上一个点是 `active`、`border`、`blanking`、`sync` 还是 `burst`                    |
| `colour`        | 上一个点的调色板 RAM 值，主机芯片为 6 位，Game Gear 为 12 位，或为 `None`         |
| `interrupt`     | INT 引脚被拉起时为 True                                                           |
| `status`        | 三个状态标志，读取时不清除任何东西                                                |
| `registers`     | 十一个寄存器，类型为 `bytearray`                                                  |
| `mode`          | 寄存器所选的 `Mode`：`name`、`height`，以及是否使用较高画面的表格的 `tall`        |
| `cram`          | 调色板 RAM：`entry(index)`、`entries()` 和 `write(address, value, handheld_mode)` |
| `sound`         | 芯片内置的声音发生器                                                              |
| `region`        | `ntsc` 或 `pal`                                                                   |
| `handheld_mode` | Game Gear 芯片是否处于其自身模式                                                  |
| `lost`          | 在前一次访问生效之前就发出的访问次数                                              |
| `model`         | 规范的型号名                                                                      |
| `part`          | `Model` 记录                                                                      |
| `memory`        | 显存对象                                                                          |
| `cycles`        | 自芯片构建以来的主时钟节拍数                                                      |

### 模块内容

| 名称                                       | 内容                                                                            |
| :----------------------------------------- | :------------------------------------------------------------------------------ |
| `segavdp.MODELS`                           | 三条 `Model` 记录，以规范名称为键                                               |
| `segavdp.Vram(fill=None, seed=UNSET_SEED)` | 16 KB 显存，即 TMS9918 成员自己的那个                                           |
| `segavdp.port(address)`                    | 处理器端口到达哪个寄存器：`data`、`control`、`v counter`、`h counter` 或 `None` |
| `segavdp.NTSC`, `segavdp.PAL`              | 两个制式名称                                                                    |
| `segavdp.UnknownModelError`                | 型号名缺失或未知时抛出。消息中列出可接受的名称                                  |
| `segavdp.UnknownRegionError`               | 指定了芯片不支持的制式时抛出                                                    |
| `segavdp.NoStereo`                         | 向主机芯片请求 Game Gear 的立体声寄存器时抛出                                   |
| `segavdp.__version__`                      | 已安装的版本                                                                    |

### 模块

每个模块都是构成芯片的一个部件，测试或调用方可以直接使用。

| 模块                 | 内容                                                |
| :------------------- | :-------------------------------------------------- |
| `segavdp.core`       | 芯片本身、端口解码和访问提前量                      |
| `segavdp.display`    | 在模式 4 和 TMS9918 各模式下每个点显示什么          |
| `segavdp.background` | 模式 4 的背景单元、滚动和屏幕映射地址               |
| `segavdp.sprites`    | 模式 4 的精灵评估和一行精灵的点                     |
| `segavdp.modes`      | 寄存器所选的模式和画面高度                          |
| `segavdp.timing`     | 帧的布局、V 和 H 计数器以及行事件所在的点           |
| `segavdp.palette`    | 两类芯片的调色板 RAM、其亮度以及旧模式的颜色        |
| `segavdp.sound`      | 建立在 `ti-sn76489-python` 之上的芯片内置声音发生器 |
| `segavdp.models`     | 三条 `Model` 记录和制式名称                         |
| `segavdp.flags`      | 三个状态标志                                        |
| `segavdp.errors`     | 这个包抛出的一切                                    |

```python
import segavdp

for name, model in segavdp.MODELS.items():
    print(name, model.aliases, model.regions, model.extended, model.zoomed_across)

for name in ("315-5124", "315-5246", "315-5378"):
    part = segavdp.Chip(name)
    print(part.model, part.region, len(part.kinds), part.handheld_mode)

print(
    segavdp.Chip("315-5246", region="pal").region,
    segavdp.Chip("gg", handheld_mode=False).handheld_mode,
)

try:
    segavdp.Chip("315-5313")
except segavdp.UnknownModelError as error:
    print(error)

try:
    segavdp.Chip("315-5378", region="pal")
except segavdp.UnknownRegionError as error:
    print(error)
```

```
315-5124 ('5124', 'sms', 'mark3', 'markiii') ('ntsc', 'pal') False 4
315-5246 ('5246', 'sms2') ('ntsc', 'pal') True 8
315-5378 ('5378', 'gg', 'gamegear') ('ntsc',) True 8
315-5124 ntsc 262 False
315-5246 ntsc 262 False
315-5378 ntsc 262 True
pal False
315-5313 is not a model this package covers; it has 315-5124, 315-5246, 315-5378
pal is not a region the 315-5378 runs in; it runs in ntsc
```

## 行计数器

```python
import segavdp

part = segavdp.Chip("315-5124", segavdp.Vram(fill=0))
part.reset()
part.read_status()
for register, value in {0: 0x16, 1: 0x80, 10: 94}.items():
    part.write_control(value)
    part.write_control(0x80 | register)

for line in (200, 0):
    while (part.line, part.dot) != (line, 0):
        part.clock()
part.read_status()

raised = []
for _ in range(193 * 342):
    part.clock()
    if part.interrupt:
        raised.append(part.line)
        part.read_status()
print(raised)
```

```
[94, 189]
```

世嘉的手册说，寄存器 10 要装入比希望中断的行少一的值。装入 94 时，请求在第 95 行（从 1 数起）开始时到来，并在 95 行之后再来一次。计数器在显示期间之外重新装载，所以这一帧的第三次请求不会出现。

## 处理器的访问速度

世嘉的手册说，芯片接收数据的速度不超过显示期间每 29 个 T 状态一次、垂直消隐期间每 16 个 T 状态一次。两盒针对真实硬件编写的测试卡带都比这更快，所以模型在显示期间让一次访问在前一次之后 26 个 T 状态生效，在消隐期间则一次也不丢。第一次访问还在等待时到来的第二次访问会取代它。

```python
import segavdp


def spaced(gap, display):
    part = segavdp.Chip("315-5124", segavdp.Vram(fill=0))
    part.reset()
    part.read_status()
    part.write_control(0x40 if display else 0x00)
    part.write_control(0x81)
    while (part.line, part.dot) != (10, 0):
        part.clock()
    part.write_control(0x00)
    part.write_control(0x40)
    for value in (0x11, 0x22, 0x33):
        part.write_data(value)
        for _ in range(gap * 3):
            part.tick()
    part.run_dots(100)
    return [hex(part.memory.read8(address)) for address in range(3)], part.lost


print(spaced(26, display=True))
print(spaced(20, display=True))
print(spaced(12, display=False))
```

```
(['0x11', '0x22', '0x33'], 0)
(['0x0', '0x0', '0x33'], 2)
(['0x11', '0x22', '0x33'], 0)
```

## 普查

```bash
python3 -m conformance.census "external/Master EverDrive" "external/EverDrive GG" --frames 600 --jobs 12
```

普查把 Master System 和 Game Gear 卡带库中的每个映像，放在由这个芯片、`zilog-z80-python` 处理器和世嘉的分页组成的电路板上启动，各运行固定的帧数。`.sms` 映像运行在 315-5246 上，`.gg` 映像运行在处于其自身模式的 315-5378 上。它接受目录、ZIP 压缩包和单个映像，按摘要把每个不同的映像只计一次，打印摘要，写出 [`conformance/corpus.json`](conformance/corpus.json)，并在某项性质被破坏时以 1 退出。

运行由两项性质把关：模型在任何映像上都不抛出异常，以及每个使用世嘉分页的零售映像都会打开显示。[`conformance/boards.json`](conformance/boards.json) 按 MAME 软件列表的记录，以整个文件的 SHA-1 列出建在其他电路板上的映像，例如 Codemasters 的分页；这些映像在没有自身电路板的情况下运行，并单独计数。丢失的访问按映像计数并列出，但不参与把关。

| 上一次运行的结果                                       | 数量      |
| :----------------------------------------------------- | :-------- |
| 两个卡带库中的条目                                     | 5,110     |
| 不同的映像                                             | 2,608     |
| 使用世嘉分页的零售映像，参与把关                       | 794       |
| 建在其他电路板上的映像，在没有该电路板的情况下运行     | 59        |
| 模式 4，192 行                                         | 2,429     |
| 模式 4，224 行                                         | 8         |
| Graphics II                                            | 68        |
| Graphics I                                             | 29        |
| 设置了 Multicolor 位的 Text                            | 2         |
| 模式 4 的无效 Text 模式                                | 2         |
| 从未打开显示，其中没有使用世嘉分页的零售版             | 79        |
| 8 x 8 精灵                                             | 1,778     |
| 8 x 16 精灵                                            | 764       |
| 8 x 8 精灵，放大                                       | 9         |
| 请求过行中断                                           | 1,011     |
| 零售版映像上丢失的访问，45% 来自 CJ Elephant Fugitive  | 91,127    |
| 其余映像上丢失的访问，大多来自公有领域的测试程序和演示 | 2,991,054 |

[`conformance/corpus.json`](conformance/corpus.json) 只保存这些计数，不含任何卡带内容，因此在没有卡带库的机器上，测试套件也能核对它们。

## 测试卡带

```bash
python3 -m conformance.testroms "/path/to/5 Tools & Service Test Carts.zip"
```

[`conformance/testroms.json`](conformance/testroms.json) 按 SHA-256 列出每一盒测试这个芯片的测试卡带、每次运行所用的手柄按键脚本，以及它显示的内容。

| 卡带                                         | 运行于                                        | 记录的内容                                                                      |
| :------------------------------------------- | :-------------------------------------------- | :------------------------------------------------------------------------------ |
| SEGA Master System TestSuite 0.32，sverx 作  | 60 Hz 的 315-5124，60 Hz 和 50 Hz 的 315-5246 | 其 System Info 页面正确说出每个芯片和每种电视制式，没有丢失访问                 |
| V Counter Test Program，Charles MacDonald 作 | 60 Hz 的 315-5246                             | 其页面显示 00h 至 DAh，然后 D5h 至 FFh，与 MacDonald 文档所列一致，没有丢失访问 |
| Line Interrupt Test #1，Charles MacDonald 作 | 60 Hz 的 315-5246                             | 仅作刺激；丢失 1 次访问                                                         |
| Interrupt Test                               | 60 Hz 的 315-5246                             | 仅作刺激；没有丢失访问                                                          |
| BG Test 0.01                                 | 60 Hz 的 315-5124                             | 仅作刺激；丢失 721 次访问                                                       |
| Sprite Test                                  | 60 Hz 的 315-5246                             | 仅作刺激；丢失 600,408 次访问，显示期间每 11 和 18 个 T 状态写一次              |
| 64 Color Palette Test                        | 60 Hz 的 315-5124                             | 仅作刺激；丢失 15,568 次访问                                                    |
| Color & Switch Test                          | 60 Hz 的 315-5124                             | 仅作刺激；没有丢失访问                                                          |
| Palette Tool 1.0                             | 60 Hz 的 315-5246                             | 仅作刺激；没有丢失访问                                                          |

System Info 页面还会说出主机型号、地区和引导程序。这些由普查用的电路板回答，而不是由这个芯片回答，所以记录只保留它们而不作判断。三盒刺激用卡带在这里丢失的写入，真实主机是否也会丢失尚不清楚；什么能解决这个问题见 [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)。

## 是否正确

世嘉印出的、测试能够触及的每一项事实都由代码核对。[`conformance/hardware.json`](conformance/hardware.json) 记录每项事实及其原句和页码，[`conformance/hardware.test.py`](conformance/hardware.test.py) 和 [`conformance/display.test.py`](conformance/display.test.py) 用它们来驱动芯片。`python3 -m conformance.quotes` 会在所引用的文档中找到每一句引文。

手册没有印出的每个值都放在同一文件的 `notStated` 下，标记为未验证，并附有来源以及能够解决它的测量。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出仍未解决的问题。两个来源（包括手册）相互矛盾的地方见 [`conformance/divergences.json`](conformance/divergences.json)。

## 参与开发

| 需要                           | 位置                                                                |
| :----------------------------- | :------------------------------------------------------------------ |
| 所有检查及其运行顺序           | [CONTRIBUTING.md](CONTRIBUTING.md)                                  |
| 面向编码代理的同样内容         | [AGENTS.md](AGENTS.md)                                              |
| 本仓库与家族其他成员共享的标准 | [FAMILY.md](FAMILY.md)                                              |
| 缺陷报告                       | [GitHub Issues](https://github.com/gufranco/sega-vdp-python/issues) |
| 安全报告                       | [SECURITY.md](SECURITY.md)                                          |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 segavdp/core.test.py
```

每个模块旁边都有一个以它命名的测试文件，每个都可以像上面那样单独运行。覆盖率是硬性检查，语句和分支都必须达到 100%。

## 参考资料

- _Software Reference Manual for the SEGA Mark III Console_，世嘉，无日期，重新打字版。45 页，184,840 字节，SHA-256 `166f09331ba9df055f7a352f10c6a7843911470bc72d9347eda4a0de86e8cfce`。本仓库不包含它。`python3 -m conformance.documents` 从 https://segaretro.org/images/d/d6/SoftwareReferenceManualForSegaMarkIIIEU.pdf 下载它，并拒绝任何其他文件。
- _Sega Master System VDP documentation_，Charles MacDonald，2002 年 11 月 12 日。43,417 字节，SHA-256 `dc16f8e687b8b137d9f7d457659135ebb7b21e6e7874250fac0719dd1eb6207c`，取自 https://www.smspower.org/uploads/Development/msvdp-20021112.txt 。
- _SN76489_，SMS Power，由 Maxim 维护的页面的打印视图。54,534 字节，SHA-256 `14d146c13d4d98a04b2c2c05498753bc60197696cea1b73860bfa23416cd15ce`，取自 https://www.smspower.org/Development/SN76489?action=print 。
- Genesis Plus GX，提交 `a5834b3df455c49bb97bfaa328c20845831f576b` 时的 `core/hvc.h` 和 `core/vdp_render.c`，https://github.com/ekeeke/Genesis-Plus-GX ，用于 H 计数器、一行中事件的顺序以及旧模式的颜色。只采用事实，不取任何代码。
- MAME，提交 `94fc55c9692b180dcb608e2e222e48315db5017a` 时的 `hash/sms.xml` 和 `hash/gamegear.xml`，https://github.com/mamedev/mame ，用于卡带的电路板。只采用事实，不取任何代码。

## 引用本项目

[CITATION.cff](CITATION.cff) 在每次发布时由写入包版本号的脚本更新。

## 许可证

MIT。见 [LICENSE](LICENSE)。
