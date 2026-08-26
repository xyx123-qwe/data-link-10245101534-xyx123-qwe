# M5 异常结果说明

- 批次时间：1710000120
- 四类必做规则是否均运行：是，已运行位置缺失、延迟、联合键重复、航向越界四类规则。
- 告警总数及按类型统计：总数 5；POSITION_MISSING=1，DATA_DELAYED=1，DUPLICATE_RECORD=2，HEADING_OUT_OF_RANGE=1。
- HIGH/MEDIUM 数量：HIGH=1，MEDIUM=4。
- 正常记录是否被误报：780abc 未产生告警，display_status 为 OK。
- heading=360 与 heading为空的处理：heading=360 不满足 0 <= heading < 360，产生 HEADING_OUT_OF_RANGE；heading 为空时不触发航向越界，但可由其他字段规则继续检查。
- 字段缺失、帧验证失败、来源真实性三者的区别：字段缺失是业务字段为空或不可用；帧验证失败是 TeachingLink 消息格式、校验和或保留位不通过；来源真实性表示数据是否来自真实接口或可信来源，不能由 message_valid 直接推出。
