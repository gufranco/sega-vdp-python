# Sega VDP

Sega の 315-5124、315-5246、315-5378 ビデオディスプレイプロセッサを、それぞれに内蔵されたサウンドジェネレータとともに Python で実装したものです。マスタークロック 1 ティックずつ進み、Sega の Mark III リファレンスマニュアルに照らして検証されています。

[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/sega-vdp-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sega-vdp-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/sega-vdp-python)](https://github.com/gufranco/sega-vdp-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

異なるマスターシステムとゲームギアのイメージ **2,608** 本をそれぞれ **600** フレーム起動、Sega のページングを使う市販の **794** 本で性質の不合格 **0** 件、マニュアル内で所在を確認した引用 **64** 件、**3** 品種、テスト **862** 件、ステートメントとブランチのカバレッジ **100%**、標準ライブラリとファミリーの 2 つのメンバー以外への依存関係なし

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

パーツはレジスタ、カラー RAM、ビデオメモリがランダムな状態で起動するため、例ではまずリセットし、ステータスを一度読んで書きかけのコマンドをクリアしています。5 回のレジスタ書き込みでモード 4 を選び、表示をオンにし、スクリーンマップを 3800h に置き、両方のスクロールをゼロにします。2 回のカラー RAM 書き込みで色 0 を黒、色 1 を白にします。スクリーンマップの最初のセルはパターン 1 で、その最上段は色 1 のドット 1 つから始まります。ライン 0 を 2 回待つのは、実機と同じく垂直スクロールをフレームの先頭でラッチさせるためです。

## インストール

| 要件   | バージョン                       |
| :----- | :------------------------------- |
| Python | 3.12 以降                        |
| git    | 任意。サブモジュールの取得に使用 |

```bash
git clone --recurse-submodules https://github.com/gufranco/sega-vdp-python.git
cd sega-vdp-python
export PYTHONPATH=.:ti-tms9918-python:ti-sn76489-python
python3 segavdp/doctor.py
```

このパッケージは、ファミリーの他の 2 つのメンバーをコピーせずに組み合わせています。TMS9918 のモードは `ti-tms9918-python` から、サウンドジェネレータは `ti-sn76489-python` から来ており、どちらもインポートパス上の git サブモジュールで、`PYTHONPATH` の行がそれを設定します。3 つ目のサブモジュール `zilog-z80-python` は、全数調査とテストカートリッジを動かします。ダウンロード ZIP のリンクから得たソースアーカイブにはサブモジュールが含まれず、実行できません。代わりに `--recurse-submodules` を付けてクローンしてください。このようにメンバーを取り込んでいるため、このパッケージはインデックスからインストールできず、そこには何も公開しません。

doctor はマシンとチェックアウトを調べ、最後に 1 行を出力します。バグ報告には、その出力全体を貼り付けてください。

```
  11 checks, nothing to report
```

リリースは [Semantic Versioning](https://semver.org/) に従い、semantic-release がコミット履歴から作成します。すべてのリリースにはタグが付けられ、[リリースページ](https://github.com/gufranco/sega-vdp-python/releases)に掲載されます。

## インターフェース

`segavdp.Chip(model, memory=None, seed=UNSET_SEED, region=None, handheld_mode=None)` はパーツを 1 つ構築します。`model` は必須です。`memory` は `read8(address)` と `write8(address, value)` を持つ任意のオブジェクトで、省略するとパーツがランダムな 16 KB の `Vram` を作ります。`region` は `ntsc` か `pal` で、省略するとそのパーツが動作する最初の方式になります。`handheld_mode` はゲームギアのパーツを独自モードにします。起動時はこのモードで、コンソール用のパーツでは常にオフです。

| モデル     | 別名                              | 方式          | 画面                 | 横方向の拡大 | レガシーモードの色   |
| :--------- | :-------------------------------- | :------------ | :------------------- | :----------- | :------------------- |
| `315-5124` | `5124`, `sms`, `mark3`, `markiii` | `ntsc`, `pal` | 192 ライン           | 4 スプライト | 固定の表             |
| `315-5246` | `5246`, `sms2`                    | `ntsc`, `pal` | 192、224、240 ライン | 8 スプライト | 固定の表             |
| `315-5378` | `5378`, `gg`, `gamegear`          | `ntsc`        | 192、224 ライン      | 8 スプライト | カラー RAM の 16〜31 |

### 呼び出し

| 呼び出し                     | 効果                                                                                                                 |
| :--------------------------- | :------------------------------------------------------------------------------------------------------------------- |
| `reset()`                    | レジスタ 0 と 1、ステータスフラグ、書きかけのコマンドをクリアし、ビームをライン 0 の先頭に移します。パーツを返します |
| `write_control(value)`       | コントロールポートへの 1 バイト。2 ビットのコマンド付きアドレスの半分、またはレジスタ書き込みの半分                  |
| `write_data(value)`          | ビデオメモリ、またはコマンド 3 の後ならカラー RAM への 1 バイト。アクセスのリードの後に書き込まれます                |
| `read_data()`                | リードバッファを返し、次のバイトを取り込みます                                                                       |
| `read_status()`              | ステータスバイトを返し、フレーム、オーバーフロー、衝突の各フラグと保留中のライン割り込みをクリアします               |
| `read_v_counter()`           | 現在のラインの V カウンタ                                                                                            |
| `read_h_counter()`           | 最後にラッチされた H カウンタ                                                                                        |
| `latch_h_counter()`          | コントローラの TH ラインの変化と同じく、H カウンタをラッチします                                                     |
| `write_sound(value)`         | パーツに内蔵されたサウンドジェネレータへの 1 バイト                                                                  |
| `read_port(address)`         | 40h から BFh までを A7、A6、A0 でデコードした読み出し。範囲外では `None`                                             |
| `write_port(address, value)` | 同じデコードによる書き込み。データ、コントロール、またはサウンドジェネレータ                                         |
| `tick()`                     | マスタークロック 1 周期。プロセッサクロックの 3 分の 1                                                               |
| `clock()`                    | 1 ドット、つまり 2 ティック                                                                                          |
| `run_dots(count)`            | `count` ドット                                                                                                       |

### 状態

| 属性            | 意味                                                                                                  |
| :-------------- | :---------------------------------------------------------------------------------------------------- |
| `line`          | 最初の表示ラインから数えたライン番号。そのラインの最初の表示ドットの 76 ドット前に進みます            |
| `dot`           | 最初の表示ドットから数えたドット番号                                                                  |
| `shown`         | 直前のドットが `active`、`border`、`blanking`、`sync`、`burst` のどれだったか                         |
| `colour`        | 直前のドットのカラー RAM 値。コンソール用パーツでは 6 ビット、ゲームギアでは 12 ビット、または `None` |
| `interrupt`     | INT ピンがアサートされている間 True                                                                   |
| `status`        | 3 つのステータスフラグ。何もクリアせずに読みます                                                      |
| `registers`     | 11 個のレジスタ。`bytearray`                                                                          |
| `mode`          | レジスタが選ぶ `Mode`。`name`、`height`、高い画面の表を使っているかどうかの `tall`                    |
| `cram`          | カラー RAM。`entry(index)`、`entries()`、`write(address, value, handheld_mode)`                       |
| `sound`         | パーツに内蔵されたサウンドジェネレータ                                                                |
| `region`        | `ntsc` または `pal`                                                                                   |
| `handheld_mode` | ゲームギアのパーツが独自モードかどうか                                                                |
| `lost`          | 直前のアクセスが反映される前に要求されたアクセスの数                                                  |
| `model`         | 正式なモデル名                                                                                        |
| `part`          | `Model` レコード                                                                                      |
| `memory`        | ビデオメモリのオブジェクト                                                                            |
| `cycles`        | パーツを構築してからのマスタークロックのティック数                                                    |

### モジュールの内容

| 名前                                       | 内容                                                                                                |
| :----------------------------------------- | :-------------------------------------------------------------------------------------------------- |
| `segavdp.MODELS`                           | 3 つの `Model` レコード。正式名がキー                                                               |
| `segavdp.Vram(fill=None, seed=UNSET_SEED)` | 16 KB のビデオメモリ。TMS9918 メンバーのもの                                                        |
| `segavdp.port(address)`                    | プロセッサのポートがどのレジスタに届くか。`data`、`control`、`v counter`、`h counter` または `None` |
| `segavdp.NTSC`, `segavdp.PAL`              | 2 つの方式名                                                                                        |
| `segavdp.UnknownModelError`                | モデル名がない、または未知のときに送出。メッセージに受け付ける名前を列挙します                      |
| `segavdp.UnknownRegionError`               | パーツが動作しない方式を指定したときに送出                                                          |
| `segavdp.NoStereo`                         | コンソール用パーツにゲームギアのステレオレジスタを求めたときに送出                                  |
| `segavdp.__version__`                      | インストールされているバージョン                                                                    |

### モジュール

各モジュールはパーツを構成する部品で、テストや呼び出し側が直接使うことができます。

| モジュール           | 内容                                                                 |
| :------------------- | :------------------------------------------------------------------- |
| `segavdp.core`       | パーツ本体、ポートのデコード、アクセスのリード                       |
| `segavdp.display`    | モード 4 と TMS9918 のモードで各ドットに何が表示されるか             |
| `segavdp.background` | モード 4 の背景セル、スクロール、スクリーンマップのアドレス          |
| `segavdp.sprites`    | モード 4 のスプライト評価と、1 ライン分のスプライトのドット          |
| `segavdp.modes`      | レジスタが選ぶモードと画面の高さ                                     |
| `segavdp.timing`     | フレームの構成、V と H のカウンタ、ラインイベントのドット            |
| `segavdp.palette`    | 両方の種類のパーツのカラー RAM、その輝度、レガシーモードの色         |
| `segavdp.sound`      | `ti-sn76489-python` の上に作られた、パーツ内蔵のサウンドジェネレータ |
| `segavdp.models`     | 3 つの `Model` レコードと方式名                                      |
| `segavdp.flags`      | 3 つのステータスフラグ                                               |
| `segavdp.errors`     | パッケージが送出するすべての例外                                     |

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

## ラインカウンタ

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

Sega のマニュアルは、割り込みを起こしたいラインより 1 少ない値をレジスタ 10 に入れるよう指示しています。94 なら 1 から数えて 95 番目のラインが始まるときに要求が来て、さらに 95 ライン後にもう一度来ます。カウンタは表示期間の外で再ロードされるため、そのフレームの 3 回目の要求は来ません。

## プロセッサのアクセス速度

Sega のマニュアルは、パーツがデータを受け取れるのは表示期間中は 29 T ステートごと、垂直ブランキング中は 16 T ステートごとが限度だとしています。実機を相手に書かれた 2 つのテストカートリッジはどちらもそれより速いため、モデルは表示期間中は直前のアクセスから 26 T ステート後にアクセスを反映し、ブランキング中は一つも失いません。最初のアクセスがまだ待っている間に 2 つ目が来ると、2 つ目が最初のものを置き換えます。

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

## 全数調査

```bash
python3 -m conformance.census "external/Master EverDrive" "external/EverDrive GG" --frames 600 --jobs 12
```

全数調査は、マスターシステムとゲームギアのライブラリにあるすべてのイメージを、このパーツ、`zilog-z80-python` プロセッサ、Sega のページングで作ったボード上で起動し、それぞれ決まったフレーム数だけ動かします。`.sms` イメージは 315-5246 で、`.gg` イメージは独自モードの 315-5378 で動きます。ディレクトリ、ZIP アーカイブ、単体のイメージを受け付け、異なるイメージをダイジェストで 1 回ずつ数え、要約を出力し、[`conformance/corpus.json`](conformance/corpus.json) を書き出し、性質が破れると 1 で終了します。

実行を判定する性質は 2 つです。どのイメージでもモデルが例外を送出しないこと、そして Sega のページングを使う市販のイメージがすべて表示をオンにすることです。[`conformance/boards.json`](conformance/boards.json) は、MAME のソフトウェアリストの記録に従い、Codemasters のページングのような別のボードで作られたイメージをファイル全体の SHA-1 で挙げています。それらは自分のボードなしで動かされ、別に数えられます。失われたアクセスはイメージごとに数えて名前を挙げますが、判定には使いません。

| 直近の実行の結果                                                                 | 件数      |
| :------------------------------------------------------------------------------- | :-------- |
| 2 つのライブラリにある項目                                                       | 5,110     |
| 異なるイメージ                                                                   | 2,608     |
| Sega のページングを使う市販イメージ。判定の対象です                              | 794       |
| 別のボードのイメージ。そのボードなしで動かしました                               | 59        |
| モード 4、192 ライン                                                             | 2,429     |
| モード 4、224 ライン                                                             | 8         |
| Graphics II                                                                      | 68        |
| Graphics I                                                                       | 29        |
| Multicolor のビットが立った Text                                                 | 2         |
| モード 4 の無効な Text モード                                                    | 2         |
| 表示をオンにしなかったもの。Sega のページングを使う市販品は含まれません          | 79        |
| 8×8 のスプライト                                                                 | 1,778     |
| 8×16 のスプライト                                                                | 764       |
| 8×8 のスプライト、拡大あり                                                       | 9         |
| ライン割り込みを要求したもの                                                     | 1,011     |
| 市販イメージで失われたアクセス。45% は CJ Elephant Fugitive のものです           | 91,127    |
| それ以外で失われたアクセス。大半はパブリックドメインのテストプログラムとデモです | 2,991,054 |

[`conformance/corpus.json`](conformance/corpus.json) はそれらの数だけを保持し、カートリッジの中身は一切含まないため、ライブラリのないマシンでもテストスイートがそれを確かめられます。

## テストカートリッジ

```bash
python3 -m conformance.testroms "/path/to/5 Tools & Service Test Carts.zip"
```

[`conformance/testroms.json`](conformance/testroms.json) は、このパーツを動かすすべてのテストカートリッジを SHA-256 で挙げ、各実行が行うコントローラ入力の手順と、表示された内容を記録しています。

| カートリッジ                                 | 実行したパーツ                                | 記録の内容                                                                                                            |
| :------------------------------------------- | :-------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------- |
| SEGA Master System TestSuite 0.32、sverx 作  | 60 Hz の 315-5124、60 Hz と 50 Hz の 315-5246 | System Info ページが各パーツと各テレビ方式を正しく名指しし、失われたアクセスはありません                              |
| V Counter Test Program、Charles MacDonald 作 | 60 Hz の 315-5246                             | ページに 00h から DAh、続いて D5h から FFh が表示され、MacDonald の文書の値と一致します。失われたアクセスはありません |
| Line Interrupt Test #1、Charles MacDonald 作 | 60 Hz の 315-5246                             | 刺激のみ。失われたアクセス 1                                                                                          |
| Interrupt Test                               | 60 Hz の 315-5246                             | 刺激のみ。失われたアクセスなし                                                                                        |
| BG Test 0.01                                 | 60 Hz の 315-5124                             | 刺激のみ。失われたアクセス 721                                                                                        |
| Sprite Test                                  | 60 Hz の 315-5246                             | 刺激のみ。失われたアクセス 600,408。表示中に 11 と 18 T ステートごとに書き込みます                                    |
| 64 Color Palette Test                        | 60 Hz の 315-5124                             | 刺激のみ。失われたアクセス 15,568                                                                                     |
| Color & Switch Test                          | 60 Hz の 315-5124                             | 刺激のみ。失われたアクセスなし                                                                                        |
| Palette Tool 1.0                             | 60 Hz の 315-5246                             | 刺激のみ。失われたアクセスなし                                                                                        |

System Info ページはコンソールの機種、地域、ブートプログラムも表示します。それらはこのパーツではなく全数調査用のボードが答えるものなので、記録は判断せずにそのまま残しています。3 つの刺激用カートリッジがここで失う書き込みを実機も失うかどうかはわかっていません。何がそれを決着させるかは [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) にあります。

## 正しいかどうか

Sega が印刷した事実のうち、テストが届くものはすべてコードで確かめられています。[`conformance/hardware.json`](conformance/hardware.json) は各事実をその文とページとともに保持し、[`conformance/hardware.test.py`](conformance/hardware.test.py) と [`conformance/display.test.py`](conformance/display.test.py) がパーツをそれらに照らして動かします。`python3 -m conformance.quotes` は、引用されたすべての文を、それが名指しする文書の中に見つけます。

マニュアルに印刷されていない値はすべて同じファイルの `notStated` の下にあり、未検証と記され、出典と、それを決着させる測定が付いています。[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) はまだ開いているものを挙げています。2 つの出典が食い違う箇所は、マニュアルを含め [`conformance/divergences.json`](conformance/divergences.json) にあります。

## 開発に参加する

| 必要なもの                                   | 場所                                                                |
| :------------------------------------------- | :------------------------------------------------------------------ |
| すべてのゲートとその実行順                   | [CONTRIBUTING.md](CONTRIBUTING.md)                                  |
| コーディングエージェント向けの同じ内容       | [AGENTS.md](AGENTS.md)                                              |
| このリポジトリがファミリーの他と共有する標準 | [FAMILY.md](FAMILY.md)                                              |
| バグ報告                                     | [GitHub Issues](https://github.com/gufranco/sega-vdp-python/issues) |
| セキュリティ報告                             | [SECURITY.md](SECURITY.md)                                          |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 segavdp/core.test.py
```

各モジュールには、その名を持つテストファイルが隣にあり、それぞれ上のように単独で実行できます。カバレッジは文と分岐の両方で 100% が必須のゲートです。

## 参考文献

- _Software Reference Manual for the SEGA Mark III Console_、Sega、日付なし、打ち直し版。45 ページ、184,840 バイト、SHA-256 `166f09331ba9df055f7a352f10c6a7843911470bc72d9347eda4a0de86e8cfce`。このリポジトリには含まれていません。`python3 -m conformance.documents` が https://segaretro.org/images/d/d6/SoftwareReferenceManualForSegaMarkIIIEU.pdf からダウンロードし、それ以外のファイルは拒否します。
- _Sega Master System VDP documentation_、Charles MacDonald、2002 年 11 月 12 日。43,417 バイト、SHA-256 `dc16f8e687b8b137d9f7d457659135ebb7b21e6e7874250fac0719dd1eb6207c`、https://www.smspower.org/uploads/Development/msvdp-20021112.txt から取得。
- _SN76489_、SMS Power、Maxim が管理するページの印刷用表示。54,534 バイト、SHA-256 `14d146c13d4d98a04b2c2c05498753bc60197696cea1b73860bfa23416cd15ce`、https://www.smspower.org/Development/SN76489?action=print から取得。
- Genesis Plus GX、コミット `a5834b3df455c49bb97bfaa328c20845831f576b` 時点の `core/hvc.h` と `core/vdp_render.c`、https://github.com/ekeeke/Genesis-Plus-GX 。H カウンタ、ライン内のイベントの順序、レガシーモードの色に使用しています。事実のみを利用し、コードは一切取り込んでいません。
- MAME、コミット `94fc55c9692b180dcb608e2e222e48315db5017a` 時点の `hash/sms.xml` と `hash/gamegear.xml`、https://github.com/mamedev/mame 。カートリッジのボードに使用しています。事実のみを利用し、コードは一切取り込んでいません。

## 引用

[CITATION.cff](CITATION.cff) は、パッケージのバージョンを刻むスクリプトによってリリースごとに更新されます。

## ライセンス

MIT。[LICENSE](LICENSE) を参照してください。
