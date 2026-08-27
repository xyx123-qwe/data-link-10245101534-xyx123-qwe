# M1 系统处理流程与风险说明


## 处理流程图

OpenSky离线数据 raw_states.json
  -> 发送方解析：按OpenSky字段索引读取目标标识、时间、经纬度、高度、速度、航向等字段
  -> 发送方内部状态：统一字段名称，处理必需字段、可空字段、时间回退和高度来源
  -> TeachingLink消息封装：按41字节、大端字节序、定点量化、有效位、状态位和校验和生成二进制帧
  -> 模拟传输：逐帧传输固定长度消息
  -> 接收方解封与校验：检查长度、magic、version、message_type、checksum、保留位和有效位一致性
  -> 接收方内部记录：恢复目标编号、时间、位置、运动状态、有效性标志和 message_valid
  -> CSV / SQLite选做：保存解码后的结构化记录
  -> 航迹与当前态势：按 target_id 分组，按 timestamp 排序，每个目标保留最新记录
  -> 语义映射：转换为统一态势模型
  -> 一致性检查：检查字段缺失、延迟、重复、越界等问题
  -> 输出当前态势、统一态势和告警结果


## 接口、通信与风险说明

1. 原始接口提供什么数据？

OpenSky 原始接口提供航空器状态向量数据。每条状态向量是一个按固定索引排列的数组，包含 icao24、callsign、origin_country、time_position、last_contact、longitude、latitude、baro_altitude、on_ground、velocity、true_track、vertical_rate、geo_altitude、position_source 等字段。

2. 为什么原始数据不是完整态势结果？

raw_states.json 只是离线原始输入数据，字段仍按 OpenSky 状态向量索引排列。它还没有经过发送方解析、协议封装、接收方校验、航迹排序和当前态势提取，因此不能直接看作完整态势结果。当前态势需要按目标分组，并为每个目标保留时间最新的一条可接受记录。

3. 为什么发送方需要把内部状态封装成消息？

发送方内部状态是程序中的结构化记录，不能直接在线传输。通信双方必须使用共同约定的二进制格式，明确字节序、字段偏移、位宽、比例因子、偏置、有效位、状态位和校验和。TeachingLink 41字节消息就是本实验中发送方和接收方共同使用的教学消息格式。

4. 为什么接收方要检查长度、类型、校验和与保留位？

这些检查用于判断收到的帧是否符合 TeachingLink 协议。长度和 message_length 确认帧边界正确；magic、version、message_type 确认消息类型正确；checksum 用于发现传输或封装错误；保留位检查用于发现不符合协议约定的异常数据。非法帧应记录错误，不能导致程序整体崩溃。

5. CSV 与 SQLite 分别承担什么角色？

CSV 是必做输出格式，用于保存解码记录、航迹表、当前态势表、校验日志和误差报告，便于查看和提交。SQLite 是 M3 的选做持久化方式，可以把接收记录保存到数据库中，支持查询和 NULL 值保存，但不是完成必做任务的前置条件。

6. 至少列出三个工程风险，并说明影响与处理方式。

字段缺失：呼号、经纬度、高度、速度等字段可能为空。处理时应使用 validity_flags 标记字段是否有效，不能用 0 冒充缺失值。

接口延迟：time_position 可能缺失。处理时优先使用 time_position，必要时回退到 last_contact，并通过 status_flags 记录 timestamp_fallback。

消息损坏：长度、magic、version、message_type 或 checksum 可能错误。处理时接收方应记录错误日志，并将帧标记为不可接受，而不是让程序崩溃。

量化误差：经纬度、高度、速度、航向和垂直速度经过定点编码后会产生小误差。处理时应生成 roundtrip_report.csv，比较源值和解码值，确认误差在允许范围内。

保留位异常：经纬度三字节容器最高两位、status_flags 保留位或 validity_flags 保留位可能不为 0。处理时应记录 RESERVED_BITS_ERROR。


## 自查

- [x] 区分外部原始数据、传输帧和接收方内部记录
- [x] 覆盖发送、传输、接收、存储、航迹、映射和检查
- [x] 没有把 TeachingLink 描述为真实装备或行业标准协议
