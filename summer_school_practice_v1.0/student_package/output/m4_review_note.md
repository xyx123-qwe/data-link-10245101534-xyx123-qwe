# M4 AI辅助映射核验说明

- 候选来源：学校预生成候选
- 使用的提示或候选文件：student_package/reference/pre_generated_mapping_candidate.csv
- 发现的字段、单位、层次、有效性或来源问题：
  - 预生成候选将 TeachingLink latitude_code 映射到 position.lon，实际应映射到 position.lat。
  - 预生成候选将 TeachingLink longitude_code 映射到 position.lat，实际应映射到 position.lon。
  - altitude_code 不能直接作为高度，必须按 TeachingLink 规范减去 1000 米偏置。
  - status_flags.bit2 表示 timestamp_fallback，不表示 time_valid。
  - callsign、位置、运动字段必须结合 validity_flags 判断，不能把占位 0 当作有效真实值。
- 人工修订依据：student_package/schema/teaching_message_spec.md、student_package/schema/unified_model.json、M3 current_situation.csv 与 TeachingLink 当前态势样例。
- 正常样例验证结果：000001 与 780abc 在 OpenSky 和 TeachingLink 两种来源下均能映射为统一模型，timestamp、位置、运动、高度来源和 message_valid 保持一致。
- 真实零值与缺失值样例验证结果：000001 的 0 附近位置和 0 值运动字段被保留为有效值；780def 的经纬度缺失被映射为 null，并在 quality.anomaly_flags 中记录 POSITION_MISSING。
- 不应由大模型自行决定的内容：字段方向、单位换算、比例因子、偏置、有效性位、状态位语义、message_valid 的含义以及缺失值处理规则。
