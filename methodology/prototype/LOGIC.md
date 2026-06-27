# Logic Prototype - 逻辑原型

一个**让用户手动驱动状态模型**的小交互式终端 app。当问题是关于**业务逻辑、状态转换、数据形状**——那种纸面看着合理、真跑起来才知道哪里不对的——用这个分支。

## 适用的问题形状

- "我不确定这个状态机能不能处理 X 然后 Y 的边界情况。"
- "这个数据模型真的能表示 ... 这种情况吗？"
- "我想在写之前感受一下 API 应该长什么样。"
- 任何用户想**按按钮看状态变化**的场景。

如果问题是"这应该长什么样" —— 错分支。用 [UI.md](UI.md)。

## 流程

### 1. 写下问题

写代码前，写下你在原型化什么状态模型、回答什么问题。一段，写在原型 README 或文件顶部注释。**回答错问题的逻辑原型 = 纯浪费**——把问题显式化，可被检查；用户不在场也可被回看。

### 2. 选语言

用 host 项目的语言。**本项目用 Python**。匹配项目现有约定——别为了原型引入新包管理器或运行时。

### 3. 把逻辑隔离在一个可移植模块里

把"实际在回答问题的那段逻辑"放到一个**小、纯**的接口背后，未来能整段抠出来塞到真实代码里。围绕它的 TUI 是一次性的；**逻辑模块不是**。

形状取决于问题：

- **纯 reducer** —— `(state, action) -> state`。适合"动作离散、状态是单一值"。
- **状态机** —— 显式的状态与转换。适合"当前哪些动作合法"也是问题的一部分。
- **一组纯函数**操作普通数据类型。适合"没有隐含当前状态、只是变换"。
- **一个有清晰方法表面的类 / 模块**。适合"逻辑确实拥有持续的内部状态"。

按**最适合问题**的形状选，**不是按"最容易接 TUI"**的形状选。**保持纯**：无 I/O、无终端代码、没有用 `print` 控制流。TUI 导入它、调用它；反方向不流。

这是原型超出自身寿命还有用的关键：**问题答完后，验证过的 reducer / machine / 函数集可被抠到真实模块**——TUI 外壳直接删。

### 4. 建最小的、暴露状态的 TUI

做成轻量 TUI ——每 tick 清屏（Python 用 `print("\033[2J\033[H")` 或 `os.system("cls" if os.name=="nt" else "clear")`），重渲染整帧。**用户永远只看到一个稳定视图**，不是一直滚动的 scrollback。

每帧两部分，按顺序：

1. **当前状态**，pretty-print，diff 友好（每行一个字段，或格式化 JSON）。**bold** 用于字段名 / 区段标题，**dim** 用于次要上下文（时间戳、ID、衍生值）。本项目可直接用 ANSI 转义 `\x1b[1m`（bold）/ `\x1b[2m`（dim）/ `\x1b[0m`（reset）。
2. **键盘快捷键**，列在底部：`[a] add stock  [d] delete stock  [t] tick clock  [q] quit`。

行为：

1. **初始化状态**——一个内存对象。启动时渲染第一帧。
2. **一次读一个键**（或一行），分发到 handler 改状态。
3. **每次动作后重渲染整帧**——不要追加，要替换。
4. **循环到退出**。

整帧应能放进一屏。

### 5. 一条命令能跑

加进项目的任务运行器或 Makefile。本项目示例：

```bash
# 在 scripts/prototypes/ 下
python scripts/prototypes/retry_state_machine.py
```

如果 host 项目没有任务运行器，原型 README 顶部写出命令。

### 6. 交付

把命令告诉用户。他们自己驱动；有趣的瞬间是他们说"等等，这不应该可能"或"嗯，我以为 X 会不一样"——那些就是**想法本身的 bug**，正是这个原型的全部目的。要加新动作就加。原型是会演化的。

### 7. 捕获答案

原型干完活，**问题的答案是唯一值得保留的东西**。用户在场，问他们学到什么。不在场，原型旁留 `NOTES.md` 让答案能填上去（如果你看了会话，你来填）——**填完再删**。

## 反模式

- **不要加测试**。需要测试的原型不再是原型。
- **不要接真实数据库**。用内存 store——除非问题就是关于持久化（用临时 SQLite 文件）。
- **不要泛化**。"如果以后想支持 X"——不要。原型只回答一个问题。
- **不要把逻辑和 TUI 搅在一起**。如果 reducer / state machine 引用了 `print`、prompt、终端转义码，它就不再可移植。**TUI 是逻辑的薄壳**。
- **不要把 TUI 外壳带进生产**。外壳是为"手动驱动"优化的。**值得保留的是 TUI 后面的逻辑模块**。

## 本项目典型示例

```python
# scripts/prototypes/fallback_state_machine.py

from dataclasses import dataclass, field

@dataclass
class State:
    current_source: str = "tushare"
    failures: dict = field(default_factory=dict)
    last_data: str | None = None

def reduce(state: State, action: str) -> State:
    """纯 reducer：可被抠到 data_collection/core/fallback.py"""
    ...

def render(state: State) -> str:
    """纯渲染：仅给 TUI 用，不会被抠走"""
    ...

def main():
    state = State()
    while True:
        print("\033[2J\033[H" + render(state))
        key = input("> ").strip()
        if key == "q": break
        state = reduce(state, key)

if __name__ == "__main__":
    main()
```
