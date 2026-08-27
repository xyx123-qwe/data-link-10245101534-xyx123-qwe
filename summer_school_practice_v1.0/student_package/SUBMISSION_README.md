# 数据链软件暑期学校 M1-M6 提交说明

## 基本信息

- 姓名：谢扬暄
- 学号：10245101534
- GitHub用户名：xyx123-qwe
- Python版本：3.13.5
- 是否使用SQLite：否，M3 必做部分使用 CSV
- M4候选来源：学校预生成候选

## 安装与运行

在课程包根目录执行：

`./.venv/bin/python environment/run_student_checks.py`

`./.venv/bin/python student_package/src_skeleton/run_all.py`

## 程序入口

统一入口为 `student_package/src_skeleton/run_all.py`。主要模块顺序为 M2 解析与编解码、M3 航迹与当前态势、M4 语义映射、M5 一致性检查、M6 输出整理。

## 输入文件

- M2：student_package/data/raw_states.json
- M3：student_package/data/partner_messages_multitime.bin
- M4：student_package/output/current_situation.csv、student_package/data/m4/partner_current_situation.csv、student_package/reference/pre_generated_mapping_candidate.csv
- M5：student_package/data/m5/anomaly_cases.csv、student_package/data/m5/anomaly_rules.csv

## 输出文件

输出位于 `student_package/output/`，包括 encoded_messages.bin、decoded_partner_states.csv、validation_log.csv、roundtrip_report.csv、decoded_multitime.csv、track_table.csv、current_situation.csv、llm_mapping_candidate.csv、verified_mapping_table.csv、unified_situation.ndjson、alert_log.csv、quality_situation.csv、M4/M5说明文件。

## 实验结果

M2 从 5 条 OpenSky 样例中生成 3 帧合法 TeachingLink 消息，二进制长度 123 字节。M3 解码 9 帧多时刻消息，形成 3 个目标的航迹和当前态势。M4 生成 6 条统一态势记录。M5 识别 5 条告警，其中 HIGH=1，MEDIUM=4。

## 已知限制

SQLite 为选做，本次未使用。TeachingLink 是课程教学协议，不对应真实装备或行业标准。M4 使用学校预生成候选，并完成人工核验修正。

## 最终提交信息

- 仓库链接：https://github.com/xyx123-qwe/data-link-10245101534-xyx123-qwe
- 最终commit ID：最终提交后填写
- 最后检查日期：2026-08-27

