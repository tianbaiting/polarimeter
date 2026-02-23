# 自旋为 1 的氘核：密度矩阵、磁场进动与坐标系变换（以 beam 方向为 $z$ 轴）

下面给出一套可直接用于计算的推导链条：
1. 先用自旋 $1/2$ 的系综密度矩阵作铺垫；
2. 再到自旋 $1$（氘核）的密度矩阵（含矢量/张量极化）；
3. 在恒定磁场中的时间演化（Larmor 进动）；
4. 最后加入坐标系变化（源坐标 $\to$ beam 坐标 $\to$ 磁场坐标 $\to$ 探测器坐标）。

---

## 0. 记号与约定

- 采用基底顺序：
  $$\{|+1\rangle, |0\rangle, |-1\rangle\}$$
  这里的 $m$ 是沿当前量子化轴的磁量子数。

- 角动量算符写作 $\mathbf J$，无量纲自旋算符写作
  $$\mathbf S = \mathbf J/\hbar.$$

- 磁矩与哈密顿量：
  $$\mathbf\mu = \gamma\,\mathbf J,\qquad H=-\mathbf\mu\cdot\mathbf B=-\gamma\,\mathbf J\cdot\mathbf B.$$

- 定义进动角频率（含符号）
  $$\Omega\equiv -\gamma B,$$
  则演化算符可写成
  $$U(t)=\exp\left[-i\,\Omega t\,(\hat{\mathbf B}\cdot\mathbf S)\right].$$

> 注：若只关心进动角大小，可用 $|\Omega|=|\gamma|B$，符号决定转动方向。

---

## 1. 先从自旋 $1/2$ 的系综密度矩阵开始

### 1.1 系综定义

对两能级系统（$m=+1/2,-1/2$），若概率分别为 $w_+,w_-$，满足
$$w_++w_-=1,$$
则在该量子化轴基底下
$$\rho_{1/2}=\begin{pmatrix}
w_+ & 0\\
0 & w_-
\end{pmatrix}.$$

定义极化度 $P\equiv w_+-w_-$，可得
$$w_+=\frac{1+P}{2},\qquad w_-=\frac{1-P}{2},$$
所以
$$\rho_{1/2}=\frac12\bigl(I+P\sigma_z\bigr).$$

若量子化轴与实验坐标不一致，做旋转 $R$（SU(2) 表示为 $D^{1/2}(R)$）：
$$\rho' = D^{1/2}(R)\,\rho\,D^{1/2}(R)^\dagger.$$

这一步是后面自旋 1 的完全类比模板。

---

## 2. 自旋 $1$（氘核）的系综密度矩阵

### 2.1 仅由三态布居概率给出（无相干项）

设沿某轴的三态概率为
$$w_{+1},\ w_0,\ w_{-1},\qquad w_{+1}+w_0+w_{-1}=1.$$

则密度矩阵（该轴基底）
$$\rho_{\text{diag}}=\begin{pmatrix}
w_{+1} & 0 & 0\\
0 & w_0 & 0\\
0 & 0 & w_{-1}
\end{pmatrix}.$$

### 2.2 用矢量/张量极化参数化

在核物理中常用
$$p_z \equiv w_{+1}-w_{-1},$$
$$p_{zz} \equiv w_{+1}+w_{-1}-2w_0.$$

联立归一化可解得
$$w_0=\frac{1-p_{zz}}{3},$$
$$w_{+1}=\frac{2+p_{zz}+3p_z}{6},\qquad
w_{-1}=\frac{2+p_{zz}-3p_z}{6}.$$

于是
$$\rho_{\text{diag}}=
\begin{pmatrix}
\dfrac{2+p_{zz}+3p_z}{6} & 0 & 0\\[6pt]
0 & \dfrac{1-p_{zz}}{3} & 0\\[6pt]
0 & 0 & \dfrac{2+p_{zz}-3p_z}{6}
\end{pmatrix}.$$

物理可行性要求 $w_m\in[0,1]$，即对 $(p_z,p_{zz})$ 有约束（三角区域）。

### 2.3 若极化主轴不与 beam-$z$ 重合

设极化先在某主轴系（记作 $\mathcal S$）中为上式对角形式，
要变到 beam 坐标系（记作 $\mathcal B$，其 $z$ 轴即束流方向），用自旋 1 的 Wigner 旋转矩阵 $D^{1}(R)$：
$$\rho^{(\mathcal B)}(0)=D^{1}(R_{\mathcal S\to\mathcal B})\,\rho^{(\mathcal S)}_{\text{diag}}\,D^{1}(R_{\mathcal S\to\mathcal B})^\dagger.$$

此时通常会出现非对角元（相干项）。

---

## 3. 自旋 1 算符与磁场哈密顿量

在 beam-$z$ 基底 $\{|+1\rangle,|0\rangle,|-1\rangle\}$ 中（取 $\hbar=1$ 的无量纲形式）：
$$S_x=\frac{1}{\sqrt2}
\begin{pmatrix}
0&1&0\\
1&0&1\\
0&1&0
\end{pmatrix},\quad
S_y=\frac{1}{\sqrt2}
\begin{pmatrix}
0&-i&0\\
i&0&-i\\
0&i&0
\end{pmatrix},\quad
S_z=
\begin{pmatrix}
1&0&0\\
0&0&0\\
0&0&-1
\end{pmatrix}.
$$

若磁场方向单位矢量为
$$\hat{\mathbf B}=(\sin\theta_B\cos\phi_B,\sin\theta_B\sin\phi_B,\cos\theta_B),$$
则
$$H=-\gamma\hbar B\,(\hat{\mathbf B}\cdot\mathbf S).$$

---

## 4. 在磁场中的时间演化（进动）

密度矩阵的一般演化：
$$\rho(t)=U(t)\rho(0)U(t)^\dagger,
\qquad U(t)=e^{-i\Omega t(\hat{\mathbf B}\cdot\mathbf S)}.$$

### 4.1 在“以 $\mathbf B$ 为量子化轴”的坐标系最简单

记该坐标系为 $\mathcal M$。此时
$$\hat{\mathbf B}\cdot\mathbf S = S_z^{(\mathcal M)}.$$
于是
$$U_{\mathcal M}(t)=\operatorname{diag}\left(e^{-i\Omega t},1,e^{+i\Omega t}\right).$$

故矩阵元演化为
$$\rho^{(\mathcal M)}_{mm'}(t)
=e^{-i(m-m')\Omega t}\rho^{(\mathcal M)}_{mm'}(0),
\quad m,m'\in\{+1,0,-1\}.$$

- 对角元（布居）不变；
- 非对角元相位按 $m-m'$ 线性进动。

### 4.2 回到 beam-$z$ 坐标系

若 $D^1_B\equiv D^1(\phi_B,\theta_B,0)$ 是把 beam 轴转到磁场轴的旋转表示，则
$$\rho^{(\mathcal M)}(0)=D^1_B\,\rho^{(\mathcal B)}(0)\,D^{1\dagger}_B,$$
$$\rho^{(\mathcal M)}(t)=U_{\mathcal M}(t)\rho^{(\mathcal M)}(0)U_{\mathcal M}^\dagger(t),$$
再变回 beam 系：
$$\rho^{(\mathcal B)}(t)=D_B^{1\dagger}\,\rho^{(\mathcal M)}(t)\,D_B^1.$$

合并成一步：
$$\rho^{(\mathcal B)}(t)=U_{\mathcal B}(t)\rho^{(\mathcal B)}(0)U_{\mathcal B}^\dagger(t),$$
$$U_{\mathcal B}(t)=D_B^{1\dagger}\,U_{\mathcal M}(t)\,D_B^1.
$$

---

## 5. 用矢量/张量极化看进动（更直观）

将自旋 1 的极化分为
- 一阶（矢量）极化 $\mathbf P$；
- 二阶（对称无迹）张量极化 $T_{ij}$。

在纯磁偶极哈密顿量下：

1) 矢量满足经典进动方程
$$\frac{d\mathbf P}{dt}=\boldsymbol\Omega\times\mathbf P,
\quad \boldsymbol\Omega=\Omega\hat{\mathbf B},$$
解为
$$\mathbf P(t)=R_{\hat{\mathbf B}}(\Omega t)\,\mathbf P(0).$$

2) 二阶张量满足
$$\frac{dT_{ij}}{dt}=\epsilon_{i\ell m}\Omega_\ell T_{mj}+\epsilon_{j\ell m}\Omega_\ell T_{im},$$
解为
$$T(t)=R_{\hat{\mathbf B}}(\Omega t)\,T(0)\,R_{\hat{\mathbf B}}^{\mathsf T}(\Omega t).$$

即：一阶量像矢量转，二阶量像二阶张量双边转。

---

## 6. 加入“坐标系变化”的总链式公式

实验里常见三个坐标系：
- 源极化坐标系 $\mathcal S$（制备时自然轴）；
- 束流坐标系 $\mathcal B$（beam 为 $z$）；
- 探测器/末端坐标系 $\mathcal D$（可能相对 beam 再转一个角）。

若磁场作用在中间，且在磁场段可视作恒定方向与恒定 $B$，则

$$\rho^{(\mathcal D)}(t)
= D^1(R_{\mathcal B\to\mathcal D})\,
U_{\mathcal B}(t)\,
D^1(R_{\mathcal S\to\mathcal B})\,
\rho^{(\mathcal S)}_{\text{diag}}\,
D^1(R_{\mathcal S\to\mathcal B})^\dagger\,
U_{\mathcal B}(t)^\dagger\,
D^1(R_{\mathcal B\to\mathcal D})^\dagger.
$$

其中
$$U_{\mathcal B}(t)=D_B^{1\dagger}\operatorname{diag}(e^{-i\Omega t},1,e^{+i\Omega t})D_B^1.$$

若粒子速度约为常数 $v$、磁场有效长度 $L$，则可写
$$t\approx L/v,\qquad \varphi\equiv \Omega t\approx \Omega L/v.$$

---

## 7. 常用特例（磁场沿 beam-$z$）

若 $\mathbf B\parallel z_{\text{beam}}$，则 $D_B^1=I$，
$$U(t)=\operatorname{diag}(e^{-i\Omega t},1,e^{+i\Omega t}).$$

- 若初始 $\rho$ 在此基底对角（仅有布居，无相干），则 $\rho(t)=\rho(0)$（对角元不变，且无非对角可转相位）；
- 若初始存在非对角元，则其相位随 $e^{-i(m-m')\Omega t}$ 旋进。

这解释了：仅“纯布居型”极化在与量子化轴同向的均匀磁场中不会改变布居，但在坐标系变换后观测到的分量会变。

---

## 8. 最后可直接使用的计算步骤（给程序/数值）

1. 由给定 $(p_z,p_{zz})$ 算 $w_{+1},w_0,w_{-1}$，构造 $\rho^{(\mathcal S)}_{\text{diag}}$；
2. 用 $D^1(R_{\mathcal S\to\mathcal B})$ 旋到 beam 系，得 $\rho^{(\mathcal B)}(0)$；
3. 给定 $B,\hat{\mathbf B},t$，构造 $U_{\mathcal B}(t)$ 并算
   $$\rho^{(\mathcal B)}(t)=U_{\mathcal B}(t)\rho^{(\mathcal B)}(0)U_{\mathcal B}^\dagger(t);$$
4. 若探测器轴与 beam 轴有夹角，再用 $D^1(R_{\mathcal B\to\mathcal D})$ 旋到探测器系；
5. 用末态密度矩阵计算任意可观测量
   $$\langle O\rangle=\operatorname{Tr}(\rho O).$$

以上链条就把“系综概率 $\to$ 自旋 1 密度矩阵 $\to$ 磁场进动 $\to$ 坐标系变化”完整串起来了。
