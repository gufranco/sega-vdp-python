# Sega VDP

以 Python 實作的世嘉 315-5124、315-5246 及 315-5378 視像顯示處理器，連同各自內置的聲音產生器，以主時鐘一個節拍為單位推進，並以世嘉的 Mark III 參考手冊為準核對。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![ci](https://img.shields.io/github/actions/workflow/status/gufranco/sega-vdp-python/ci.yml?branch=main&style=flat-square&label=ci)](https://github.com/gufranco/sega-vdp-python/actions/workflows/ci.yml)
[![release](https://img.shields.io/github/v/release/gufranco/sega-vdp-python?style=flat-square&label=release)](https://github.com/gufranco/sega-vdp-python/releases/latest)
[![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?style=flat-square)](https://github.com/gufranco/sega-vdp-python/actions/workflows/ci.yml)
[![openssf scorecard](https://img.shields.io/ossf-scorecard/github.com/gufranco/sega-vdp-python?style=flat-square&label=openssf%20scorecard)](https://scorecard.dev/viewer/?uri=github.com/gufranco/sega-vdp-python)
[![license](https://img.shields.io/github/license/gufranco/sega-vdp-python?style=flat-square&label=license)](LICENSE)

**2,608** 個不同的 Master System 和 Game Gear 映像各啟動 **600** 幀，其中 **794** 個使用世嘉分頁的零售映像的屬性失敗為 **0**，在手冊中找到 **64** 處引文，**3** 款晶片，**862** 個測試，**100%** 語句和分支覆蓋率，除標準庫和家族中兩個成員外沒有依賴套件

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

晶片開機時暫存器、調色盤 RAM 和視像記憶體都是隨機的，所以例子先重設，再讀一次狀態，清除寫到一半的指令。五次暫存器寫入選擇模式 4、開啟顯示、把畫面映射放在 3800h，並把兩個捲動值清零。兩次調色盤 RAM 寫入把顏色 0 設為黑色、顏色 1 設為白色。畫面映射的第一個格是圖案 1，其最上一行以一點顏色 1 開始。等待兩次第 0 行，是為了像真實晶片一樣，讓垂直捲動在一幀開頭被鎖存。

## 安裝

| 要求   | 版本                     |
| :----- | :----------------------- |
| Python | 3.12 或以上              |
| git    | 任何版本，用來取得子模組 |

```bash
git clone --recurse-submodules https://github.com/gufranco/sega-vdp-python.git
cd sega-vdp-python
export PYTHONPATH=.:ti-tms9918-python:ti-sn76489-python
python3 segavdp/doctor.py
```

這個套件沒有複製家族中另外兩個成員，而是把它們組合起來。TMS9918 的各種模式來自 `ti-tms9918-python`，聲音產生器來自 `ti-sn76489-python`，兩者都是位於匯入路徑上的 git 子模組，`PYTHONPATH` 這一行就是設定它們的。第三個子模組 `zilog-z80-python` 驅動普查和測試卡帶。經下載 ZIP 連結取得的原始碼封存不含子模組，無法執行；請改用 `--recurse-submodules` 複製。由於以這種方式引用其他成員，這個套件無法從索引安裝，也不會在那裏發佈任何東西。

doctor 檢查電腦和簽出的程式碼，最後輸出一行結論。提交錯誤報告時，請貼上它的完整輸出。

```
  11 checks, nothing to report
```

版本遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 按提交歷史產生。每個版本都會加上標籤，並列在[發佈頁面](https://github.com/gufranco/sega-vdp-python/releases)上。

## 介面

`segavdp.Chip(model, memory=None, seed=UNSET_SEED, region=None, handheld_mode=None)` 建立一塊晶片。`model` 是必需的。`memory` 是任何具有 `read8(address)` 和 `write8(address, value)` 的物件，省略時晶片會自行建立一個隨機的 16 KB `Vram`。`region` 為 `ntsc` 或 `pal`，省略時取該晶片支援的第一種制式。`handheld_mode` 令 Game Gear 晶片進入其自身模式，它開機時就處於該模式；主機晶片上這個選項永遠關閉。

| 型號       | 別名                              | 制式          | 畫面             | 橫向放大 | 舊模式的顏色              |
| :--------- | :-------------------------------- | :------------ | :--------------- | :------- | :------------------------ |
| `315-5124` | `5124`, `sms`, `mark3`, `markiii` | `ntsc`, `pal` | 192 行           | 4 個精靈 | 固定表                    |
| `315-5246` | `5246`, `sms2`                    | `ntsc`, `pal` | 192、224、240 行 | 8 個精靈 | 固定表                    |
| `315-5378` | `5378`, `gg`, `gamegear`          | `ntsc`        | 192、224 行      | 8 個精靈 | 調色盤 RAM 第 16 至 31 項 |

### 呼叫

| 呼叫                         | 作用                                                                               |
| :--------------------------- | :--------------------------------------------------------------------------------- |
| `reset()`                    | 清除暫存器 0 和 1、狀態旗標以及寫到一半的指令，並把電子束移到第 0 行開頭。傳回晶片 |
| `write_control(value)`       | 向控制連接埠寫一個位元組：帶兩個指令位元的位址的一半，或暫存器寫入的一半           |
| `write_data(value)`          | 向視像記憶體寫一個位元組，指令 3 之後則寫向調色盤 RAM。它在存取前置時間之後生效    |
| `read_data()`                | 傳回讀取緩衝區，然後取下一個位元組                                                 |
| `read_status()`              | 傳回狀態位元組，並清除幀、溢出和碰撞旗標以及待處理的行中斷                         |
| `read_v_counter()`           | 目前一行的 V 計數器                                                                |
| `read_h_counter()`           | 最近一次鎖存的 H 計數器                                                            |
| `latch_h_counter()`          | 鎖存 H 計數器，與手掣 TH 線的變化效果相同                                          |
| `write_sound(value)`         | 向晶片內置的聲音產生器寫一個位元組                                                 |
| `read_port(address)`         | 按 A7、A6、A0 對 40h 至 BFh 解碼的讀取；超出範圍時為 `None`                        |
| `write_port(address, value)` | 按同樣方式解碼的寫入：資料、控制或聲音產生器                                       |
| `tick()`                     | 一個主時鐘週期，即處理器時鐘的三分之一                                             |
| `clock()`                    | 一點，即兩個節拍                                                                   |
| `run_dots(count)`            | `count` 點                                                                         |

### 狀態

| 屬性            | 意思                                                                              |
| :-------------- | :-------------------------------------------------------------------------------- |
| `line`          | 從第一條顯示行開始計算的行號。它在該行第一個顯示點之前 76 點時就會前進            |
| `dot`           | 從第一個顯示點開始計算的點號                                                      |
| `shown`         | 上一點是 `active`、`border`、`blanking`、`sync` 還是 `burst`                      |
| `colour`        | 上一點的調色盤 RAM 值，主機晶片為 6 位元，Game Gear 為 12 位元，或為 `None`       |
| `interrupt`     | INT 針腳被觸發期間為 True                                                         |
| `status`        | 三個狀態旗標，讀取時不清除任何東西                                                |
| `registers`     | 十一個暫存器，類型為 `bytearray`                                                  |
| `mode`          | 暫存器所選的 `Mode`：`name`、`height`，以及是否使用較高畫面的表格的 `tall`        |
| `cram`          | 調色盤 RAM：`entry(index)`、`entries()` 和 `write(address, value, handheld_mode)` |
| `sound`         | 晶片內置的聲音產生器                                                              |
| `region`        | `ntsc` 或 `pal`                                                                   |
| `handheld_mode` | Game Gear 晶片是否處於其自身模式                                                  |
| `lost`          | 在前一次存取生效之前就發出的存取次數                                              |
| `model`         | 規範的型號名稱                                                                    |
| `part`          | `Model` 記錄                                                                      |
| `memory`        | 視像記憶體物件                                                                    |
| `cycles`        | 自晶片建立以來的主時鐘節拍數                                                      |

### 模組內容

| 名稱                                       | 內容                                                                              |
| :----------------------------------------- | :-------------------------------------------------------------------------------- |
| `segavdp.MODELS`                           | 三筆 `Model` 記錄，以規範名稱為鍵                                                 |
| `segavdp.Vram(fill=None, seed=UNSET_SEED)` | 16 KB 視像記憶體，即 TMS9918 成員自己的那個                                       |
| `segavdp.port(address)`                    | 處理器連接埠到達哪個暫存器：`data`、`control`、`v counter`、`h counter` 或 `None` |
| `segavdp.NTSC`, `segavdp.PAL`              | 兩個制式名稱                                                                      |
| `segavdp.UnknownModelError`                | 型號名稱缺失或不明時拋出。訊息列出可接受的名稱                                    |
| `segavdp.UnknownRegionError`               | 指定了晶片不支援的制式時拋出                                                      |
| `segavdp.NoStereo`                         | 向主機晶片要求 Game Gear 的立體聲暫存器時拋出                                     |
| `segavdp.__version__`                      | 已安裝的版本                                                                      |

### 模組

每個模組都是構成晶片的一個部件，測試或呼叫方可以直接使用。

| 模組                 | 內容                                            |
| :------------------- | :---------------------------------------------- |
| `segavdp.core`       | 晶片本身、連接埠解碼和存取前置時間              |
| `segavdp.display`    | 在模式 4 和 TMS9918 各模式下每一點顯示甚麼      |
| `segavdp.background` | 模式 4 的背景格、捲動和畫面映射位址             |
| `segavdp.sprites`    | 模式 4 的精靈評估和一行精靈的點                 |
| `segavdp.modes`      | 暫存器所選的模式和畫面高度                      |
| `segavdp.timing`     | 幀的佈局、V 和 H 計數器以及行事件所在的點       |
| `segavdp.palette`    | 兩類晶片的調色盤 RAM、其亮度以及舊模式的顏色    |
| `segavdp.sound`      | 建基於 `ti-sn76489-python` 的晶片內置聲音產生器 |
| `segavdp.models`     | 三筆 `Model` 記錄和制式名稱                     |
| `segavdp.flags`      | 三個狀態旗標                                    |
| `segavdp.errors`     | 這個套件拋出的一切                              |

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

## 行計數器

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

世嘉的手冊說，暫存器 10 要載入比希望中斷的行少一的值。載入 94 時，請求在第 95 行（由 1 數起）開始時到來，並在 95 行之後再來一次。計數器在顯示期間以外重新載入，所以這一幀的第三次請求不會出現。

## 處理器的存取速度

世嘉的手冊說，晶片接收資料的速度不超過顯示期間每 29 個 T 狀態一次、垂直消隱期間每 16 個 T 狀態一次。兩盒針對真實硬件編寫的測試卡帶都比這更快，所以模型在顯示期間令一次存取在前一次之後 26 個 T 狀態生效，在消隱期間則一次也不會遺失。第一次存取仍在等待時到來的第二次存取會取代它。

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

普查把 Master System 和 Game Gear 卡帶庫中的每個映像，放在由這塊晶片、`zilog-z80-python` 處理器和世嘉的分頁組成的電路板上啟動，各執行固定的幀數。`.sms` 映像在 315-5246 上執行，`.gg` 映像在處於其自身模式的 315-5378 上執行。它接受目錄、ZIP 封存和單一映像，按摘要把每個不同的映像只計一次，列印摘要，寫出 [`conformance/corpus.json`](conformance/corpus.json)，並在某項性質被破壞時以 1 結束。

執行由兩項性質把關：模型在任何映像上都不拋出例外，以及每個使用世嘉分頁的零售映像都會開啟顯示。[`conformance/boards.json`](conformance/boards.json) 按 MAME 軟件清單的記錄，以整個檔案的 SHA-1 列出建於其他電路板上的映像，例如 Codemasters 的分頁；這些映像在沒有自身電路板的情況下執行，並另行計算。遺失的存取按映像計算並列出，但不參與把關。

| 上次執行的結果                                         | 數量      |
| :----------------------------------------------------- | :-------- |
| 兩個卡帶庫中的項目                                     | 5,110     |
| 不同的映像                                             | 2,608     |
| 使用世嘉分頁的零售映像，參與把關                       | 794       |
| 建於其他電路板上的映像，在沒有該電路板的情況下執行     | 59        |
| 模式 4，192 行                                         | 2,429     |
| 模式 4，224 行                                         | 8         |
| Graphics II                                            | 68        |
| Graphics I                                             | 29        |
| 設定了 Multicolor 位元的 Text                          | 2         |
| 模式 4 的無效 Text 模式                                | 2         |
| 從未開啟顯示，其中沒有使用世嘉分頁的零售版             | 79        |
| 精靈 8 乘 8                                            | 1,778     |
| 精靈 8 乘 16                                           | 764       |
| 精靈 8 乘 8，已放大                                    | 9         |
| 請求過行中斷                                           | 1,011     |
| 零售版映像上遺失的存取，45% 來自 CJ Elephant Fugitive  | 91,127    |
| 其餘映像上遺失的存取，大多來自公有領域的測試程式和示範 | 2,991,054 |

[`conformance/corpus.json`](conformance/corpus.json) 只保存這些計數，不含任何卡帶內容，因此在沒有卡帶庫的電腦上，測試套件也能核對它們。

## 測試卡帶

```bash
python3 -m conformance.testroms "/path/to/5 Tools & Service Test Carts.zip"
```

[`conformance/testroms.json`](conformance/testroms.json) 按 SHA-256 列出每一盒測試這塊晶片的測試卡帶、每次執行所用的手掣按鍵腳本，以及它顯示的內容。

| 卡帶                                         | 執行於                                        | 記錄的內容                                                                      |
| :------------------------------------------- | :-------------------------------------------- | :------------------------------------------------------------------------------ |
| SEGA Master System TestSuite 0.32，sverx 作  | 60 Hz 的 315-5124，60 Hz 和 50 Hz 的 315-5246 | 其 System Info 頁面正確說出每塊晶片和每種電視制式，沒有遺失存取                 |
| V Counter Test Program，Charles MacDonald 作 | 60 Hz 的 315-5246                             | 其頁面顯示 00h 至 DAh，然後 D5h 至 FFh，與 MacDonald 文件所列一致，沒有遺失存取 |
| Line Interrupt Test #1，Charles MacDonald 作 | 60 Hz 的 315-5246                             | 只作刺激；遺失 1 次存取                                                         |
| Interrupt Test                               | 60 Hz 的 315-5246                             | 只作刺激；沒有遺失存取                                                          |
| BG Test 0.01                                 | 60 Hz 的 315-5124                             | 只作刺激；遺失 721 次存取                                                       |
| Sprite Test                                  | 60 Hz 的 315-5246                             | 只作刺激；遺失 600,408 次存取，顯示期間每 11 及 18 個 T 狀態寫一次              |
| 64 Color Palette Test                        | 60 Hz 的 315-5124                             | 只作刺激；遺失 15,568 次存取                                                    |
| Color & Switch Test                          | 60 Hz 的 315-5124                             | 只作刺激；沒有遺失存取                                                          |
| Palette Tool 1.0                             | 60 Hz 的 315-5246                             | 只作刺激；沒有遺失存取                                                          |

System Info 頁面還會說出主機型號、地區和開機程式。這些由普查用的電路板回答，而不是由這塊晶片回答，所以記錄只保留它們而不作判斷。三盒刺激用卡帶在這裏遺失的寫入，真實主機是否也會遺失仍未清楚；甚麼能解決這個問題見 [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)。

## 是否正確

世嘉印出的、測試能夠觸及的每一項事實都由程式碼核對。[`conformance/hardware.json`](conformance/hardware.json) 記錄每項事實及其原句和頁碼，[`conformance/hardware.test.py`](conformance/hardware.test.py) 和 [`conformance/display.test.py`](conformance/display.test.py) 用它們來驅動晶片。`python3 -m conformance.quotes` 會在所引用的文件中找到每一句引文。

手冊沒有印出的每個值都放在同一檔案的 `notStated` 下，標記為未驗證，並附有來源以及能夠解決它的量度。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 列出仍未解決的問題。兩個來源（包括手冊）互相矛盾的地方見 [`conformance/divergences.json`](conformance/divergences.json)。

## 參與開發

| 需要                             | 位置                                                                |
| :------------------------------- | :------------------------------------------------------------------ |
| 所有檢查及其執行次序             | [CONTRIBUTING.md](CONTRIBUTING.md)                                  |
| 給編碼代理的同樣內容             | [AGENTS.md](AGENTS.md)                                              |
| 本儲存庫與家族其他成員共用的標準 | [FAMILY.md](FAMILY.md)                                              |
| 錯誤報告                         | [GitHub Issues](https://github.com/gufranco/sega-vdp-python/issues) |
| 保安報告                         | [SECURITY.md](SECURITY.md)                                          |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 segavdp/core.test.py
```

每個模組旁邊都有一個以它命名的測試檔案，每個都可以像上面那樣獨立執行。覆蓋率是硬性檢查，陳述式和分支都必須達到 100%。

## 參考資料

- _Software Reference Manual for the SEGA Mark III Console_，世嘉，沒有日期，重新打字版。45 頁，184,840 位元組，SHA-256 `166f09331ba9df055f7a352f10c6a7843911470bc72d9347eda4a0de86e8cfce`。本儲存庫不包含它。`python3 -m conformance.documents` 從 https://segaretro.org/images/d/d6/SoftwareReferenceManualForSegaMarkIIIEU.pdf 下載它，並拒絕任何其他檔案。
- _Sega Master System VDP documentation_，Charles MacDonald，2002 年 11 月 12 日。43,417 位元組，SHA-256 `dc16f8e687b8b137d9f7d457659135ebb7b21e6e7874250fac0719dd1eb6207c`，取自 https://www.smspower.org/uploads/Development/msvdp-20021112.txt 。
- _SN76489_，SMS Power，由 Maxim 維護的頁面的列印檢視。54,534 位元組，SHA-256 `14d146c13d4d98a04b2c2c05498753bc60197696cea1b73860bfa23416cd15ce`，取自 https://www.smspower.org/Development/SN76489?action=print 。
- Genesis Plus GX，提交 `a5834b3df455c49bb97bfaa328c20845831f576b` 時的 `core/hvc.h` 和 `core/vdp_render.c`，https://github.com/ekeeke/Genesis-Plus-GX ，用於 H 計數器、一行中事件的次序以及舊模式的顏色。只採用事實，不取任何程式碼。
- MAME，提交 `94fc55c9692b180dcb608e2e222e48315db5017a` 時的 `hash/sms.xml` 和 `hash/gamegear.xml`，https://github.com/mamedev/mame ，用於卡帶的電路板。只採用事實，不取任何程式碼。

## 引用本項目

[CITATION.cff](CITATION.cff) 在每次發佈時由寫入套件版本號的腳本更新。

## 授權

MIT。見 [LICENSE](LICENSE)。
