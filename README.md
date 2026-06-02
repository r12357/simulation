# Phase Oscillator Studio

Kuramoto モデルを中心とした位相振動子ネットワークを、円周上の発信機として操作・観察する PySide6 GUI アプリです。

## 起動方法

Python 3.10 以上を用意し、PowerShell で次を実行してください。

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

## 画面の使い方

- `開始` / `一時停止`: シミュレーションの時間発展を切り替えます。
- `1 step`: 停止中でも少しだけ時間を進めます。
- `ランダム配置へ戻す`: 位相をランダム配置に戻し、時刻を 0 にします。
- 円周上の発信機: 発信機をクリックして選択し、ドラッグすると円周上の位置、すなわち位相を変更できます。円周上の別の場所をクリックすると、選択中の発信機を移動できます。
- `発信機数`: 発信機の個数を変更します。
- `結合強度 K`: 発信機どうしの結合の強さを変更します。
- `周波数ばらつき`: 各発信機が持つ固有角周波数のばらつきを変更します。
- `進行速度`: 画面上での時間発展の速度を変更します。
- `関数プリセット`: 結合関数をプルダウンから選択します。
- `プリセット例を配置`: 選択中のプリセットに対応する代表的な配置を表示します。

## 実装したプリセット

`reference.pdf` の記述に基づき、全結合ネットワークとして以下を実装しています。

- `Kuramoto: sync`: 引力型の正弦結合です。位相同期へ向かいます。
- `Repulsive: phase balancing`: PDF の式 (34) に対応する反発型の正弦結合です。
- `Harmonics: (m, n)-pattern`: PDF の式 (35) を参考にした高調波結合です。`m=2` から `m=6` まで用意しています。
- `Mixed harmonics: sync`: 1 次と 2 次の引力型高調波を混ぜ、同期を強めます。
- `Pure harmonic: 2 clusters`: 2 次高調波のみを使い、2 クラスタを形成します。
- `Pure harmonic: 3 clusters`: 3 次高調波のみを使い、3 クラスタを形成します。
- `Sakaguchi-Kuramoto: phase lag`: 位相遅れ `pi / 4` を含む正弦結合です。
- `Mixed: attractive / repulsive`: 1 次の引力型結合と 2 次の反発型結合を競合させます。
- `Cyclic neighbors: cotangent flow`: 番号順で隣接する発信機だけを参照する cotangent flow です。

状態欄では秩序パラメータと高調波の秩序パラメータから、`phase synchronization`、`phase balancing`、`splay state`、`(m,n)-pattern`、遷移中の状態を分類します。

## Cyclic neighbors: cotangent flow

`Cyclic neighbors: cotangent flow` では、次の式を使います。

```text
dot(theta_i) =
    1 / 2 * (
        cot((theta_i - theta_(i-1)) / 2)
        - cot((theta_(i+1) - theta_i) / 2)
    )
```

添字は周期境界として扱い、`theta_(n+1) = theta_0`、`theta_(-1) = theta_n` とします。NumPy 配列上では、末尾と先頭も隣接します。

このプリセットは指定式そのものを時間発展に使います。そのため、選択中は GUI の `結合強度 K` と `周波数ばらつき` が無効になります。位相が衝突した場合に cotangent が発散するため、実装では分母が極めて小さい場合だけ数値的に正則化しています。

## 関数プリセットを追加する

GUI 上からプリセットを追加する機能はありません。`presets.py` の末尾で `_register_defaults()` の後に登録コードを追加してください。結合関数は、位相差の NumPy 配列を受け取り、同じ形状の配列を返します。

```python
import numpy as np

register_preset(
    CouplingPreset(
        key="custom_two_harmonics",
        label="Custom: two harmonics",
        description="Example custom coupling function.",
        coupling=lambda delta: -np.sin(delta) - 0.25 * np.sin(2 * delta),
        suggested_clusters=1,
    )
)
```

`key` は他のプリセットと重複しない文字列にしてください。追加後にアプリを再起動すると、プルダウンへ反映されます。

全結合の位相差関数ではなく、位相配列全体から速度を直接求めたい場合は `coupling` の代わりに `phase_velocity` を指定します。

```python
register_preset(
    CouplingPreset(
        key="custom_direct_velocity",
        label="Custom: direct velocity",
        description="Example direct phase-velocity field.",
        phase_velocity=lambda phases: np.sin(np.roll(phases, 1) - phases),
    )
)
```

`coupling` と `phase_velocity` は、どちらか片方だけを指定してください。

## テスト

GUI と分離した数値計算部分は、標準ライブラリの `unittest` で確認できます。

```powershell
python -m unittest discover -s tests -v
```
