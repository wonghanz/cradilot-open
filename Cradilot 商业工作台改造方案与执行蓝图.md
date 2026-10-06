# **AI SME Digital Growth Advisor (Cradilot Cockpit)**

## **商业级工作台改造方案与实施蓝图 (2026 伙伴挑战赛全指标合规版 v5.0)**

**Project Title**: AI SME Digital Growth Advisor

**Tagline**: "Helping SMEs Discover Their Next Digital Step"

**Target Benchmark**: the AI Horizon Solution Challenge 2026 & Cradle CIP Spark Institutional Due Diligence

## **1\.本公司官方任务书与系统架构 100% 逐项对照矩阵**

本系统严格对照本公司官方 Challenge PDF 规划，将 12 项交付指标与系统实现进行确定性映射，杜绝任何赛题遗漏：

\+-------------------------------------------------------------------------------------------------------------------------+  
|                                  本公司 2026 官方指标与系统架构实现对照表                                             |  
\+--------------------------+------------------------------------+---------------------------------------------------------+  
| 官方任务书要求项         | 官方具体规格与示例                 | Cradilot Cockpit 架构落地实现                           |  
\+--------------------------+------------------------------------+---------------------------------------------------------+  
| Real Business Problem    | 覆盖 95% SME，解答 6 大核心困惑    | 首页 TOP HUD 与诊断报告第一页直接锚定 6 大问题解答      |  
| (商业痛点与目标)         | (何处开始/最大影响/AI准备度/工具   | (防止买错工具、乱排工期与资金浪费)                      |  
|                          | 顺序/费用预算/预期 ROI)            |                                                         |  
\+--------------------------+------------------------------------+---------------------------------------------------------+  
| Challenge 5-Min Limit    | 5 分钟内分析 SME 并输出专属蓝图    | 4 步 CoT 快速推理，总交互控制在 8-10 轮内 (300 秒闭环)  |  
\+--------------------------+------------------------------------+---------------------------------------------------------+  
| Step 1: Business         | 询问约 5 个核心问题: 行业、规模、  | SOP 骨架强制约束 6 大发现槽位，AI 大脑 100% 动态生成提问|  
| Discovery (+ Dynamic Qs) | 员工数、现有工具、最大痛点、目标   | 遇 10% 盲点自动弹出动态补充探针容器 (Dynamic Container) |  
\+--------------------------+------------------------------------+---------------------------------------------------------+  
| Step 2: Digital          | 6 维度打分 (0-100 / 星级):         | 纯数学纯函数打分引擎:                                   |  
| Maturity Score (DMS)     | Website / Cloud / CRM / Marketing  | 基于 SQLite 事实证据节点确定性加权计算，杜绝 AI 幻觉打分|  
|                          | / Cybersecurity / AI Adoption      | (若 DMS \< 40 触发 Cradle 创投硬锁门禁 Hard-Lock)        |  
\+--------------------------+------------------------------------+---------------------------------------------------------+  
| Step 3: AI Readiness     | 5 大评估要素: 领导力、数据可用性、 | ARS 5 维度加权评估方程:                                 |  
| Score (ARS)              | 员工技能、数字工作流、流程成熟度   | 受 DMS 硬锁因子 mu 调节，防止不成熟企业盲目采购高阶 AI  |  
\+--------------------------+------------------------------------+---------------------------------------------------------+  
| Step 4: Evidence-Based   | 证据链支撑的 Top 5 根因痛点清单    | 事实抽离引擎自动提炼 Top 5 失血痛点矩阵，               |  
| Pain Point Analysis      | (如: 手工作业繁多/无CRM/漏单等)    | 每一条严格绑定用户原话引用 (Quote) 与失血金额           |  
\+--------------------------+------------------------------------+---------------------------------------------------------+  
| Step 5: Action Roadmap   | Phase 1: Quick Wins (2-4 周)       | 拓扑依赖编排算法:                                       |  
| & Recommendation Engine  | Phase 2: Productivity (3-6 个月)   | 依据痛点严重程度动态编排，并输出 Explaining WHY 选型理由|  
| (Explaining WHY)         | Phase 3: Growth (6-12 个月)        | (如: 为什么选本公司Email 而非 M365)                 |  
\+--------------------------+------------------------------------+---------------------------------------------------------+  
| Bonus 1: Potential ROI   | 算清省多少小时/年化挽回多少马币    | 建立马来西亚法定工时基准 (RM 22/hr) 精算模型，          |  
| Estimation               | (例: 12hr/周 \-\> 减8hr \-\> RM18,000) | 实时跳动累计失血卡 (累计失血额与挽回 ROI)               |  
\+--------------------------+------------------------------------+---------------------------------------------------------+  
| Bonus 2: Implementation  | 编排实施时间线: Month 1-3,         | 动态甘特时间线引擎，阶段末尾自动绑定                    |  
| Timeline                 | Month 3-6, Month 6-12              | Cradle CIP Spark 拨款核销的 Form A2 验收节点            |  
\+--------------------------+------------------------------------+---------------------------------------------------------+  
| Bonus 3: PDF Proposal    |本公司品牌标识、商业摘要、成熟度| Typst Rust 极速矢量编译引擎 (150ms 本地离线生成)，      |  
| Generation               | 路线图、ROI、推荐方案、顾问评注    | 导出包含官方标识、雷达图与顾问签名的 6 页投资级商业蓝图 |  
\+--------------------------+------------------------------------+---------------------------------------------------------+  
| Even Better: Sales Tool  | 客户点击“免费咨询” \-\> 自动建单 \-\>  | 销售线索一键派发模块: 自动打包线索 Payload、            |  
| (Lead Generation CRM)    | 派单销售 \-\> 附带报告与痛点预算     | 生成本公司官方预置购物车与销售电话破冰话术          |  
\+--------------------------+------------------------------------+---------------------------------------------------------+

## **2\. 核心架构哲学：SOP 骨架驱动 \+ AI 大脑动态生成 (前端零硬编码)**

针对“静态假问卷、假评分”的硬编码弊端，系统确立铁律：**前端代码无任何固定题库文本，所有交互探针、选项胶囊与追加容器均由 AI 大脑根据 SOP 状态机动态计算生成**。

\+---------------------------------------------------------------------------------------------------------+  
|                                    SOP 骨架与 AI 动态大脑双擎驱动架构                                    |  
\+------------------------------------+------------------------------------+-------------------------------+  
| 核心模块                           | SOP 确定性合规骨架 (Deterministic)  | AI 动态生成大脑 (Dynamic Brain)|  
\+------------------------------------+------------------------------------+-------------------------------+  
| 问题生成机制                       | 强制约束 6 大发现槽位与完成度门禁  | 100% 动态生成提问与选项胶囊，  |  
|                                    | (Completeness Gate \>= 90%)         | 依据行业上下文定制提问口吻    |  
| 容器动态挂载                       | 规范容器 Schema 与状态机           | 检测到 10% 盲点时，动态下发并 |  
| (Dynamic Container)                | (Probe / Audit / Mitigation / Box) | 挂载独立排查容器卡片          |  
| 语音输入抗噪过滤                   | 规范业务事实本体与字段提取规范     | 过滤抱怨与闲聊，秒级提炼核心  |  
| (Live-to-Speech Distiller)         | (Tool, Frequency, Financial Loss)  | 数字、工具与失血事实          |  
| Step 2 深度安全审计                | 开发者级扫描规范 (Keys, Env, DMARC)| 自动化分析客户端源码并输出    |  
| (Dev-Level Audit)                  | 严格界定在合法合规被动检测范围     | 具备创投合规效力的安全评级    |  
| 选型理由生成 (WHY)                 | 约束本公司官方合格 SKU 候选池  | 动态对比不同产品，深度剖析    |  
|                                    | (Email, Cloud, VPS, CRM, AI)       | 推荐该产品之商业与技术根因    |  
| 实施时间线                         | 依赖拓扑算法 (前置依赖硬约束)      | 依据痛点严重程度动态编排      |  
| (Dynamic Timeline)                 | Form A2 首期必设验收红线           | Month 1-3/3-6/6-12 交付任务   |  
\+------------------------------------+------------------------------------+-------------------------------+

## **3\. 前端交互核心演进：Apple Live Orb 与三栏作战空间**

工作台彻底剔除向导表单，核心视觉采用 **Apple Spatial 风格的悬浮三栏工作台**，中央聚焦于一颗代表 AI 大脑活跃度的 **Apple Live 动态光球（Apple Dynamic Orb）**。

\+-------------------------------------------------------------------------------------------------------------------------+  
| \[TOP HUD\]  项目: AI SME Digital Growth Advisor | 标语: Helping SMEs Discover Their Next Digital Step                    |  
| 企业名称: 巴生汽配五金 | 行业: 汽车制造批发 | 员工数: 12人 | 营业额: RM 3.2M | 采集完成度: 88% \[SOP 阶段 2/5 推进中\]      |  
\+------------------------------------+------------------------------------+-----------------------------------------------+  
| 左栏: 创投交锋与语音动态交互 (35%) | 中栏: Apple Orb & 动态容器 (40%)    | 右栏: 资产沉淀与交付蓝图 (25%)                |  
|                                    |                                    |                                               |  
| • 实时对话历史流                   | • \[中央核心\] Apple Live 动态光球   | • 6 维度 DMS 雷达图 (当前: 34.2 / 100\)        |  
|   (Gemma Cradle 导师犀利把关)      |   (流体渐变微光, 随音频与思考跳动) | • 5 维度 ARS 评分 (锁定 \<= 10.0)              |  
|                                    |                                    | • 动态年化失血卡 (累计: RM 33,590/年)         |  
| • 动态探针容器 (Dynamic Container) | • \[当前聚焦\] 动态问题挂载容器 Box  | • Cradle Hard-Lock 警示横幅                   |  
|   \- 由 AI 大脑实时下发             |   \- AI 动态生成的提问              |   (DMS \< 40 强制阻断高阶 AI 采购)             |  
|   \- 启发式选项胶囊 (Capsules)      |   \- 快捷选项胶囊 (Clickable)       | • 证据支撑的 Top 5 痛点实时清单               |  
|                                    |                                    | • 动态生成的实施路线图 (Timeline)             |  
| • 交互底栏 (Multimodal Input):     | • \[补充排查\] 动态追加容器 (10%盲点)|   \- Phase 1 (M1-3): 漏洞筑基与容灾            |  
|   \- \[Live-to-Speech\] 语音按键      |   \- 针对 HTTPS/备份/密钥进行追问   |   \- Phase 2 (M3-6): 业务流程自动化            |  
|   \- 自然语言输入框 (支持 Enter)    |                                    |   \- Phase 3 (M6-12): 本地智能落地             |  
|   \- 实时语音波形反馈               | • \[底层背景\] 实时力导向知识网络    | • 核心动作:                                   |  
|                                    |   (Cytoscape.js 动态生长拓扑图)    |   \[150ms 编译 Typst 6页投资蓝图\]              |  
|                                    |                                    |   \[申请免费咨询 (一键派发销售 CRM)\]           |  
\+------------------------------------+------------------------------------+-----------------------------------------------+

### **Apple Live Orb 状态机设计**

中心光球由 CSS3 径向渐变与 WebGL 着色器共同驱动，状态随系统运转毫秒级响应：

* **IDLE (待命)**: 柔和的深蓝与银灰冷光流体缓慢流动；  
* **LISTENING (正在聆听用户语音)**: 外圈扩散青蓝色音波光环，随声音振幅动态缩放；  
* **ANALYZING (抓重点提炼中)**: 内核高速自旋，光芒凝聚为琥珀金，折叠呈现 4 步 CoT 思考；  
* **PROBING (生成动态问题容器)**: 光芒扩散至下方的动态容器，将生成的结构化问题卡片平滑推入视野；  
* **HARD-LOCKED (触发创投资本熔断)**: 爆发红色警示微光，提示底层数字化成熟度不足 40 分。

## **4\. 动态问题容器与自适应补全机制 (Dynamic Container Injection)**

系统坚决杜绝在前端预置固定问卷。AI 大脑内部维护一个 **SOP 维度覆盖率矩阵（Completeness Matrix）**：

![][image1]flowchart TD  
&nbsp;&nbsp;&nbsp;&nbsp;A\["SOP 阶段目标设定 (如: Step 1 发现 / Step 2 审计)"\] \--\> B\["AI 评估当前已知事实与置信度"\]  
&nbsp;&nbsp;&nbsp;&nbsp;B \--\> C{"当前置信度评估"}  
&nbsp;&nbsp;&nbsp;&nbsp;C \-- "置信度 \>= 90%" \--\> D\["推进至下一 SOP 阶段\<br/\>渲染阶段达标里程碑"\]  
&nbsp;&nbsp;&nbsp;&nbsp;C \-- "置信度 \< 90% (存在 10% 关键盲区)" \--\> E\["AI 动态构建【补充探针容器 (Deep Probe Container)】"\]  
&nbsp;&nbsp;&nbsp;&nbsp;E \--\> F\["容器挂载: 注入精准提问 \+ 启发胶囊 \+ 辅助验证机制"\]  
&nbsp;&nbsp;&nbsp;&nbsp;F \--\> G\["用户通过语音或文本提交补充事实"\]  
&nbsp;&nbsp;&nbsp;&nbsp;G \--\> H\["事实抽离引擎回写 SQLite Wiki，闭环置信度"\]  
&nbsp;&nbsp;&nbsp;&nbsp;H \--\> B

### **动态容器协议定义 (Backend-to-Frontend JSON)**

前端收到此协议后，动态渲染 DOM 结构，无任何本地预存问题：

{  
&nbsp;&nbsp;"container\_id": "box\_probe\_cybersec\_02",  
&nbsp;&nbsp;"sop\_stage": "Step 2: Technical & Cybersecurity Audit",  
&nbsp;&nbsp;"confidence\_score": 0.88,  
&nbsp;&nbsp;"missing\_blindspots": \["cloud\_backup\_frequency", "api\_key\_governance"\],  
&nbsp;&nbsp;"dynamic\_question": {  
&nbsp;&nbsp;&nbsp;&nbsp;"title": "异地数据冷备与开发者凭据管控排查",  
&nbsp;&nbsp;&nbsp;&nbsp;"prompt": "官网技术扫描显示您的前端源码引用了第三方支付与地图组件，请问您的财务与客户数据库是否有每日异地自动快照？",  
&nbsp;&nbsp;&nbsp;&nbsp;"rationale": "检测到 10% 的安全合规盲区，需补全以规避 2024 PDPA 数据主权违规处罚",  
&nbsp;&nbsp;&nbsp;&nbsp;"quick\_capsules": \[  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{"label": "单机电脑手动拷贝", "impact": "高失血风险 (勒索病毒)", "loss\_est": 15000},  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{"label": "已有本公司/云端自动冷备", "impact": "合规达标", "loss\_est": 0},  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{"label": "完全没有备份习惯", "impact": "致命缺陷 (单点崩溃)", "loss\_est": 35000}  
&nbsp;&nbsp;&nbsp;&nbsp;\]  
&nbsp;&nbsp;},  
&nbsp;&nbsp;"visual\_state": "EXPAND\_CONTAINER"  
}

## **5\. Live-to-Speech 语音抗噪与“抓重点”事实抽离引擎**

SME 企业主在面对麦克风时，往往伴随着大量口语化抱怨、情绪宣泄和无序表述。系统构建专用的**抗噪事实蒸馏管线（Noise Filter Pipeline）**，专门“抓重点”，剔除抱怨，提炼符合 SOP 要求的硬核事实：

flowchart LR  
&nbsp;&nbsp;&nbsp;&nbsp;A\["用户连续语音输入 (Live Audio)"\] \--\> B\["Web Speech API / Whisper 本地转录"\]  
&nbsp;&nbsp;&nbsp;&nbsp;B \--\> C\["原始文本 (包含大量抱怨、杂音与情绪词)"\]  
&nbsp;&nbsp;&nbsp;&nbsp;C \--\> D\["Gemma 事实抽离过滤器 (Prompt Filter)"\]  
&nbsp;&nbsp;&nbsp;&nbsp;D \--\> E{"事实判定与校验"}  
&nbsp;&nbsp;&nbsp;&nbsp;E \-- "情绪宣泄 / 冗余闲聊" \--\> F\["丢弃 (Drop Noise)"\]  
&nbsp;&nbsp;&nbsp;&nbsp;E \-- "核心业务事实" \--\> G\["标准化本体结构化入库"\]  
&nbsp;&nbsp;&nbsp;&nbsp;G \--\> H\["wiki\_evidence\_nodes (SQLite)"\]

### **事实抽离提示词约束工程 (Fact Extraction Prompt Guard)**

\[SYSTEM OBJECTIVE\]  
你是一个冷酷、严谨的 Cradle 创投资本尽调专家。你的任务是从用户的口语或语音转录文本中，  
剔除所有情绪词、抱怨、背景故事与废话，精确“抓重点”，提取出符合 SOP 规范的确定性事实：  
1\. 涉及工具 (Tools): 如 WhatsApp, Excel, 某某单机财务软件;  
2\. 频次与工时 (Time): 如 每天花费3小时, 每周对账10小时;  
3\. 财务与商业漏洞 (Bleeding): 如 错单率5%, 夜间询盘无响应, 无法追踪销售漏斗;  
4\. 合规缺陷 (Legal Gap): 如 使用个人邮箱传输客户隐私, 客户数据无授权存储.

\[OUTPUT SCHEMA\]  
严格输出以下 JSON，严禁输出任何多余分析说明：  
{  
&nbsp;&nbsp;"filtered\_facts": \[  
&nbsp;&nbsp;&nbsp;&nbsp;{"dimension": "CRM", "fact\_key": "customer\_intake\_channel", "fact\_value": "Personal WhatsApp", "quote": "WhatsApp几十个消息"},  
&nbsp;&nbsp;&nbsp;&nbsp;{"dimension": "Cloud", "fact\_key": "data\_redundancy", "fact\_value": "None (Manual Sheet)", "quote": "对账对到半夜"}  
&nbsp;&nbsp;\],  
&nbsp;&nbsp;"quantified\_loss": {  
&nbsp;&nbsp;&nbsp;&nbsp;"hours\_wasted\_weekly": 14.0,  
&nbsp;&nbsp;&nbsp;&nbsp;"estimated\_annual\_loss\_myr": 16016.0  
&nbsp;&nbsp;}  
}

## **6\. Step 2 开发者级安全与合规深度扫描 SOP (Dev-Level Audit)**

系统不搞表面虚假测试，而是在合法合规的边界内，执行**开发者级的前端配置与资产安全排查**：

\+---------------------------------------------------------------------------------------------------------+  
|                              STEP 2 开发者级安全与配置审计 SOP 规范                                      |  
\+--------------------------+------------------------------------------+-----------------------------------+  
| 审计项 (Audit Item)      | 检测技术原理 (Methodology)               | 发现问题对应之商业与合规风险      |  
\+--------------------------+------------------------------------------+-----------------------------------+  
| 前端敏感凭据泄漏扫描     | 正则匹配公开 JS Bundle 中的硬编码凭据    | 导致云资源被盗用刷量、            |  
| (API Key Exposure)       | (如: AWS AKIA\*, Google API Key, 支付私钥)| 数据库凭据泄漏 (PDPA 顶格处罚)    |  
\+--------------------------+------------------------------------------+-----------------------------------+  
| 敏感配置文件与目录暴露   | 检测 \`/.env\`, \`/.git/HEAD\`,              | 攻击者可轻易下载整站源码及账本，  |  
| (Exposed Sensitive Files)| \`/wp-config.php.bak\` 是否直接返回 200 OK | 触犯 MACC 17A 管理层失职红线      |  
\+--------------------------+------------------------------------------+-----------------------------------+  
| 企业邮箱防仿冒三重解析   | 校验域名 DNS 之 SPF, DKIM 与 DMARC 记录  | 邮件无认证极易被假冒发送欺诈账单，|  
| (Email Spoofing Defense) | 缺失情况                                 | 极易被客户反垃圾系统直接拦截      |  
\+--------------------------+------------------------------------------+-----------------------------------+  
| 传输层与安全响应头       | 探测 TLS 1.2/1.3 加密套件及 HSTS,        | 容易遭受中间人劫持与点击劫持，    |  
| (Transport Security)     | Content-Security-Policy 头部缺失度       | 官网信誉度被浏览器标记为不安全    |  
\+--------------------------+------------------------------------------+-----------------------------------+

## **7\. DMS (6维) & ARS (5维) 纯数学评分与 Cradle Hard-Lock 门禁**

Scoring 彻底杜绝 LLM 幻觉生成，由纯数学函数计算：

### **1\. Digital Maturity Score (DMS) \- 官方 6 维度权重**

* ![][image2]**Website (15%)**: 域名所有权、SSL 评级、移动端适配；  
* **Cloud (20%)**: 数据集中化、自动异地快照冷备、灾备可用性；  
* **CRM (20%)**: 集中销售漏斗、跟进日志、权限隔离；  
* **Marketing (15%)**: 获客渠道数字化、广告转化归因追踪；  
* **Cybersecurity (15%)**: 凭据管理、终端防护、PDPA 2024 合规基线；  
* **AI Adoption (15%)**: 自动化流程集成度、智能化客户交互。

### **2\. AI Readiness Score (ARS) \- 官方 5 大评估要素**

### **![][image3]3\. Cradle Hard-Lock 资本熔断门禁**

为杜绝向底层 IT 裸奔的 SME 滥销高阶 AI 工具，系统设置硬锁保护：

&nbsp;

![][image4]![][image5]当 ![][image6] 时，![][image7] 强制硬截断为 ![][image8] 分，右侧工作台弹出红色 Hard-Lock 警告，锁定 Phase 3 的高阶 AI 采购推荐，强制企业先修补基础设施。

## **8\. 证据链支撑的 Top 5 痛点矩阵与量化 ROI 精算模型 (Bonus 1\)**

系统坚决杜绝泛化的 AI 建议，提炼出的 **Top 5 根因痛点** 每一条均与事实证据链强绑定：

\+-------------------------------------------------------------------------------------------------------------------------+  
|                                  TOP 5 根因商业痛点与失血量化清单 (示例)                                                |  
\+---+----------------------------+------------------------------------+-----------------------+---------------------------+  
| \# | 根因痛点 (Pain Point)      | 用户原话证据 (Evidence Quote)      | 对应合规/商业漏洞     | 预估年化失血额 (MYR)      |  
\+---+----------------------------+------------------------------------+-----------------------+---------------------------+  
| 1 | 缺乏集中式 CRM 销售漏斗    | "销售用私人 WhatsApp 聊单，经常跳单| 客户资产流失、无法复盘| RM 18,000 / 年            |  
|   | (Customer Enquiries Manual)| 上周还丢了个印尼大单"              | 转化漏斗              | (夜间询盘无响应流失)      |  
\+---+----------------------------+------------------------------------+-----------------------+---------------------------+  
| 2 | 手工作业繁多且对账低效     | "工人手写单据，每天花3小时对账，   | 人力冗余、错单率 5%、 | RM 16,016 / 年            |  
|   | (Too Much Manual Work)     | 对到半夜经常出错"                  | 账目延迟              | (14小时/周 x RM22 x 52周) |  
\+---+----------------------------+------------------------------------+-----------------------+---------------------------+  
| 3 | 本地单机财务账本裸奔       | "会计软件装在一台旧电脑，平时用    | 勒索病毒单点崩溃、    | RM 35,000 / 潜在损失      |  
|   | (No Cloud Backup)          | U盘偶尔拷一下"                     | 违反 PDPA 数据可用性  | (数据灾难性损毁风险)      |  
\+---+----------------------------+------------------------------------+-----------------------+---------------------------+  
| 4 | 使用免费个人邮箱开展外贸   | "给客户发报价单都用                | 极易遭受邮件仿冒欺诈、| RM 12,000 / 年            |  
|   | (No Business Email)        | ahseng\_autoparts@gmail.com"        | 触犯 MACC 17A 审计红线| (海外弃单与拦截损失)      |  
\+---+----------------------------+------------------------------------+-----------------------+---------------------------+  
| 5 | 内部知识孤岛与培训断层     | "新员工要带三个月才上手，老师傅    | 人员离职经验清零、    | RM 9,600 / 年             |  
|   | (No Knowledge Management)  | 问一句答一句，资料乱七八糟"        | 培训成本高昂          | (重复沟通与试错工时)      |  
\+---+----------------------------+------------------------------------+-----------------------+---------------------------+

### **马来西亚法定工时与 ROI 精算方程 (Bonus 1\)**

根据官方基准：行政/操作员工平均月薪 RM 3,000，加上 EPF/SOCSO 后企业综合人力成本约 RM 3,500/月（折合 RM 22.00/小时）：

&nbsp;

![][image9]![][image10]![][image11]![][image12]*典型测算*：年化总投入 RM 5,550.68，挽回商业失血 RM 33,590.00，净收益 RM 28,039.32，**投资回报率达到 505%**。

## **9\.本公司即兴推荐引擎 (Explain WHY) 与动态实施时间线 (Bonus 2\)**

AI 大脑根据痛点即兴构建选型方案，并强制输出 **选型设计理由（Explaining WHY）**：

\+-------------------------------------------------------------------------------------------------------------------------+  
|                                    本公司 即兴方案构建与选型理由 (WHY) 规范                                          |  
\+--------------------------+--------------------------------+-------------------------------------------------------------+  
| 企业面临的痛点           | 推荐本公司官方 SKU 方案    | AI 大脑阐述选型理由 (Explaining WHY)                        |  
\+--------------------------+--------------------------------+-------------------------------------------------------------+  
| 无企业邮箱，使用个人     | Business Email /      | "选本公司Email 而非自建邮局：1. 本地 IP 信誉高，直通外商|  
| Gmail 发送商业报价       | Google Workspace Starter       | 收件箱；2. 内置 SPF/DKIM/DMARC 预配置，直接阻断发票欺诈；   |  
|                          |                                | 3\. 完美满足 MACC 17A 商业往来不可篡改审计要求。"            |  
\+--------------------------+--------------------------------+-------------------------------------------------------------+  
| 官网老旧或无独立官网，   | Managed WordPress /   | "针对汽配制造业，放弃昂贵的定制开发，选择托管 WordPress：  |  
| 依靠社媒单页接单         | AI Website Builder             | 1\. 7天内极速上线包含 SEO 优化的产品目录；2. 预置 NVMe 极速  |  
|                          |                                | 缓存与自动补丁；3. 解决海外采购商在 Google 的背书核验。"     |  
\+--------------------------+--------------------------------+-------------------------------------------------------------+  
| 财务账本存单机，无灾备   | Acronis Cloud Backup  | "选 Acronis 异地冷备而非移动硬盘：1. 勒索病毒防御与版本回溯;|  
|                          | (500GB 异地加密存储)           | 2\. 每日凌晨自动静默增量同步，免除人为遗忘；3. 满足 2024     |  
|                          |                                | PDPA 数据主权合规，30分钟内即可在异机拉起完整账本。"        |  
\+--------------------------+--------------------------------+-------------------------------------------------------------+

### **动态编排实施时间线 (Bonus 2: Month 1-3, 3-6, 6-12)**

graph TD  
&nbsp;&nbsp;&nbsp;&nbsp;subgraph P1\["Phase 1: 止血与筑基 (Month 1 \- 3\) \[Quick Wins | ROI: 2-4 周\]"\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;T1\["高危漏洞修补: 关闭 .env 暴露与配置 DMARC"\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;T2\["异地冷备筑基: 部署本公司Acronis 容灾 (500GB)"\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;T3\["官方品牌邮箱: 开通企业域名邮箱，停止个人 Gmail 报价"\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;T4\["Cradle Form A2 节点: 30分钟容灾恢复演练报告 \+ DMARC Pass"\]  
&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;&nbsp;&nbsp;&nbsp;subgraph P2\["Phase 2: 提效与流程贯通 (Month 3 \- 6\) \[Productivity | ROI: 3-6 个月\]"\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;T5\["集中式商机治理: 部署 Freshsales CRM 管道"\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;T6\["自动化工单路由: Linux VPS 部署 n8n 自动分流询盘"\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;T7\["协作知识底座: Google Workspace 集中化权限云盘"\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;T8\["Cradle Form A2 节点: 首批 50 笔商机流转审计日志"\]  
&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;&nbsp;&nbsp;&nbsp;subgraph P3\["Phase 3: 规模化与智能协同 (Month 6 \- 12\) \[Growth | ROI: 6-12 个月\]"\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;T9\["全天候智能获客: 24/7 WhatsApp AI 销售路由"\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;T10\["本地知识库增强: Local RAG 内部技术问答库"\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;T11\["营销自动化引擎: 废弃询盘唤醒与多渠道漏斗追踪"\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;T12\["Cradle Form A2 节点: \<60秒响应率与零外泄合规报告"\]  
&nbsp;&nbsp;&nbsp;&nbsp;end

&nbsp;&nbsp;&nbsp;&nbsp;T1 \--\> T2 \--\> T3 \--\> T4  
&nbsp;&nbsp;&nbsp;&nbsp;T4 \-. "验证通过方可解锁" .-\> T5  
&nbsp;&nbsp;&nbsp;&nbsp;T5 \--\> T6 \--\> T7 \--\> T8  
&nbsp;&nbsp;&nbsp;&nbsp;T8 \-. "DMS \>= 40 方可解锁" .-\> T9  
&nbsp;&nbsp;&nbsp;&nbsp;T9 \--\> T10 \--\> T11 \--\> T12

## **10\. 150ms 极速编译投资级 Typst 商业蓝图 (Bonus 3\)**

用户完成工作台交互后，点击导出蓝图，后台调用 Rust 编写的 Typst 编译器，在 **150 毫秒内** 生成包含本公司官方 Visual Identity 的 6 页矢量 PDF：

\+---------------------------------------------------------------------------------------------------------+  
|                                TYPST 6 页投资级蓝图结构规范 (Bonus 3\)                                    |  
\+--------+------------------------------------+-----------------------------------------------------------+  
| 页码   | 页面核心主题                       | 页面关键元素与内容呈现                                    |  
\+--------+------------------------------------+-----------------------------------------------------------+  
| Page 1 | 执行总览与成熟度雷达               |本公司官方标识、项目标题、DMS 6 维雷达图、ARS 评分、  |  
|        | (Executive Diagnostic Summary)     | 商业基础信息 (营业额/团队/行业)、Cradle Hard-Lock 状态    |  
\+--------+------------------------------------+-----------------------------------------------------------+  
| Page 2 | 证据链支撑的 Top 5 痛点与选型 WHY  | Top 5 痛点矩阵 (原话引用/严重度)、推荐产品与选型理由(WHY) |  
|        | (Pain Points & Architecture WHY)   | 对比说明为什么选本公司方案而非竞品                    |  
\+--------+------------------------------------+-----------------------------------------------------------+  
| Page 3 | 动态实施甘特时间线                 | Month 1-3、3-6、6-12 阶段甘特图、前后置任务拓扑连线、     |  
|        | (12-Month Action Roadmap)          | 各阶段里程碑交付物与关键负责人职责分配                    |  
\+--------+------------------------------------+-----------------------------------------------------------+  
| Page 4 | Cradle CIP Spark 资金核销表        | 对应 Cradle Form A2 拨款节点的验收材料清单、              |  
|        | (Form A2 Disbursement Schedule)    | 独立第三方审计核验方式 (如 Acronis 演练报告、DMARC 证明)  |  
\+--------+------------------------------------+-----------------------------------------------------------+  
| Page 5 | 系统工程验收与容灾测试规范         | Test Sequence 01/02/03 (备份还原、并发工单、AI提示词防漏) |  
|        | (Acceptance Testing Protocols)     | 验收未通过的应急处置与修复预案 (Remediation Protocols)    |  
\+--------+------------------------------------+-----------------------------------------------------------+  
| Page 6 | 量化 ROI 财务报表与顾问签名        | 505% 投资回报率精算表、MACC 17A 法律保护声明、            |  
|        | (ROI Statement & Consultant Notes) |本公司资深解决方案架构师顾问评注与电子手签             |  
\+--------+------------------------------------+-----------------------------------------------------------+

## **11\. 商业闭环：销售赋能与线索一键派发流水线 (Even Better: Sales Tool)**

系统直接赋能本公司真实销售转化，打通 **“诊断 ![][image13] 蓝图 ![][image13] 建单 ![][image13] 派单”** 闭环：

flowchart TD  
&nbsp;&nbsp;&nbsp;&nbsp;A\["客户在右栏点击: 【申请本公司专家落地咨询 (免费)】"\] \--\> B\["前端弹窗快速确认: 联系人姓名、WhatsApp 号码、优先回访时间"\]  
&nbsp;&nbsp;&nbsp;&nbsp;B \--\> C\["API 触发: POST /api/sales/dispatch-lead"\]  
&nbsp;&nbsp;&nbsp;&nbsp;C \--\> D\["组装销售线索包 (Structured Lead Packet)"\]  
&nbsp;&nbsp;&nbsp;&nbsp;D \--\> E\["自动生成本公司预置购物车 (Pre-configured Cart URL)"\]  
&nbsp;&nbsp;&nbsp;&nbsp;D \--\> F\["生成电销专属【痛点破冰话术脚本 (Icebreaker Script)】"\]  
&nbsp;&nbsp;&nbsp;&nbsp;D \--\> G\["自动将 6 页 Typst 蓝图 PDF 作为附件绑定"\]  
&nbsp;&nbsp;&nbsp;&nbsp;G \--\> H\["推送至本公司Sales CRM (分配专属客户经理)"\]  
&nbsp;&nbsp;&nbsp;&nbsp;H \--\> I\["客户经理致电前已掌握: 业务规模、预算上限、Top 5 痛点与选型 WHY"\]

### **销售破冰话术脚本示例 (Auto-generated Icebreaker)**

\[销售顾问背景速览\]  
• 客户企业: 巴生汽配五金 (12人规模, 年营收 RM 3.2M)  
• 核心痛点: 会计单机无备份、员工用个人 WhatsApp 经常跳单、丢过印尼大单  
• 数字化成熟度: 34.2 (处于 Cradle 基础设施高危预警状态)  
• 推荐首期方案: Business Email (5用户) \+ Acronis Cloud Backup (500GB)  
• 预置购物车总额: RM 1,899 / 年 (首期轻量启动)

\[破冰致电话术\]  
"林总您好，我是 本公司的数字化方案顾问 Alex。刚才看到您在我们的 AI 智能工作台上完成了巴生汽配的数字化诊断。报告里提到上周咱们因为私人 WhatsApp 接单遗漏了一个印尼客户的询盘，而且财务电脑目前还没有异地灾备，这确实太危险了。我们为您准备了一份针对性的防跳单与自动容灾落地方案，首期预算仅需一千多马币，今天下午两点方便跟您做个 10 分钟的线上演示吗？"

## **12\. 详尽端到端用户全生命周期旅程 (00:00 \- 05:00 User Flow)**

00:00 \- 00:30  \[阶段 0: 企业档案冷启动与开发者级扫描\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• 用户在工作台输入企业名称（巴生汽配五金）与官网地址。  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• 后台快速启动开发者级安全审计：扫描 DNS/SPF、检测敏感文件暴露及公开 JS 敏感凭据。  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• 中心 Apple Orb 泛起淡蓝微光，中栏生成初始核心节点。

00:30 \- 02:00  \[阶段 1: 语音/文本交锋 & 动态问题容器挂载\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• AI 大脑生成第一个动态问题容器（围绕核心获客与客户沉淀）。  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• 用户按住麦克风发言：“我们平时都用自己的 WhatsApp 接单，工人手写单据，经常对不上账，上周还丢了印尼客户的大单。”  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• 语音转录后送入“抗噪蒸馏引擎”，自动滤除口语废话，提取“无集中CRM”、“手工单据错漏”、“海外询盘流失”等核心事实。  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• Apple Orb 泛出金光，中栏图谱实时生长出红色失血节点，右侧年化失血额跳动增加 RM 18,000。

02:00 \- 03:00  \[阶段 2: 10% 盲点识别与二级容器自适应弹出\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• AI 评估当前置信度仅为 88%（缺少异地容灾与凭据治理细节）。  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• AI 大脑在中心 Orb 下方动态挂载【补充探针容器 Box】：“检测到您的官网引用了未防护的外部接口，请问本地财务账本是否有自动云端备份？”  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• 用户点击快捷胶囊：“单机电脑手动备份”。  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• 触发 Cradle Hard-Lock 门禁（DMS \= 34.2 \< 40），右栏弹出红色警示横幅，锁定高阶 AI 采购，防止资本浪费。

03:00 \- 04:00  \[阶段 3:本公司即兴方案构建与动态时间线编排\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• Cradle 导师切换为本公司架构师角色，针对痛点即兴构建方案（Acronis 异地备份 \+ Linux VPS 自动化网关）。  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• 详细阐述选型 WHY、挽回商业损失精算（505% ROI）。  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• 依据 SOP 依赖算法，动态编排生成 Month 1-3、3-6、6-12 的实施路线图与 Cradle Form A2 验收节点。

04:00 \- 04:30  \[阶段 4: 150ms 极速编译投资级 Typst 商业蓝图\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• 用户点击 \[编译 6 页 Typst 商业实施蓝图\]。  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• 调用 Rust Typst 编译器，150 毫秒内生成包含本公司官方标识、DMS 雷达图、即兴方案理由、动态甘特图及顾问签名的 6 页矢量 PDF。

04:30 \- 05:00  \[阶段 5: 销售转化赋能与线索一键派发\]  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• 点击 \[申请本公司专家落地咨询\]。  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• 系统自动生成销售线索包、预置购物车（Pre-configured Cart）及针对该客户痛点的电销破冰话术，完成商业闭环。

## **13\. 实施代码落地改造检查清单 (Engineering Checklist)**

### **模块 1: 前端 Apple Orb 与动态容器渲染 (static/index.html, static/js/workbench.js)**

* \[ \] 移除旧有的全部硬编码问答表单 DOM。  
* \[ \] 构建中心 Apple Live Orb（CSS 径向渐变流体 \+ WebGL 音频振幅联动）。  
* \[ \] 编写动态容器挂载函数 renderDynamicContainer(containerData)，支持由后台 JSON 驱动的卡片挂载与平滑过渡动画。  
* \[ \] 集成浏览器 Web Speech API / 录音组件，支持长按录音、实时转录与波形反馈。

### **模块 2: 后端抗噪抽离与动态探针引擎 (core/agentic\_diagnostic.py, core/noise\_filter.py)**

* \[ \] 编写 NoiseFilterEngine：利用微调模型从口语转录中提取标准化的 Facts 字典，丢弃无关闲聊与抱怨。  
* \[ \] 编写动态提问决策机：根据 SqlWikiEngine 中的置信度得分，动态生成下一轮提问与快捷选项胶囊（零硬编码题库）。  
* \[ \] 接入开发者级被动安全探测：异步扫描企业域名的 SPF/DMARC 记录与常见的敏感文件状态码（/.env, /.git）。

### **模块 3: SOP 动态实施时间线编排器 (core/dynamic\_timeline.py)**

* \[ \] 编写拓扑依赖编排算法：将高危漏洞与单机备份缺陷强制排入 Phase 1（M1-3）。  
* \[ \] 实现 Cradle Hard-Lock 门禁约束：若 DMS \< 40，自动将 Phase 3 节点打上待解锁锁定标记。  
* \[ \] 动态输出符合 Typst 编译模板的甘特时间线数据结构。

### **模块 4: Typst 极速编译桥接与销售线索导出 (typst\_generator/, sales/)**

* \[ \] 确保 Typst 能够即时接收动态生成的问题、即兴方案理由（WHY）与动态时间线节点。  
* \[ \] 验证 150 毫秒内本地无外网编译导出 6 页高保真矢量 PDF。  
* \[ \] 完善销售线索分发模块，确保一键打包生成预置购物车与破冰话术。

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAA/CAYAAABdEJRVAAAFFklEQVR4Xu3dTWgcZRgH8A2tYPH7o6ZNNpnZpBo9iUQURargxSJKwYLQehP1IggKFkWkBwUPWlBTkYJUT371IhZ6UDRYULEgFASlJ5XiTXPSg4fW583OpOPrbkzSpEnb3w8eduZ535nd5PRnPlstAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACA5TPQ6XS2FkXxTD4AAMAaUJblVxHYBiOw7czHAABYAyKozURguy0+P83HAABYAyKoTW/cuPHSsizfi9WBfBwAgFUWge3wxMTEZVVgAwBgDRoYHh6+Jj7X5QMAAAAAAAAAAACwHIqiOFXVH6Ojo7/2qsacuWq32xvyfQEAsAKqZ63NpBDWWsDjO1JQixD3bMyfai1gPgDABaUsy3uqOzfT8qZ8fKkmJycvqo6c/TA+Pn5dPt5LzH0o6vm8DwBwTkihJ8LMN41TiCfqQNRqPCYj1v+u+u83Nk8GGtvureZui3oh6vOofaOjow9k25yR2OeP1fftz8f6WBe/4aq8CQBwTonw80vUdNabSUe06vUIPS9G72RzTvR2RO/PettY3x3LR+vxsbGxK5Y7sLX+HRJvyQcBAM5LfQLbrqg36vUIXpNlWe6J3h2N3lPNwBbjT6QgNTIyMlTPGRoaurZeXi6dTqeI7zqevqu1hOvTxsfHR+pTtkkdTGO/W0/PWrR0JG9H+j/lAwAAZ6xPYEunNo+k1z6l9RREUjVDXApvzcAWIahdVKcsY+678XlnPXe5Fd1r006lz3zs/6TXWMV2x1Joa7fbw7H8dOqn/eVzFyq2PVQdcdzXWkKIBACYV9E/sB2tr/+qjxzVoSZCz33V+lxgq6WXscf8t6P/V3w+0hxbTkX3OrlTUR/lY/2MjIzcmk7VFt3r8dbH58spaKax+K0H6nmxfO/cRpX4m7fH/PvzfhL931K4LRohNfbxWHMOAMCSFb0D21QdypJGYJuK0PNgfL5Urc8Ftvh8MzslmALR7FjD7Ls/o7+5V8V3XpnNn1dsM5Me+ZH35xO/cXfUWFqO7U/U/fju10/P+q8tW7Zc3u+5bvEbbi66/8clH6UDAOirChrTWS+/6WA2iKUQF/VdryNs1anGJ+ttWt0bBA421mevF0tHr9Lpw14V+7i9OX8+6Vq2YomnROtTven3N/oPR22K3lvNv30+1Z223w8ODl6SQmD6X6Z+LN8Vy9vy+QAAi1KFjSPpqFCq0e7bAk5G/dQ8klSPF9XRqAg1e6r+142xvbH9gRh7JZani+6jPX5vrdD1XNVpzVfz/kJUQS/93R9HvRb1TtShNBZ/9/XpCGIsrs8266l6NtxU1P6oL+N33RD7uLoKfrvy+QAAF4TR7hsMPsv7yyH2e1PUt/Edj+dji1F275idu6MWAOCCEkHoWDpKlvd7qa6X25n3+4n9TsT8LyJw3ZiPLUbs49HYx3N5HwDgvBch6Hjem8e6CE4/1zcYAACwgtJ1YenIV3oob9Hj7tJU6fqzCHTboz4sqmvrquvRAABYacXpZ64tqjqdzmC+LwAAAAAAAAAAAFiK9KDa+t2f/aS3DpSLfMUVAABnUXqNVlEUm/M+AABnQVmWn+S9nMAGALBK0rPY0vtK835OYAMAWEXVC+bvjro4hbJmpV41R2ADAFgtEcY+aLfbG/J+rQpyh6MORm3LxwEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGb9A4OdMdfB6QpQAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,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>

[image4]: <data:image/png;base64,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>

[image5]: <data:image/png;base64,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>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHYAAAAbCAYAAACpzXuVAAAFDElEQVR4Xu1Yb2hWVRi/YxOMzOjPHPt3z/tugzHTvkyNgUGIRBCVWkEkGDOwEEHzg8rwgyh+UFNwiIQFIyIGIX4zNEKFgUaDlUEKgcRkJBrWlwr/4PT3232e7XmP933v3m2vLDk/eLjnPOe55z7n+Z3znHNuFAUEBAQEBAQEBPzvUZVLsCqO4xc6OzvnUJfP59vxrPFsA8oBgvqxc+6+kb8gN6T8D+TzxsbGJvtOa2vrAugv6Dvo4z3bbgGS6mBz2fYPEleyDeV+lE/huRZ97MNzCNID3ena2tp5fl+PEJxwWxgbq+SEg3/7Iccg7zc1NT1h20ugCva9kKOQ11Gv9g0qAgRyO4OO5xt+G1eRDORvDGyZbYOuHvIV25qbmxfZNkENgrMLclj6364NCEojCbXGBCcJ9Gdnitj29vanojIC2dLS8jS+f8b3F5O52fqLtmdQH4RsUl0aYNcJm+um3oL6MMb5mrWrCEoRS5A0kgf5RtLlGITY1ZBRGwTT3iHE7vADJQPea+1Fz4H3T5NYrriX0M9ZyMEyV9ZWyAHIv9Zf1NfSZ8/2a8i5Ur5yjJBhrXOioT6AvvpQrTKmM48sYs3svAnpUD3K9UzTeP5A4Wy37yG43dB3mf7HA9XQ0PA8gwd5204WlmG3MJraoKvxzbfEn53w7TnfoBRkMnxKn+mbR2yvRyztv4T+Giej1SvQPhftJ50hlpMA9XOQQcbV2s84soitq6t7Eu3f0wayRvUo19NReX80lr2TkJTWy2casfI++1PhQDeXSwbBySApfIh90F/fJgvi7zH0kyOBziOWJBYhlnYFeoUhMY3YYUi9tZ9xZBFLyCAKyKFjdNSk6iORrDSUu/BON8sliN0E+Y9tRv5Ef0usXTEwxcJ+PeRnPstIuT6Yuj+Bf++y4hOrZPgEZhHrkq2KBM5OYr0VO36AoGOyv9SgfBwyAslHSaB2OUnbxYgVVIPIVth/BJufaIfyj1krF31thu0QV6pN5VMBD4Xo66D24xOr4/cJzCJWbgRX3GwlNp7YYwsGQcf04MAAoz7KJwdEYiO5i6YRm5YuZX/tYz+xSetpQP+/uWRbmPSJNw2ylXyG/nKq84klSKJPYBaxsz4Va6pF+ymb7iyxel+lDQbcbftKI7ZYMKBfDtu7xXxRcGLEsmrxXDfVNIz3FsPfX9DHVRVn7vGiW4nyXt9nIXbEv+cbaCZLI3ZArmKVgwn8Q8E099jbIPhl2+YMsVFy/D/ikpPutyRa7YoRa20U+MZS2N4gwX5bGsw+e4lEp2WCckHfOA7rL/x6kwRrPTdx4j3Jsqh5Kie0rmO/qXW5DfwK6VVdxYCP9EjgC4jlPueSvyW34uRgUXAFgb6Df6FMndeE2867nxYjFrovvJXGybEHgfnOTJjJouCq09bWNt83mCxkcvFQ16M6xiKXbC9jgN9taB/Jmb9uqH/IcUL6I9mG1E5tuDhckhG6VFcR5Ap/Kd6JJ9LRHan35ZN/t+OQX4pjBx2RE1wpkmY4i8ec5gx3E2lN5Q/qhdjdkCvw4TDkAxKK+kV8z9nvlYlq9LECMgA5kHUIs5BxnYfcM/4ye+gv0N9R3gZ5B+VB+LvPHty4MFyyCLZFZhFAtwa6DRwjypcgG237YwXM5Gf5ZNqCvMJgkexomochgypMkBcRxEP6remCkxd9vgp/V/EXo99eCiSdUs5ECwgICAgICAgICAgICAh43PAAPEXQhgQ0YH0AAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE8AAAAaCAYAAAD2dwHCAAADlElEQVR4Xu2XS0hVQRjHlQx6Qfawi68712sQRYFwK3DjKnpARUiLwKJFmwqKiqCQgh64iMhNthCCHmAGRQ8kAotwlZItCrwoQVBRCQVGUC6itN/fM1PH6d4C0eja+cOfmfnmO3PO/O/3zTc3Ly9ChAgRImRERUVFTSKR2OLbxwOsHYMrWX+axmVlZQvhdN8vV1FgjGmF6ZKSkvn+JBtdxsafMT8c4oBlH9ydSYxUKjWV507BR/jUw6e27YLFvn9OIh6PJ9lMPxyiv8qfdygvL1+BzyC8zrBANoSpYvwc9hBdJuzP3E4JVVpaOk/jZDI5m/F9+HLSiMdG6qwAw7AJU77vIyBsivnPiHIpbLfP69nWPCtqUVHRLMYdsMHzrYbpySJeAaJchNtMEH29OqN8JyGbeNg3SDyldmVl5QLZJI4JIuxHlFrfObJNCvFsyt5QatlNDSHCWt9PyCaeyRB5Kg6M78Bv8EDIPZ91lug8DNlyE9o4Gz3m+lYEpe4vyCQeUbrIFpNufoCysD9n5EYrntbsw+84kVke9slljKQsG6vWIFQ4en1HwYlngiqr80z8qsKQJZIUZevxeWcFFL/AWt9Rkerb/mm4lFUVtCZdWUZSd5SjRabIY3weftA9LuzrQSJuxe+eFfCt7npujvX2ax3WOEj/cJYf4rfgijWDNS7Dj/pOf368MSrqHFz0ZSoaWcRzheF1OG1ll5+qrrMJbn3aQ3acgrd8v7FAa2itCRePDSyGbaGocxiJvkxF4w/iDeoe6NkfY1vqbIIEltAmOGsLTRC5b1j7Am0TtuZYLDaTtkrvwXaGdru+FZ7UZZzxJvqN8oW7XKT+LfGm8PIjvOSq+v6kNqaN5Hn3vdAlucXNxYOrR7cJ0rHO2vbgu8YEoj5gw3PdGvEgfdMuSsORZ9dvc1FIv5a5VzBpBW3Htg7eNUEFz6c9C3fIf8LFIx1Xm58VcNTdTB+I7Zqbg59go/6e0faEnzNB0WjUc7S1JigED22FvUlE65kunWG0L2z06Ezqx2e5+56weOG+ndP9scONFYmy2X3E7HxL3B4BEy7eREHprx/GplSx0ssVBaUVG9rMfI1fDMYiHrZzou6mEi7nxRsrxijeE/1AstE2wBOw7r8SDzESbPoKHKDb7PrwqK4+tJ3wPaxnfp8J7qCd9G/TnqbdpRam6e+Vn/zpt8Mq/30RLBCnMJFrF+sIESJEiDD58B14M0eR6o7V7QAAAABJRU5ErkJggg==>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEIAAAAaCAYAAAADiYpyAAACpklEQVR4Xu2Xz6uMURzG32lSRCSNSfPjnV+R3a0hW0nqLq4rJCF/gbKjpKjbXbii2ChlYaGUtSi33NiIUhZYWCjhZsFCroXS9Xmac+o4zhgzc18Nnaee3jnP+Z7vOd/n/c687yRJRERERMTIIV+tVg/4olAul1ekaXoIXq3X65v8+RAUR/yM1mitcvgxmaPVaq1m89O1Wu1BpVJp+vMWOhzFTxB3ifh3cMGPaTQaa9DvwalCobCK6wu4z49zoXnFkXfMrJlSDuXyYzNBqVRax4bn4UO4Aynvx7gwd3qcA2/HkDMhI9BPoj/hulZjPh+GL7njRT9WaDabFeZfKc5qWqsc8JgbmwnYpK4OgNsY5vz5XjAF/2SELYCc161Gh21F+8J1txtrYYxaYG3bkXNoN+CcOsTRlw7mu3hLTAYwwCJkBOPN8KNrhApUHJx2Yy3QLweMSJQDfR694erDIqc7T+I78Bqs+wH9ImSELTpkhKu5MAV3M+IXfSiQdJKkn+HeZIgucNHFiAm0xX6MYG4uVHAmRgj9/jD2QsgIxuMDGDEbKjgzI3wUi8WVbPSUjY4O8swOGYHWQJsPGQFPubEW6NOhgo0Rb7mBZVfPBO12exkbHjSGHJc5fkw3hIww7wBq9dvkXW7idjL+pquN06NUHarPepow/92d11rlcPP8LeTZcJLD3KU7Wv5kCMaIrwH9CHyTmh/ktPNy9Mi+HJmn1gfdbcXIEPZ+DM/aHDqD5nWTrDZSUMdQ5E0O+QkuGr6HF22MuoyYK2j3KWQP1+dcx+y8Wh3tGZy15tAVWxi/Zt0JuD/tvIucUy677l9FjiI3qqg/LUYm0y27ZJ7eNv35JYEOo+8lTm/4HTnA+mTIp8lIQ62Zdv7V9eIFGeKvj4iIiIiI+H/xA7Bx1bI6VNz+AAAAAElFTkSuQmCC>

[image9]: <data:image/png;base64,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>

[image10]: <data:image/png;base64,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>

[image11]: <data:image/png;base64,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>

[image12]: <data:image/png;base64,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>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAYCAYAAAAVibZIAAAAoUlEQVR4XmNgGAWjYGCBgoICh5ycXJqoqCgPuhwlgFFeXr4VaLAxugRFAGQg0OBeIJMFXY4SwAgMhgKg4XEgNrokGAAVCABtliQFKykpAc2Umw9kT1ZRUeFDN5MsICsrawI0cLW0tLQMuhxZAGiQMNDAxYqKivLocmQDoIFZwCCLQBcnG4DSKdDQqTIyMtLocpQARnV1dV4QjS4xCkYBjQAAvNgWekn9kccAAAAASUVORK5CYII=>