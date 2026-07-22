# 有限几何、边界、缺陷与 Cheshire string 路线图

状态：已批准，分阶段实施中

日期：2026-07-22
适用项目：`mobility_toolkit`

## 1. 已确定的产品取舍

本文按以下决定制定，不再把它们列为待定项。

1. **不保留旧接口兼容性。** 这是个人研究工具，允许一次性替换旧 CLI、MCP、skill 输入和 Python API；旧格式最多保留离线迁移脚本，不保留运行期 compatibility layer。
2. **finite/boundary 与 Laurent/nonuniform 两条路线都做。** 两条路线在共享代数内核完成后并行推进，不能以其中一条代替另一条。
3. **3D 也做边界枚举。** 但所有结果必须说明枚举空间与完备性等级，不能把有限窗口内的完备枚举写成一般 3D/fracton 边界分类定理。
4. **Cheshire string 是近期优先用例。** 在通用内核刚具备条件时先交付一个静态 Cheshire vertical slice，之后再用 boundary/half-space 枚举能力升级为自动合成与分类工具。
5. **核心从第一版支持 composite、nonuniform local dimensions 与 phase-aware Pauli 数据。** uniform prime 只是优化路径。
6. **geometry 采用 generic finite region + identifications + stratification。** rectangle、box、cylinder 和 torus 只是方便构造器。
7. **核心保留 stabilizer 与 subsystem/gauge 两种表示。** boundary gauge algebra 不再被强行塞进 commuting stabilizer list。
8. **所有数学结果强制携带 exactness、assumptions、certificate 和 backend provenance。** 不允许 exact 请求静默降级成 heuristic。
9. **当前项目范围仍是 generalized Pauli/stabilizer。** 为 non-Pauli boundary 留扩展点，但本路线图不覆盖 magic boundary 或一般 commuting-projector 分类。

## 2. 最终能力边界

### 2.1 正式目标

完成本路线图后，底层应能表达和分析：

- 任意有限、显式可描述的 qudit 集合与局域 stabilizer/gauge generators；
- uniform prime、uniform composite、mixed/nonuniform qudit dimensions；
- 任意有限 region mask、洞、多边界分量、corners、hinges、周期或 twisted gluing；
- 给定的 boundary Hamiltonian、domain wall、branch cut、line defect、junction 和 endpoint；
- 有限码的 commutation、phase consistency、centralizer、logical group、GSD 与 invariant factors；
- 平移不变 bulk 的 Laurent/group-ring module、Ext、annihilator 与 Krull dimension；
- rational flat half-space 的 primary/secondary boundary module 与 quasi-symplectic pairing；
- 2D topological generalized Pauli code 的 boundary anyons、凝聚、completion 与 folding defects；
- 3D boundary candidates 的有限枚举、有限周期/支撑范围枚举及逐模型 symbolic research enumeration；
- Cheshire closed loop、open segment、tube、endpoint 和 junction 的静态 stabilizer 数据与 defect-local logical algebra。

### 2.2 明确不承诺

以下内容不属于本路线图的完成条件：

- 任意不可有限描述的无限 irregular boundary；
- 所有 3D/fracton phase 的一般数学分类定理；
- non-Pauli/magic boundaries；
- 通用 exact code distance 的高效算法；
- 从静态 stabilizer quotient 自动推出最小创建 circuit depth；
- Cheshire string 的完整动态相分类、最优创建电路或所有 finite-depth equivalence；
- 没有指定等价关系时宣称“物理上不同的全部边界”；
- 仅凭有限尺寸数值稳定就宣称热力学极限 completeness。

## 3. 三种执行核心

系统统一的是数学语义、请求/结果 schema 和证书，不强迫所有问题共用一种矩阵消元器。

### 3.1 Finite FGA core

处理有限生成阿贝尔群 presentation：

\[
M=\mathbb Z^m/\operatorname{im}R_M.
\]

主要算法：

- HNF、SNF、Howell normal form；
- integer congruence kernel；
- image、intersection、sum、quotient、membership；
- orthogonal complement、radical、symplectic reduction；
- CRT/prime-power decomposition；
- finite stabilizer phase consistency。

它负责所有有限 geometry、finite GSD/logicals、finite boundary algebra 和有限枚举。

### 3.2 Laurent/group-ring core

处理平移不变 bulk：

\[
R=\mathbb Z_n[\Lambda],\qquad P=P_0[\Lambda].
\]

主要算法：

- Gröbner basis；
- syzygy/free or quasi-free resolution；
- Ext；
- annihilator、saturation、Krull dimension；
- translation action 与 coarse-graining。

Macaulay2 继续负责这部分，但输入输出改为结构化 module presentation；不再把自由文本 polynomial matrix 当作 canonical IR。

### 3.3 Half-space/stratum core

对 primitive normal \(n\) 定义

\[
H_n=\{r\in\mathbb Z^D:n\cdot r\ge 0\},
\qquad
R_\parallel=\mathbb Z_n[\ker n].
\]

计算：

\[
L_H=L\cap P_H,
\qquad
P_\partial=L_H^{\perp_H}/L_H.
\]

这部分使用 one-sided support、depth filtration、semigroup/Toeplitz presentation 和 \(R_\parallel\)-module 算法。它不是 `R/(z-1)`，也不是普通有限 patch 的改名。

## 4. Canonical 数据模型

以下对象是后续所有阶段的共同合同。

### 4.1 代数对象

```text
FiniteAbelianGroup
  relation presentation
  invariant factors

ModuleMap
  source / target
  sparse integer matrix
  relation witness

PauliModule
  local finite abelian factors
  phase modulus and convention
  alternating bicharacter

PauliOperator
  central phase
  sparse site -> local Weyl exponents

StabilizerCodeSpec
  PauliModule
  isotropic stabilizer subgroup
  phase assignment

SubsystemCodeSpec
  PauliModule
  gauge subgroup
  derived or explicit stabilizer center
```

对普通 mixed-dimensional qudit，projective Pauli space 为

\[
P=\bigoplus_i\left(\mathbb Z_{d_i}\oplus\mathbb Z_{d_i}\right),
\]

配对取值于公共 phase modulus 或等价的 \(\mathbb Q/\mathbb Z\)。

### 4.2 Periodic 与 finite 双 IR

```text
PeriodicCode
  translation group
  local species and dimensions
  dimension-independent sparse operator templates
  equivariant Pauli module and pairing

FiniteCode
  explicit finite Pauli module
  stabilizer/gauge presentation
  geometry and provenance
```

两者共享 operator 和 pairing 语义，通过 geometry compiler 相连，但不合并成一个 mega-class。

### 4.3 Geometry 与 defect

```text
FiniteRegion
  selected sites/cells
  identifications and twisted gluings
  removed subregions
  coordinate metadata

Stratification
  strata
  incidence relations

Stratum
  intrinsic dimension / codimension
  selector
  component id
  orientation / normal data
  parents / children
  labels

LocalModification
  selector
  remove/replace/add generators
  add/remove local degrees of freedom
  optional Pauli automorphism or gluing
  optional condensation data
```

普通边界、tube wall、Cheshire line、segment endpoint 和 junction 都由不同 strata 表示。

### 4.4 结果与证书

```text
ComputationResult[T]
  schema_version
  canonical_input_hash
  value
  exactness
  assumptions
  theorem_scope
  certificate
  verification
  backend_provenance
  resource_usage
  warnings
```

`exactness` 固定为：

- `certified_exact`：有可机器复验的完整性证书；
- `bounded_exact`：在明确给定的 finite region/window/period/support bound 内完备；
- `stabilized_empirically`：多次扩大窗口后不变，但没有 completeness proof；
- `experimental`：研究算法或尚未验证的 coefficient/domain；
- `unsupported`：能力不匹配，结构化拒绝。

## 5. 3D 枚举的精确定义

“3D 也要枚举”拆成三个正式层级。三者都实现，但不能混用名称。

### E1：有限系统全枚举

输入是有限 boundary algebra \(A_W\) 或完整 finite boundary code。枚举其中所有满足指定条件的：

- isotropic subgroups；
- maximal isotropic/Lagrangian subgroups；
- compatible phase lifts；
- 可局域 lifting 的 boundary terms；
- 用户选择等价关系下的 orbit representatives。

这是有限问题，可以做到 `certified_exact`。复杂度和输出数量可能指数增长，因此必须支持资源预算、延迟迭代器和分片缓存。

### E2：有限周期与支撑上限内全枚举

输入包括：

- boundary unit-cell period；
- generator support radius/depth；
- boundary normal；
- coefficient domain；
- 允许的 ancillary boundary qudits；
- completion depth。

在这个明确搜索空间内枚举所有 translation-compatible candidate submodules 和 local Hamiltonian completions。结果是 `bounded_exact`，不是一般 thermodynamic completeness。

### E3：symbolic half-space/fracton 枚举

在 \(R_\parallel\)-module 层枚举 finitely generated isotropic/Lagrangian submodules，结合：

- primary/secondary boundary module；
- saturation；
- boundary charge pairing；
- syzygy 与 submodule enumeration；
- directional mobility/termination constraints；
- completion 与 anomaly checks。

只有在算法能够给出 module-theoretic completeness certificate 时才标 `certified_exact`；否则标 `experimental`。E3 是正式研究目标，但路线图不预设一般 3D/fracton 分类定理已经成立。

### 3D 边界等价关系

枚举结果必须让用户显式选择 quotient 关系：

1. generator change 与冗余项；
2. microscopic translation/relabeling；
3. boundary-local Clifford/symplectic automorphism；
4. 添加/移除 trivial ancilla；
5. stacking 2D topological layers；
6. foliated equivalence。

前四项先进入稳定实现；后两项属于 3D/fracton research track。没有选择等价关系时输出 raw candidates，不能称为“不同物理边界数”。

## 6. 实施阶段

## Phase 0：冻结理论合同与清理旧入口

### 要做

- 等当前并发修改结束后冻结一个明确 git baseline；
- 写 ADR：Pauli phase convention、矩阵行列约定、pairing sign、Laurent involution；
- 固定 canonical schema v1；
- 记录现有 toric、Z4、color、X-cube、Haah、fish 等 regression fixtures；
- 区分 `compatibility regression`、`mathematical correctness` 和 `literature benchmark`；
- 设计 backend capability 与 exactness schema；
- 列出旧 API、CLI、MCP、skill 的删除清单。

### 不做

- 不保留旧运行期 API adapter；
- 不把当前 tuple/polynomial string schema 延伸到新代码；
- 不在工作区仍有未归属中间改动时开始目录级重构；
- 不把当前 boundary golden output 当作论文级 correctness oracle。

### 交付物

- `docs/adr/` 下的语义 ADR；
- schema v1 文档；
- backend capability matrix；
- baseline manifest 与旧入口删除计划。

### 验收门槛

- 同一数学输入 canonical serialization/hash 唯一；
- 所有矩阵 map 方向和 Pauli coordinate order 无歧义；
- 删除旧入口不会误删尚无替代品的核心算法实现。

## Phase 1：Universal algebra 与 phase-aware Pauli core

### 要做

- 实现 `FiniteAbelianGroup`、`PresentedModule`、`ModuleMap`、`Submodule`；
- 实现 mixed \(d_i\) 的 `PauliModule` 与 alternating bicharacter；
- 实现 phase-aware `PauliOperator`、Heisenberg lift 与 scalar-obstruction 检查；
- 同时定义 `StabilizerCodeSpec` 与 `SubsystemCodeSpec`；
- 实现 dimension-independent sparse `OperatorTemplate`；
- 实现 canonical sparse Laurent polynomial AST；
- 核心函数保持纯计算，DB/log/cache 由 service layer 显式控制。

### 不做

- 不先写 boundary-specific class hierarchy；
- 不用 `qudit_dim + prime_bypass` 表示 mixed dimensions；
- 不用 NumPy dense matrix 作为 public IR；
- 不实现物理 boundary 分类。

### 交付物

- `core/` algebra 与 Pauli objects；
- `periodic/` 和 `finite/` 的基础 IR；
- schema round-trip 与 canonical hash tests。

### 验收门槛

- 支持 \(d=2,3,4,6,8,12\) 及 mixed `[2,3]`、`[2,4]`、`[3,6]` 的合法对象；
- projective commutation 与 phase lift 分层验证；
- qudit reorder、generator reorder 不改变 canonical invariants。

## Phase 2：可信的 exact finite FGA kernel

### 要做

- 实现 image、kernel、intersection、sum、quotient、membership witnesses；
- 实现 HNF/SNF/Howell 与 CRT/prime-power route；
- 实现 orthogonal complement、pairing radical、symplectic reduction；
- 实现 finite stabilizer centralizer、logical group、GSD 与 paired logicals；
- prime field 与 \(d=2\) bit-packed 快路径统一回 canonical FGA result；
- 评估 FLINT/python-flint 作为 optional native backend；
- Sage 或独立 CAS 仅作 oracle/cross-check，不设为硬依赖；
- 每个 normal form/kernel/quotient 都返回 standard certificate；
- 写小系统 brute-force property tests。

### 不做

- 不继续把当前固定 100 次 break 的自写 SNF 当作生产 backend；
- 不因为输入是 composite 就降级成域上 rank；
- 不默认计算巨大的完整 SNF transforms；只有请求 representatives/witness 时才计算；
- 不实现通用 exact minimum distance 搜索。

### 交付物

- `finite/solver`；
- backend protocol 与 verifier；
- composite/nonuniform correctness suite；
- 性能基线和 sparse-to-dense materialization policy。

### 验收门槛

- 所有小系统与 Pauli-group/Hilbert-space 穷举一致；
- 满足 \(|S^\perp/S|=K^2\) 等内部一致性关系；
- 注入错误 SNF/kernel certificate 时 verifier 必须拒绝；
- internal 与至少一个独立 backend 的 invariant factors 一致。

## Phase 3：Generic finite geometry、strata 与 compiler

### 要做

- 实现 arbitrary `SiteSet`/cell set、mask、holes 和 disconnected regions；
- 实现 open、periodic、twisted 与 arbitrary gluing；
- 实现 boundary components、surface/edge/corner strata 和 incidence；
- 实现 explicit term restriction/rewrite policy；
- 实现 `PeriodicCode -> FiniteCode` sparse compiler；
- 实现 local overrides、domain-wall seam、branch cut 和 auxiliary boundary qudits；
- 可视化坐标与拓扑 ID 分离；浮点位置不参与数学身份判断。

### 不做

- 不把最后一个坐标轴固定为开放方向；
- 不把 crossing stabilizer 的 drop/truncate 设为隐藏默认；
- 不为 2D/3D 复制 `_2d`/`_3d` 算法族；
- 不在本阶段自动合成 boundary terms。

### 交付物

- `geometry/regions`、`identifications`、`strata`、`compile`；
- rectangle/box/cylinder/torus/annulus/tube convenience constructors；
- arbitrary-mask 与 gluing tests。

### 验收门槛

- rectangle、torus、cylinder、annulus、multi-hole、irregular mask 均编译到同一个 `FiniteCode` IR；
- 坐标原点平移、site relabeling 不改变 algebraic result；
- 每个编译后的 generator 保留模板和 geometry provenance。

## Phase 4：Cheshire static MVP（优先纵向用例）

这一阶段在完整 boundary 枚举之前交付可用的 Cheshire 工具，输入中的 defect terms/condensation data 可以由用户指定。

### 要做

- 实现 `TubularDefect`、`LineDefect`、`ClosedLoop`、`OpenSegment` constructors；
- tube wall、line core 和 segment endpoints 使用独立 strata；
- 支持删除 tubular neighborhood 或直接施加 line-local stabilizer rewrites 两种表示；
- 编译给定的 charge-condensing tube/line Hamiltonian；
- 计算 local centralizer、defect-local logical group、GSD change、endpoint algebra；
- 检查给定 bulk string/charge 是否可终止在 line/tube 上；
- 比较 closed loop、open segment 以及长度/管径变化；
- 输出 finite-size scaling 数据和 exactness 标签；
- 提供至少一个 3+1D toric-code Cheshire reference model。

### 不做

- 不自动枚举所有 Cheshire species；
- 不自动发现 condensation data；
- 不从 static logical degeneracy 推断最小创建 circuit depth；
- 不宣称 tube-radius shrinking 总保持相等价；
- 不做完整动态 deformation/fusion circuit synthesis。

### 交付物

- `defects/cheshire` 静态 schema 与 constructors；
- `mt-cheshire` 第一版；
- closed/open Cheshire literature benchmark；
- endpoint 和 defect-local logical reports。

### 验收门槛

- 同一给定 defect 的两种有限表示在声明的等价范围内给出一致 logical invariants；
- closed loop 与 open segment 能表达不同 endpoint 数据；
- 所有结论明确区分 finite exact 与 thermodynamic inference。

## Phase 5A：Finite boundary algebra 与枚举核心

Phase 5A 与 Phase 5B 并行。

### 要做

- 对 support window \(W\) 精确计算

  \[
  C_W=\{p\in P_W:\omega(p,S_{\rm bulk})=0\},
  \qquad
  A_W=C_W/(S_{\rm bulk}\cap P_W);
  \]

- 返回 invariant factors、generator lifts、induced pairing、radical；
- 区分 primary candidates、secondary operators 和 bulk-trivial elements；
- 保留 tangent translation action，不再用 greedy translation pruning 定义商；
- 实现 finite-window stability scans；
- 实现 E1 全枚举：isotropic/Lagrangian subgroups、phase lifts 和 local completion candidates；
- 加入 automorphism/orbit reduction、延迟迭代与 checkpoint；
- 枚举引擎维度无关，2D/3D 使用同一核心。

### 不做

- 不把 support-minimized representatives 当作 boundary algebra 本身；
- 不把窗口增大后几次不变自动升级为 `certified_exact`；
- 不默认枚举所有 subgroups 后一次性放进内存；
- 不在没有选定 equivalence relation 时报告“物理边界数”。

### 交付物

- `boundary/algebra`；
- `boundary/enumeration/finite`；
- E1 certificate 与 resumable enumeration protocol；
- 旧 Algorithm 1 的替代实现，旧入口直接删除。

### 验收门槛

- boundary normal/开放轴可任意选择；
- toric、Z4 toric、fish toric 的有限 boundary algebra 与已知结果一致；
- 小 boundary algebra 的全部 Lagrangians 与 brute-force subgroup enumeration 一致。

## Phase 5B：Laurent core 泛化（与 5A 并行）

### 要做

- 用 canonical Laurent AST 和 module presentations 替换 polynomial strings；
- 表示 quasi-free \(P_0[\Lambda]\)，不再假定 uniform free \(R^{2q}\)；
- stabilizer image 与 local-order relations 一起进入 presentation；
- structured Macaulay2 I/O、backend version/capability probe；
- 重做 Ext、annihilator、Krull dimension、saturation service；
- uniform-prime 保持 production；
- composite/nonuniform Laurent 按 operation 建立 capability matrix、验证基准与 experimental-to-production gate；
- 复现 2204.06023 的 uniform、Z4 与 nonuniform examples；
- 核心删除含混的 `prime_bypass` 语义。

### 不做

- 不因为 Macaulay2 能建立 `ZZ/n` quotient ring 就宣称 composite Ext 已正确；
- 不把 finite boundary 编译成巨大 Laurent quotient 来替代 finite FGA；
- 不在无 resolution/Ext 验证时给出 production physics label；
- 不通过 `R/(z-1)` 表示实空间边界。

### 交付物

- `periodic/` canonical IR；
- M2 structured backend；
- composite/nonuniform feature matrix；
- bulk literature benchmark suite。

### 验收门槛

- 当前正确 uniform-prime charge-module 结果全部复现；
- module presentation 明确包含 nonuniform order relations；
- 不支持的 coefficient/operation 返回 `unsupported`，而不是近似答案。

## Phase 6：Half-space symbolic engine 与 E2 枚举

### 要做

- 实现 primitive normal、lattice basis change 与 tangent lattice；
- 构造 one-sided support/semigroup presentation；
- 计算 \(L_H\)、\(P_\partial\)、primary/secondary modules；
- 计算 quasi-symplectic pairing、radical、saturation、boundary charges；
- 实现 boundary-to-bulk maps；
- 支持 orientation comparison；
- 实现 E2：在指定 unit-cell period、support/depth 和 ancilla bounds 内全枚举；
- finite exhaustion 与 symbolic module 双向交叉验证；
- 保存搜索空间描述作为 completeness certificate 的一部分。

### 不做

- 不把 finite window 与 half-space result 合并成同一 exactness 类型；
- 不先支持 arbitrary irrational/non-finitely-described surfaces；
- 不把 special-direction X-cube 结果外推到所有 normals；
- 不在此阶段宣称 E3 一般完备。

### 交付物

- `boundary/halfspace`；
- `boundary/enumeration/bounded_periodic`；
- `mt-halfspace`；
- 2D/3D toric 与 X-cube orientation benchmarks。

### 验收门槛

- 2D toric、3D toric 的 symbolic/finite results 对齐；
- X-cube 至少覆盖轴向与一个 generic rational normal；
- E2 输出能够精确复述自己枚举了什么、没有枚举什么。

## Phase 7：2D topological boundary/defect 完整流水线

### 要做

- boundary strings 与 anyon extraction；
- fusion group SNF；
- topological spin 与 braiding；
- Lagrangian condensation enumeration；
- short-string lifts 与 topological-order completion；
- folding interfaces 与 defects；
- boundary logicals、GSD 和 anyon termination；
- 对 finite truncation/search ranges 给出 bounded/completeness diagnostics；
- 支持 prime 与 composite uniform \(\mathbb Z_d\)。

### 不做

- 不把 2D anyon Lagrangian 定理直接套到所有 3D/fracton boundary；
- 不隐藏 BB code 等模型中可能很长的 anyon period；
- 不用固定几个单位胞的稳定性代替 saturation/completeness check；
- 不在本阶段覆盖 non-Pauli 2D topological orders。

### 交付物

- `boundary/anyons2d`、`boundary/completion2d`、`defects/folding`；
- `mt-gapped-boundary-2d`；
- 2D all-boundaries enumeration report。

### 验收门槛

- Z2/Z4 toric、double semion、color、fish toric 和至少一个 BB code benchmark；
- rough/smooth、多洞和 mixed-boundary GSD 正确；
- folding 前后 pairing sign 与 invariants 一致。

## Phase 8：3D topological/fracton boundary 枚举

### 要做

- 用 E1 枚举有限 3D boundary algebra 的全部 isotropic/Lagrangian candidates；
- 用 E2 枚举指定周期、支撑、深度和 ancilla bounds 内的全部 local completions；
- 开发 E3 symbolic submodule enumeration、saturation 与 anomaly/completion tests；
- 为每个 candidate 生成：
  - algebraic condensation data；
  - local boundary-term lifts；
  - phase/commutation certificate；
  - residual boundary logical/topological-order data；
  - bulk excitation termination map；
  - orientation 与 mobility constraints；
- 实现 raw、translation、local Clifford 与 trivial-ancilla equivalence quotients；
- 后续研究 stacking 2D layers 与 foliated equivalence；
- 按模型推进 3D toric、X-cube、Haah、checkerboard；
- 允许输出 counterexample/inconclusive，而不是强制生成 boundary。

### 不做

- 不把 `maximal isotropic in a finite window` 自动称为 thermodynamic gapped boundary；
- 不把所有 fracton boundary 简化为普通 anyon Lagrangian subgroup；
- 不忽略 boundary normal 与特殊方向；
- 不承诺 Type-II fractal completion 在有限预设 support radius 内必然出现；
- 不把 foliated equivalence 默认为普通局域 Clifford equivalence；
- 不覆盖 non-Pauli magic boundary。

### 交付物

- `boundary/enumeration/symbolic3d`；
- `mt-gapped-boundary-3d` 或 `mt-fracton-boundary`；
- per-model theorem/assumption registry；
- resumable enumeration database 与 candidate certificates。

### 验收门槛

- 3D toric 已知 electric/magnetic 类边界可重现；
- X-cube 不同 normals 的候选集合和 termination data 有可解释差异；
- 每个“all”结果都绑定 E1/E2/E3 中的一个明确枚举域；
- 没有 completeness proof 的 E3 结果始终保持 `experimental`。

## Phase 9：Cheshire 自动合成、枚举与静态融合

这一阶段把 Phase 4 的用户指定 Cheshire 模型升级为由 boundary/half-space algebra 驱动的自动工作流。

### 要做

- 从 tubular boundary algebra 枚举 charge-condensing subgroups；
- 枚举 closed tube、open tube 和 endpoint completions；
- 将 tube 半径逐步缩到 lattice scale，并逐步核对 logical/pairing/termination data；
- 自动生成 line-local stabilizer/gauge candidates；
- 枚举指定搜索域内的 Cheshire species；
- 计算 defect-local degeneracy、endpoint algebra、bulk charge storage；
- 对两条给定或枚举得到的 Cheshire defects 执行静态 fusion construction；
- 计算 fusion 前后 finite logical counting 与候选 superselection data；
- 支持 junction strata 和多段 defect network；
- 对 3+1D toric、至少一个 fracton model 建 reference workflow。

### 不做

- 不把 tube shrinking 的有限尺寸匹配自动提升为 phase-equivalence proof；
- 不从 static fusion counting 自动推出有限深度 fusion circuit；
- 不求最小 sequential creation depth；
- 不承诺枚举搜索域外的所有 Cheshire descendants；
- 不把 Cheshire 与任意 line defect 无条件视为同一对象。

### 交付物

- `mt-cheshire` 第二版；
- tubular-to-line synthesis pipeline；
- Cheshire enumeration/fusion result schema；
- closed/open/junction reference catalog。

### 验收门槛

- Phase 4 的手工输入案例能被自动流程重现；
- 每个自动生成 defect 都附带 local Hamiltonian、phase/commutation、logical 和 termination certificates；
- 动态结论与静态结论在输出 schema 中完全分离。

## Phase 10：统一 services、skills、性能与研究发布门槛

### 要做

- 所有 CLI、MCP 和 skills 只调用一个 versioned service layer；
- 删除旧 boundary tuple、blocked/interleaved dual layout 和旧 schema；
- 建立 skills：
  - `mt-finite-code`
  - `mt-boundary-algebra`
  - `mt-relative-homology`
  - `mt-halfspace`
  - `mt-gapped-boundary-2d`
  - `mt-gapped-boundary-3d`
  - `mt-defect`
  - `mt-cheshire`
- cache key 包含 canonical input、operation、backend fingerprint、assumptions、certificate level；
- 枚举支持 checkpoint、resume、streaming、resource budget；
- 建立 correctness、literature、cross-backend、scale 四层 CI；
- production/experimental capability 自动显示在 CLI/MCP/skill 输出中。

### 不做

- 不恢复旧 API 兼容层；
- 不让 skill 各自复制输入验证或算法 dispatch；
- 不因一个模型成功就把整个 3D backend 升级为 production；
- 不把数据库写入设为 core function 的隐式副作用。

### 交付物

- 新 public API；
- 全部新 skills；
- capability/benchmark dashboard；
- release checklist。

### 验收门槛

- 同一请求从 Python、CLI、MCP、skill 得到同 schema 结果；
- 所有 experimental 能力在机器可读字段中可见；
- 长枚举可以安全中断和恢复；
- 删除旧接口后没有内部模块继续依赖旧 tuple/string conventions。

## 7. 并行执行顺序

推荐依赖图如下：

```text
Phase 0
   |
Phase 1
   |
Phase 2
   |
Phase 3
   |
Phase 4  Cheshire static MVP
   |
   +-------------------+
   |                   |
Phase 5A            Phase 5B
finite boundary     Laurent/nonuniform
algebra/enumeration bulk
   |                   |
   +---------+---------+
             |
          Phase 6
          half-space
          /        \
     Phase 7      Phase 8
     2D full      3D enumeration
          \        /
           Phase 9
        Cheshire synthesis
             |
          Phase 10
```

Phase 5A 与 5B 都是正式工作，不互相取代。若并行人力不足，优先保证 Phase 5A 不阻塞 Cheshire，但 Phase 5B 仍必须在 Phase 6 前完成所需的 module presentation 与 backend capability。

## 8. 测试矩阵

### 8.1 Coefficients 与 local systems

- uniform：2、3、4、6、8、12；
- mixed：2×3、2×4、3×6；
- even/composite phase obstruction；
- redundant generators、nonprimitive generators、scalar contradiction。

### 8.2 Geometry

- torus、cylinder、fully open box；
- annulus、single/multiple holes；
- irregular mask、disconnected region；
- corners、hinges、junctions；
- rational slanted boundary；
- twisted gluing、folded interface；
- closed tube、open tube、line segment 和 endpoints。

### 8.3 Models

- repetition/CSS toy models；
- Z2/Z4 toric、planar surface code；
- fish toric、double semion、color code；
- bivariate bicycle examples；
- 3D toric；
- X-cube 多个 normals；
- Haah cubic code；
- checkerboard；
- 3+1D toric Cheshire loop/segment；
- 至少一个 fracton Cheshire/line-defect candidate；
- mixed Z2/Z4 unit-cell toy model。

### 8.4 必须验证的性质

- \(S\subseteq S^\perp\)；
- phase lift 不含非平凡 scalar stabilizer；
- \(|S^\perp/S|=K^2\)；
- CRT recombination 与直接整数 presentation 一致；
- CSS relative homology 与 finite symplectic quotient 一致；
- folding 后第二侧 pairing 取反；
- generator reorder/redundancy/relabeling 不改变 invariants；
- finite exhaustion 与 half-space symbolic result 在已知模型中一致；
- 枚举 certificate 能证明搜索域内没有遗漏；
- Cheshire 动态未知量不会出现在 static-certified 字段中。

## 9. 主要风险与控制措施

| 风险 | 控制措施 |
|---|---|
| Composite SNF/Howell 错误或静默截断 | 使用可信 backend、certificate verifier、小系统穷举与 cross-backend tests |
| 3D 候选数量爆炸 | streaming、orbit reduction、checkpoint、resource budget、按 invariant 分片 |
| 把有限窗口结果误报为无限边界 | 强制 E1/E2/E3 与 exactness 标签 |
| phase-free IR 后期再次破坏 schema | Phase 1 即加入 phase convention/lift |
| boundary、bulk 使用不同 Pauli layout | 只保留 canonical sparse operator IR |
| Type-II fractal boundary terms超出 support bound | 明确 `bounded_exact`，发展 E3 symbolic syzygy/saturation |
| Cheshire tube 与 line 模型并非总等价 | 每次 shrinking 单独验证，不写成默认定理 |
| 3D equivalence notion 不唯一 | 枚举请求必须显式选择 equivalence relation |
| 研究算法拖慢稳定功能 | production 与 experimental backend/skill 分离 |

## 10. 主要理论依据

- B. Ruba and B. Yang, [Homological invariants of Pauli stabilizer codes](https://arxiv.org/abs/2204.06023)：bulk charge modules、composite/nonuniform qudits 与 quasi-free modules。
- B. Ruba and B. Yang, [Witt Groups and Bulk-Boundary Correspondence for Stabilizer States](https://arxiv.org/abs/2509.10418)：half-space boundary operator modules、quasi-symplectic structure 与 directional dependence。
- Z. Liang, B. Yang, J. T. Iosue, and Y.-A. Chen, [Operator algebra and algorithmic construction of boundaries and defects in (2+1)D topological Pauli stabilizer codes](https://arxiv.org/abs/2410.11942)：2D boundary/defect constructive pipeline。
- S. Bravyi and A. Kitaev, [Quantum codes on a lattice with boundary](https://arxiv.org/abs/quant-ph/9811052)：CSS/cellular relative homology。
- D. Bulmash and T. Iadecola, [Braiding and Gapped Boundaries in Fracton Topological Phases](https://arxiv.org/abs/1810.00012)：fracton boundary braiding 与 boundary Lagrangian conjecture。
- D. Aasen et al., [Topological Defect Networks for Fractons of all Types](https://arxiv.org/abs/2002.05166)：stratified defect-network 语言。
- N. Tantivasadakarn and X. Chen, [String operators for Cheshire strings in topological phases](https://arxiv.org/abs/2307.03180)：Cheshire string 的静态与动态区别。

## 11. 第一批实施合同

Phase 0/1 按以下合同启动；若实验结果推翻其中某项，再用 ADR 修改，而不是在代码中形成隐式分支：

1. canonical schema 使用 immutable Python value objects，并提供唯一 JSON serialization/hash；
2. exact finite correctness 以 integer preimage-lattice presentation 为准，FLINT/python-flint 作为首选 production candidate，独立小系统穷举为 oracle；
3. phase modulus 统一取 \(L=\operatorname{lcm}(2d_i)\)，默认使用 normal-ordered \(X^xZ^z\) cocycle；
4. schema 从第一版允许一般 invariant-factor local systems，首个执行 backend 先完成 cyclic \(\mathbb Z_{d_i}\)；
5. Phase 4 的首个 Cheshire reference 是 3+1D \(\mathbb Z_2\) plaquette-qubit toric code 的 open segment，再加入 closed loop 与 two-segment \(T^3\) benchmark；
6. 3D 枚举默认先输出 raw candidates，并可选 quotient by translation、local Clifford 和 trivial ancilla；资源预算必须是请求的一部分。

这些合同分别由 `docs/adr/`、backend capability matrix 和 benchmark manifest 固化。后续以阶段 gate 决定是否进入下一阶段。
