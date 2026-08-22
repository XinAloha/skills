# 数据完整性 / Checksum Mismatch

## 症状

```
RuntimeError: parquet checksum mismatch
expected: a3f...   actual: b7c...
```

或：

```
RuntimeError: splits.json checksum mismatch
```

## 原因

| 来源 | 说明 |
|---|---|
| `stock_data/*.parquet` 被改 | 数据被替换 / 被新数据覆盖 / 被 prepare.py 之外的代码写入 |
| `cache/splits.json` 被改 | 切分定义被人为修改 |
| 文件系统问题 | 磁盘错误 / git checkout 拉到了不一致的版本 |

## 修复

### Case 1：数据真的没变（误报）

```bash
# 看 git status，是不是有未提交的修改
git status stock_data/

# 如果文件大小、mtime 都没变，但 checksum 不一致：
# 可能是 prepare.py 的 hash 算法被改过
git log prepare.py | head
```

### Case 2：数据真的换了（如新一期数据）

```bash
# 1. 确认新数据是预期的
ls -la stock_data/

# 2. 删掉旧 splits.json，让 prepare.py 重新冻结切分
rm cache/splits.json

# 3. 跑一次 prepare 验证
py prepare.py
# 期望：splits.json 重新生成，checksum 校验通过
```

⚠️ **重新冻结切分意味着 train / val / test 的日期范围可能变化**，所有历史因子卡的可比性受影响。这是"重置 journal"级别的操作，谨慎。

### Case 3：parquet 被无意修改

```bash
# 从 git 恢复
git checkout stock_data/

# 或从备份恢复
cp /backup/stock_data/* stock_data/
```

## 不要做

- ❌ 自己重写 checksum 逻辑绕过 —— 这破坏了数据完整性保证
- ❌ 直接把 expected checksum 改成 actual —— 同上
- ❌ 修改 splits.json 的日期范围 —— 切分宪法被破

## checksum 的价值

- 防止"数据偷偷换了，因子卡却号称在同一份数据上跑的"
- 防止"实验之间数据不一致，分数不可比"
- 强制"换数据 = 重置整个研究阶段"

这是研究纪律的护栏，不是技术 bug。
