"""B10 测试包。

按职责拆为五份：

- ``fixtures``：共用的样本生成函数（make_sample / make_pool_sample / make_research_sample）。
- ``test_data_io``：输入校验 / 字段映射 / 主键 / 类型边界。
- ``test_run_metrics``：run() 输出 schema、IC/分层语义、方向调整、binary_success、bootstrap、cost。
- ``test_visual_report``：HTML 渲染、图表占位、性能拆分（make_group_reports 复用 base）。
- ``test_research_diagnostics``：研究层 V7 输出与中性化 supplied panel 路径。
- ``test_write_production``：生产写入往返、append upsert、daily_runner 当前行选择。

聚合入口：``test.py`` 仍可 ``python scripts/test.py`` 跑，本质等价于
``python -m pytest scripts/tests``。
"""
