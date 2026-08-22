# Adapter 协议

这个 skill 不假定用户的因子、特征或 pipeline 有固定接口。Adapter 的作用是把任意项目对象接到数值因果性测试。

## 必需函数

```python
def discover_cases(config: dict) -> list[dict]:
    """返回要批量检查的 case。单对象检查也返回一个 case。"""

def load_input(case: dict, config: dict):
    """加载该 case 的完整输入。输入可以是 DataFrame、dict、panel、文件路径集合或任意对象。"""

def run_target(input_obj, case: dict, config: dict):
    """运行被检查计算，返回输出对象。"""

def make_prefix(input_obj, cut: int, case: dict, config: dict):
    """只保留 cut 及以前的历史输入。"""

def mutate_future(input_obj, cut: int, case: dict, config: dict):
    """保持 cut 及以前输入不变，替换 cut 之后的未来输入。"""

def compare_outputs(full_output, test_output, cut: int, case: dict, config: dict) -> dict:
    """比较 cut 及以前的历史输出，返回 max_abs_diff、bad_points 等字段。"""
```

## 推荐可选函数

```python
def case_id(case: dict) -> str:
    """返回稳定 case 名称。"""

def input_length(input_obj, case: dict, config: dict) -> int:
    """返回时间轴长度，用于自动生成 checkpoints。"""

def choose_checkpoints(input_obj, case: dict, config: dict) -> list[int]:
    """完全自定义 checkpoints。"""

def setup_worker(config: dict) -> None:
    """多进程 worker 初始化，例如设置路径或环境变量。"""
```

## 返回字段约定

`compare_outputs()` 至少返回：

```python
{
    "max_abs_diff": 0.0,
    "bad_points": 0,
    "first_bad_idx": "",
}
```

可选返回：

```python
{
    "diff_metric": "absolute",
    "compared_points": 1000,
    "notes": "..."
}
```

runner 会根据 `max_abs_diff` 和 `bad_points` 判定 `PASS/WARN/FAIL`。如果比较逻辑更复杂，adapter 可以直接返回 `status`。

## 批量检测

批量检测一批因子时，`discover_cases()` 返回多个 case，例如：

```python
def discover_cases(config):
    root = Path(config["factor_dir"])
    return [
        {"case_id": path.stem, "path": str(path)}
        for path in sorted(root.glob("*.py"))
    ]
```

case 可以代表：

- 一个因子文件
- 一个参数组合
- 一个标签生成任务
- 一个 pipeline 节点
- 一个市场/品种/股票池切片
- 一个训练样本构建任务

## 设计建议

- Adapter 应尽量薄，不要把目标计算重写一遍。
- 比较口径要和生产输出一致，但只比较 checkpoint 及以前的历史部分。
- 未来扰动要足够强，让未来依赖更容易暴露。
- 如果目标计算有随机性，要固定 seed 或在报告中标记不确定性。
- 如果目标计算依赖缓存，prefix/mutation run 之间要隔离缓存或清理状态。
